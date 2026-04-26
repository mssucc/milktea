import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  sendChatMessageStream,
  listSessions,
  getSessionMessages,
  deleteSession
} from '@/api'
import { useConfigStore } from '@/stores/configStore'
import { characters, defaultCharacter } from '@/config/characters'

// Generate a UUID for new sessions (frontend-generated session IDs)
const generateSessionId = () => {
  // Use crypto.randomUUID() if available (modern browsers)
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID()
  }
  // Fallback for environments without crypto.randomUUID()
  return 'session_' + Date.now() + '_' + Math.random().toString(36).substring(2, 11)
}

export const useChatStore = defineStore('chat', () => {
  // Debug flag - set to true to enable verbose logging
  const DEBUG = false // Set to false in production

  // Debug logging helper
  const debugLog = (...args) => {
    if (DEBUG) {
      console.log(...args)
    }
  }

  const debugWarn = (...args) => {
    if (DEBUG) {
      console.warn(...args)
    }
  }

  // State
  const messages = ref([])
  const currentSessionId = ref(null)
  const sessions = ref([])
  const _loadingSessions = ref({}) // sessionId -> boolean
  const _streamingSessions = ref({}) // sessionId -> boolean
  const _isNewSessionLoading = ref(false) // For loading state when no session ID yet
  const _activeStreams = ref({}) // streamingSessionId -> { aiMessageId, userMessageId, streamingContent }
  const error = ref('')
  const currentModel = ref('llama2')
  const currentCharacterId = ref('sakurajima_mai')

  // Computed loading states based on current session
  const isLoading = computed(() => {
    const sessionId = currentSessionId.value
    let result
    if (sessionId) {
      result = _loadingSessions.value[sessionId] || false
    } else {
      // No current session, check if a new session is being created
      result = _isNewSessionLoading.value
    }
    if (DEBUG) {
      console.log('isLoading computed: sessionId:', sessionId, 'value:', result, '_loadingSessions:', JSON.stringify(_loadingSessions.value), '_isNewSessionLoading:', _isNewSessionLoading.value)
    }
    return result
  })
  const isStreaming = computed(() => {
    const sessionId = currentSessionId.value
    const result = sessionId ? _streamingSessions.value[sessionId] || false : false
    if (DEBUG) {
      console.log('isStreaming computed: sessionId:', sessionId, 'value:', result, '_streamingSessions:', JSON.stringify(_streamingSessions.value))
    }
    return result
  })

  // Getters
  const messageCount = computed(() => messages.value.length)
  const hasMessages = computed(() => messages.value.length > 0)
  const currentSession = computed(() =>
    sessions.value.find(s => s.session_id === currentSessionId.value)
  )
  const lastMessage = computed(() =>
    messages.value.length > 0 ? messages.value[messages.value.length - 1] : null
  )
  const currentCharacter = computed(() =>
    characters[currentCharacterId.value] || defaultCharacter
  )
  const systemPrompt = computed(() => currentCharacter.value.systemPrompt)

  // Actions

  const streamMessage = async (content, systemPrompt = null) => {
    if (!content.trim() || isLoading.value) return

    // Capture current session ID at the start of streaming
    const streamingSessionId = currentSessionId.value
    // Determine session ID to use for this request (generate new if none exists)
    const sessionIdToUse = streamingSessionId || generateSessionId()
    let streamAborted = false  // Set to true if stream should be completely aborted

    // Generate unique IDs for messages
    const userMessageId = Date.now().toString()
    const aiMessageId = (Date.now() + 1).toString()

    // Set loading states for the streaming session
    // Use the session ID for state tracking (generated if new session)
    const stateKey = sessionIdToUse
    _loadingSessions.value[stateKey] = true
    _streamingSessions.value[stateKey] = true
    if (!streamingSessionId) {
      // Also set the new session loading flag for UI states
      _isNewSessionLoading.value = true
      // Set currentSessionId to the newly generated session ID for immediate UI feedback
      currentSessionId.value = sessionIdToUse
    }
    error.value = ''

    // Safety timeout to ensure isLoading is always reset
    const safetyTimeout = setTimeout(() => {
      debugWarn('Safety timeout: forcing isLoading to false for session:', streamingSessionId)
      const timeoutKey = sessionIdToUse
      _loadingSessions.value[timeoutKey] = false
      _streamingSessions.value[timeoutKey] = false
      _isNewSessionLoading.value = false
    }, 60000) // 60 seconds max

    // Helper function to safely update AI message content by ID
    const updateAiMessageContent = (content) => {
      // Only log every 500 characters to avoid console spam
      if (content.length % 500 === 0) {
        debugLog('updateAiMessageContent: aiMessageId:', aiMessageId, 'content length:', content.length, 'first 50 chars:', content.substring(0, 50))
      }
      // Find AI message in local messages array
      const index = messages.value.findIndex(msg => msg.id === aiMessageId)
      if (index >= 0) {
        if (content.length % 500 === 0) {
          debugLog('updateAiMessageContent: Found AI message at index', index, 'old content length:', messages.value[index].content.length)
        }
        messages.value[index].content = content
        // Update streaming content in _activeStreams for tracking
        if (_activeStreams.value[aiMessageId]) {
          _activeStreams.value[aiMessageId].streamingContent = content
          _activeStreams.value[aiMessageId].lastUpdated = Date.now()
        }
        if (content.length % 500 === 0) {
          debugLog('updateAiMessageContent: Updated message content successfully')
        }
        return true
      } else {
        debugWarn('AI message not found for update, aiMessageId:', aiMessageId,
                    'messages count:', messages.value.length,
                    'currentSessionId:', currentSessionId.value, 'streamingSessionId:', streamingSessionId)
        return false
      }
    }

    try {
      // Check if session has changed before adding messages
      // This prevents issues when user quickly switches sessions after clicking send
      // For new sessions (streamingSessionId is null), we allow currentSessionId to be set
      // Only abort if streamingSessionId is not null and session has changed
      if (streamingSessionId !== null && currentSessionId.value !== streamingSessionId) {
        console.log('Session changed before adding messages, aborting streamMessage')
        streamAborted = true
        // Clean up state using stateKey (handles both regular and new sessions)
        const stateKey = streamingSessionId || aiMessageId
        _loadingSessions.value[stateKey] = false
        _streamingSessions.value[stateKey] = false
        _isNewSessionLoading.value = false
        // Clean up _activeStreams entry (key is aiMessageId)
        if (_activeStreams.value[aiMessageId]) {
          console.log('Cleaning up _activeStreams entry due to session change, aiMessageId:', aiMessageId)
          delete _activeStreams.value[aiMessageId]
        }
        clearTimeout(safetyTimeout)
        return { session_id: streamingSessionId, response: '' }
      }

      // Add user message to local state immediately
      const userMessage = {
        id: userMessageId,
        role: 'user',
        content,
        timestamp: new Date()
      }
      messages.value.push(userMessage)

      // Add placeholder AI message
      const aiMessage = {
        id: aiMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date()
      }
      messages.value.push(aiMessage)


      // Register this stream in _activeStreams using aiMessageId as key
      // This simplifies lookup and eliminates the need for temporary session keys
      // For new sessions, use the generated sessionId from frontend
      const initialSessionId = sessionIdToUse
      _activeStreams.value[aiMessageId] = {
        aiMessageId,
        userMessageId,
        sessionId: initialSessionId,   // Current session ID
        assignedSessionId: initialSessionId, // Backend should use the same session ID
        streamingContent: '',
        timestamp: Date.now(),
        lastUpdated: Date.now(),
        isNewSession: !streamingSessionId, // Flag to identify new sessions
        cancel: null,                   // Will be set when stream reader is created
        aborted: false                  // Flag to mark if stream was externally aborted
      }
      if (DEBUG) {
        console.log('Registered active stream with aiMessageId key:', aiMessageId, 'sessionId:', initialSessionId, 'isNewSession:', !streamingSessionId)
        console.log('streamMessage: Added messages, messages.value length:', messages.value.length,
                    'userMessageId:', userMessageId, 'aiMessageId:', aiMessageId,
                    'messages:', messages.value.map(m => ({id: m.id, role: m.role, content: m.content?.substring(0, 50) || ''})))
      }

      // Add new session to sessions list immediately for UI feedback
      // This ensures the sidebar shows the session right away
      if (!streamingSessionId) {
        // Remove any existing entry with the same session_id (shouldn't happen but safe)
        const existingSessionIndex = sessions.value.findIndex(s => s.session_id === sessionIdToUse)
        if (existingSessionIndex >= 0) {
          debugLog('Removing existing session with same session_id at index:', existingSessionIndex)
          sessions.value.splice(existingSessionIndex, 1)
        }

        const newSession = {
          session_id: sessionIdToUse,
          created_at: new Date().toISOString(),
          message_count: 2, // user + AI placeholder
          title: `New Chat ${new Date().toLocaleTimeString()}`,
          is_new: true
        }
        debugLog('Adding new session to sessions list immediately:', newSession)
        // Add to beginning of sessions array (most recent first)
        sessions.value.unshift(newSession)
      }

      // Helper function to check if we should continue updating
      const shouldContinueStreaming = () => {
        debugLog('shouldContinueStreaming: called, streamAborted:', streamAborted, 'aiMessageId:', aiMessageId, 'streamingSessionId:', streamingSessionId)
        // Check if stream was explicitly aborted
        if (streamAborted) {
          debugWarn('Stream was aborted, stopping updates')
          return false
        }

        // Check if stream was externally aborted via stopStreaming
        const streamData = _activeStreams.value[aiMessageId]
        if (streamData && streamData.aborted) {
          debugWarn('Stream was externally aborted, stopping updates')
          return false
        }

        // Get the current session ID
        const currentSession = currentSessionId.value
        debugLog('shouldContinueStreaming: currentSession:', currentSession)

        // Determine the expected session ID for this stream
        // For existing sessions: streamingSessionId (captured at start)
        // For new sessions: use sessionId from stream data (could be temp session ID)
        let expectedSessionId = streamingSessionId
        debugLog('shouldContinueStreaming: initial expectedSessionId:', expectedSessionId)
        if (!expectedSessionId) {
          // This is a new session, check _activeStreams for session data
          const streamData = _activeStreams.value[aiMessageId]
          debugLog('shouldContinueStreaming: streamData for aiMessageId:', streamData)
          if (streamData) {
            // First check assignedSessionId (real session ID from backend)
            if (streamData.assignedSessionId) {
              expectedSessionId = streamData.assignedSessionId
              debugLog('shouldContinueStreaming: assignedSessionId found:', expectedSessionId)
            } else {
              // No assignedSessionId yet, use current sessionId (could be temp session ID)
              expectedSessionId = streamData.sessionId
              debugLog('shouldContinueStreaming: using streamData.sessionId:', expectedSessionId)
            }
          } else {
            // No stream data found (shouldn't happen)
            expectedSessionId = null
            debugLog('shouldContinueStreaming: no stream data found')
          }
        }
        debugLog('shouldContinueStreaming: final expectedSessionId:', expectedSessionId)

        // Check if current session matches the expected streaming session
        // For new sessions before migration: expectedSessionId is null, so we can't verify session match yet
        // For new sessions after migration: expectedSessionId is the real sessionId
        // For existing sessions: expectedSessionId is the captured streamingSessionId
        let isCurrentSession = false
        if (expectedSessionId) {
          // We have an expected session ID, check if current session matches
          isCurrentSession = currentSession === expectedSessionId
          if (!isCurrentSession) {
            debugLog('shouldContinueStreaming: Not in streaming session (expected:', expectedSessionId, ', current:', currentSession, '), skipping UI updates')
            return false
          }
        } else {
          // No expected session ID yet (shouldn't happen with our new logic, but handle gracefully)
          // Allow updates only if current session is null (no session selected)
          if (currentSession === null) {
            isCurrentSession = true
            debugLog('shouldContinueStreaming: Current session is null, allowing updates')
          } else {
            // Current session is something else (user switched to a different session)
            debugLog('shouldContinueStreaming: User switched to different session (current:', currentSession, '), skipping UI updates')
            return false
          }
        }

        // Check if current messages contain our AI message
        const aiMessageExists = messages.value.some(msg => msg.id === aiMessageId)

        // If AI message exists, allow updates
        if (aiMessageExists) {
          debugLog('shouldContinueStreaming: AI message exists, allowing UI updates, aiMessageId:', aiMessageId)
          return true
        }

        // AI message not found in current session
        console.log('shouldContinueStreaming: AI message not found, skipping UI updates')
        return false
      }

      // Get API configuration
      const configStore = useConfigStore()
      const { apiKey, baseUrl, model } = configStore.apiConfig

      // Get stream from API
      // Use provided systemPrompt or fall back to store's systemPrompt
      const effectiveSystemPrompt = systemPrompt?.value ?? null
      const stream = await sendChatMessageStream({
        message: content,
        session_id: sessionIdToUse, // Use generated session ID for new sessions
        system_prompt: effectiveSystemPrompt,
        api_key: apiKey,
        base_url: baseUrl,
        model: model
      })

      // Read the stream
      const reader = stream.getReader()
      const decoder = new TextDecoder('utf-8')
      let fullResponse = ''
      let hasReceivedFirstChunk = false

      // Store cancel function in active streams for external abort
      if (_activeStreams.value[aiMessageId]) {
        _activeStreams.value[aiMessageId].cancel = () => {
          console.log('Cancel function called for stream', aiMessageId)
          try {
            reader.cancel().catch(() => {})
          } catch (e) {
            console.error('Error canceling reader:', e)
          }
        }
      }

      try {
        while (true) {
          const { done, value } = await reader.read()
          if (done) {
            console.log('Stream reading complete')
            break
          }

          const chunk = decoder.decode(value, { stream: true })

          // Note: Backend no longer sends [SESSION:] markers
          // Frontend generates session IDs and backend should use them
          // If backend happens to send [SESSION:] marker, filter it out
          if (chunk.includes('[SESSION:')) {
            // Filter out [SESSION:] marker but keep other content
            const cleanChunk = chunk.replace(/\[SESSION:[^\]]+\]/, '')
            if (cleanChunk) {
              chunk = cleanChunk
            } else {
              // Chunk was only the marker, skip it
              continue
            }
          }

          // Check for stream end marker
          if (chunk.includes('[STREAM_END]')) {
            console.log('Received stream end marker')
            // Remove the marker from the response
            const cleanChunk = chunk.replace('[STREAM_END]', '')
            fullResponse += cleanChunk
            // Clear loading state if not already cleared
            if (!hasReceivedFirstChunk) {
              hasReceivedFirstChunk = true
              // Determine current session ID for loading state
              let currentSessionIdForLoading = streamingSessionId
              if (!currentSessionIdForLoading) {
                // For new sessions, check active streams for session ID
                const streamData = _activeStreams.value[aiMessageId]
                if (streamData) {
                  currentSessionIdForLoading = streamData.sessionId
                } else {
                  currentSessionIdForLoading = aiMessageId // Fallback
                }
              }
              if (currentSessionIdForLoading) {
                _loadingSessions.value[currentSessionIdForLoading] = false
                if (DEBUG) console.log('Stream end received, cleared loading state for session:', currentSessionIdForLoading)
              }
            }
            // Update one last time with cleaned content if still in same session
            if (shouldContinueStreaming()) {
              updateAiMessageContent(fullResponse)
            } else {
              if (DEBUG) console.log('Session changed before stream end, not updating message')
            }
            break
          }

          fullResponse += chunk
          // Log only first chunk and every 500 chars to avoid console spam
          if (DEBUG && (!hasReceivedFirstChunk || fullResponse.length % 500 === 0)) {
            console.log('Received chunk, fullResponse length:', fullResponse.length, 'first 100 chars:', fullResponse.substring(0, 100))
          }

          // On first received chunk, clear loading state (hide "AI is thinking...")
          if (!hasReceivedFirstChunk) {
            hasReceivedFirstChunk = true
            // Determine current session ID for loading state
            let currentSessionIdForLoading = streamingSessionId
            if (!currentSessionIdForLoading) {
              // For new sessions, check active streams for session ID
              const streamData = _activeStreams.value[aiMessageId]
              if (streamData) {
                currentSessionIdForLoading = streamData.sessionId
              } else {
                currentSessionIdForLoading = aiMessageId // Fallback
              }
            }
            if (currentSessionIdForLoading) {
              _loadingSessions.value[currentSessionIdForLoading] = false
              debugLog('First chunk received, cleared loading state for session:', currentSessionIdForLoading)
            }
          }

          // Update AI message content reactively
          const shouldUpdate = shouldContinueStreaming()
          debugLog('shouldContinueStreaming returned:', shouldUpdate)
          if (shouldUpdate) {
            debugLog('Calling updateAiMessageContent with fullResponse')
            updateAiMessageContent(fullResponse)
          } else if (streamAborted) {
            // Message was removed, abort the stream
            debugLog('Streaming aborted due to message removal')
            try {
              reader.cancel().catch(() => {})
            } catch (e) {
              // Ignore cancel errors
            }
            break
          } else {
            // Session changed but stream continues in background
            // Skip UI updates but continue reading stream
            debugLog('Session changed, skipping UI updates but continuing stream')
            // Continue reading without updating UI
          }
        }
      } finally {
        reader.releaseLock()
      }

      // After stream completes, update with final response
      // The message content is already updated, but ensure it's complete
      if (shouldContinueStreaming()) {
        updateAiMessageContent(fullResponse)
      } else {
        debugLog('Session changed before final update, skipping')
      }

      debugLog('Stream message completed, session_id:', streamingSessionId, 'response length:', fullResponse.length, 'first 50 chars:', fullResponse.substring(0, 50))
      return { session_id: streamingSessionId, response: fullResponse }
    } catch (err) {
      console.error('Error in stream message:', err)
      error.value = err.message || 'Failed to stream message'

      // Update AI message with error if still in same session
      const errorAiMessageIndex = messages.value.findIndex(msg => msg.id === aiMessageId)
      if (errorAiMessageIndex >= 0 && currentSessionId.value === streamingSessionId) {
        messages.value[errorAiMessageIndex].content = `Sorry, I encountered an error: ${error.value}`
      } else {
        debugLog('Session changed during error handling, not updating error message')
      }

      throw err
    } finally {
      debugLog('Stream message finally block, streamAborted:', streamAborted, 'currentSessionId:', currentSessionId.value, 'streamingSessionId:', streamingSessionId, 'aiMessageId:', aiMessageId)
      clearTimeout(safetyTimeout)

      // Determine the session keys used for state tracking
      // Original key: aiMessageId for new sessions, streamingSessionId for existing
      const originalStateKey = streamingSessionId || aiMessageId

      // Check if we have an assigned session ID (for new sessions that received sessionId from backend)
      let assignedSessionId = null
      if (_activeStreams.value[aiMessageId]) {
        assignedSessionId = _activeStreams.value[aiMessageId].assignedSessionId
      }

      // Clear loading states for the streaming session
      // Clear original state key (aiMessageId or streamingSessionId)
      _loadingSessions.value[originalStateKey] = false
      _streamingSessions.value[originalStateKey] = false
      // Also clear assigned session ID if different (for migrated new sessions)
      if (assignedSessionId && assignedSessionId !== originalStateKey) {
        _loadingSessions.value[assignedSessionId] = false
        _streamingSessions.value[assignedSessionId] = false
      }
      _isNewSessionLoading.value = false

      // Clean up _activeStreams entry
      if (_activeStreams.value[aiMessageId]) {
        debugLog('Removing active stream entry for aiMessageId:', aiMessageId)
        delete _activeStreams.value[aiMessageId]
      }

      // Refresh sessions in background after stream completes (unless aborted)
      if (!streamAborted) {
        fetchSessions().then(() => {
          // If this was a new session (streamingSessionId was null/empty),
          // try to set currentSessionId to the most recent session
          // But only if user hasn't manually selected another session
          if (!streamingSessionId && sessions.value.length > 0) {
            // Find the most recent session (assuming first is most recent)
            const latestSession = sessions.value[0]
            if (latestSession && latestSession.session_id) {
              const newSessionId = latestSession.session_id

              // No need to migrate _activeStreams - entries are keyed by aiMessageId
              // and cleaned up in finally block after stream completes

              // Only set currentSessionId if it's still null/empty
              // This means user hasn't manually selected another session
              if (!currentSessionId.value) {
                debugLog('Setting currentSessionId to new session:', newSessionId)
                currentSessionId.value = newSessionId
              } else {
                debugLog('User has already selected another session, not overwriting currentSessionId')
              }
            }
          }
        }).catch(console.error)
      } else {
        debugLog('Stream was aborted, skipping session refresh')
      }
    }
  }

  const fetchSessions = async (limit = 100) => {
    try {
      debugLog('fetchSessions: calling listSessions API with limit', limit)
      const sessionList = await listSessions(limit)
      debugLog('fetchSessions: received session list:', JSON.stringify(sessionList, null, 2))
      if (!sessionList || !Array.isArray(sessionList)) {
        console.error('fetchSessions: sessionList is not an array:', sessionList)
        sessions.value = []
        return []
      }
      sessions.value = sessionList
      debugLog('fetchSessions: updated sessions store, count:', sessionList.length, 'first session:', sessionList[0]?.session_id)
      return sessionList
    } catch (err) {
      console.error('Error fetching sessions:', err)
      error.value = 'Failed to load sessions'
      sessions.value = [] // Ensure empty array on error
      throw err
    }
  }

  const loadSession = async (sessionId, limit = 100) => {
    debugLog('loadSession: Called with sessionId:', sessionId,
                'limit:', limit,
                'currentSessionId:', currentSessionId.value,
                'isStreaming:', isStreaming.value,
                'messages count before:', messages.value.length)

    try {
      // Don't show loading indicator if this session is already streaming
      // This prevents UI flickering and state conflicts
      if (!_streamingSessions.value[sessionId]) {
        debugLog('loadSession: Setting loading state for session:', sessionId, '(not streaming)')
        _loadingSessions.value[sessionId] = true
      } else {
        debugLog('loadSession: Skipping loading state set (session is currently streaming)')
      }

      // Set currentSessionId IMMEDIATELY so UI shows the session is selected
      // This also prevents the retry logic from thinking session changed
      debugLog('loadSession: Setting currentSessionId.value from', currentSessionId.value, 'to', sessionId, 'immediately')
      currentSessionId.value = sessionId

      // Check if this session has an active stream
      // Look for stream data where sessionId or assignedSessionId matches
      let streamData = null
      for (const stream of Object.values(_activeStreams.value)) {
        if (stream.sessionId === sessionId || stream.assignedSessionId === sessionId) {
          streamData = stream
          debugLog('loadSession: Found active stream data for session:', sessionId, 'aiMessageId:', stream.aiMessageId)
          break
        }
      }
      const isSessionStreaming = _streamingSessions.value[sessionId] || !!streamData

      // Always clear messages when loading a session to prevent cross-session data
      debugLog('loadSession: Clearing messages for session:', sessionId)
      messages.value = []

      // If streaming is in progress for this session, reduce retries since messages may still be arriving
      const maxRetries = isSessionStreaming ? 3 : 10
      const retryDelay = isSessionStreaming ? 100 : 200
      debugLog('loadSession: Using maxRetries:', maxRetries, 'retryDelay:', retryDelay, 'ms')

      // Retry logic to handle database commit latency
      let sessionMessages = []
      let lastError = null

      // Helper function to check if messages are complete (AI message updated)
      const messagesAreComplete = (msgs, isStreaming = false) => {
        // Look for assistant message that has been updated
        const assistantMsg = msgs.find(m => m.role === 'assistant')
        if (!assistantMsg) return false

        // If this is a streaming session, accept empty content (streaming content is in _activeStreams)
        if (isStreaming) {
          return true  // As long as there's an assistant message object, consider it complete
        }

        // Non-streaming sessions: check content is not empty and not a placeholder
        return assistantMsg.content && assistantMsg.content.trim() !== '' && assistantMsg.content !== 'AI is responding...'
      }

      for (let attempt = 0; attempt < maxRetries; attempt++) {
        debugLog(`loadSession: Starting attempt ${attempt + 1}/${maxRetries} for session ${sessionId}`)

        // Check if user has switched to a different session while we're retrying
        debugLog(`loadSession: Checking session change - currentSessionId: ${currentSessionId.value}, target sessionId: ${sessionId}`)
        if (currentSessionId.value !== sessionId) {
          debugLog(`loadSession: Session changed from ${sessionId} to ${currentSessionId.value} during retry, stopping`)
          // Don't throw error, just return empty array since user is no longer interested in this session
          return []
        }

        try {
          debugLog(`loadSession: Attempt ${attempt + 1}/${maxRetries} - Calling getSessionMessages for ${sessionId}`)
          sessionMessages = await getSessionMessages(sessionId, limit)
          debugLog(`loadSession: Attempt ${attempt + 1} - Received ${sessionMessages.length} messages`)
          lastError = null

          // Check if we have at least the expected number of messages
          // For a new conversation: at least 2 messages (user + AI placeholder)
          // But we don't know exact count, so just check if we have any messages
          const hasMessages = sessionMessages.length > 0

          // Additional check: if we're loading an active streaming session,
          // we should see at least 2 messages (user + AI placeholder)
          // But be lenient for edge cases
          if ((hasMessages && messagesAreComplete(sessionMessages, isSessionStreaming)) || attempt === maxRetries - 1) {
            if (sessionMessages.length === 0) {
              debugWarn(`loadSession: No messages retrieved after ${attempt + 1} attempts for session ${sessionId}`)
            } else {
              debugLog(`loadSession: Retrieved ${sessionMessages.length} messages for session ${sessionId} after ${attempt + 1} attempts`)
            }
            break
          }

          // If no messages but not last attempt, wait and retry
          if (!hasMessages) {
            debugLog(`loadSession: No messages retrieved for session ${sessionId}, retrying in ${retryDelay}ms (attempt ${attempt + 1}/${maxRetries})`)
            await new Promise(resolve => setTimeout(resolve, retryDelay))
            continue
          } else if (!messagesAreComplete(sessionMessages, isSessionStreaming)) {
            // Has messages but AI response not yet updated, wait and retry
            debugLog(`loadSession: AI response not yet updated for session ${sessionId}, retrying in ${retryDelay}ms (attempt ${attempt + 1}/${maxRetries})`)
            await new Promise(resolve => setTimeout(resolve, retryDelay))
            continue
          }
        } catch (err) {
          lastError = err
          console.error(`loadSession: Attempt ${attempt + 1} failed:`, err)

          // Wait before retrying on error
          if (attempt < maxRetries - 1) {
            await new Promise(resolve => setTimeout(resolve, retryDelay))
          }
        }
      }

      if (lastError) {
        throw lastError
      }

      // Convert API messages to local format
      debugLog('loadSession: Converting', sessionMessages.length, 'API messages to local format')
      let localMessages = sessionMessages.map(msg => ({
        id: msg.timestamp?.toString() || Date.now().toString(),
        role: msg.role,
        content: msg.content,
        timestamp: new Date(msg.timestamp)
      }))

      // If there's an active stream for this session, handle streaming messages specially
      if (streamData) {
        debugLog('loadSession: Session has active stream data:', streamData)

        // When a session has an active stream, we need to ensure:
        // 1. The database placeholder message (if any) is replaced with streaming content
        // 2. Message IDs match streamData for proper tracking
        // 3. No duplicate AI messages exist

        if (streamData.userMessageId && streamData.aiMessageId) {
          debugLog('loadSession: Processing streaming messages for session', sessionId)

          // Find and update the last user message to match streamData
          const userMessages = localMessages.filter(msg => msg.role === 'user')
          if (userMessages.length > 0) {
            const lastUserMessage = userMessages[userMessages.length - 1]
            const userMessageIndex = localMessages.findIndex(msg => msg.id === lastUserMessage.id)
            if (userMessageIndex >= 0) {
              debugLog('loadSession: Updating user message ID from', localMessages[userMessageIndex].id, 'to', streamData.userMessageId)
              localMessages[userMessageIndex].id = streamData.userMessageId
            }
          }

          // Find the AI message that corresponds to this streaming session
          // Look for AI messages and try to match them with streaming data
          const aiMessages = localMessages.filter(msg => msg.role === 'assistant')
          let foundAiMessage = false

          if (aiMessages.length > 0) {
            // Try to find AI message with placeholder content or check if we should update the last one
            // We need to determine which AI message is the one currently streaming
            for (let i = aiMessages.length - 1; i >= 0; i--) {
              const aiMsg = aiMessages[i]
              // Check if this AI message looks like a placeholder (empty or "AI is responding...")
              const isPlaceholder = !aiMsg.content || aiMsg.content.trim() === '' || aiMsg.content === 'AI is responding...'

              if (isPlaceholder) {
                // Found a placeholder, update it with streaming content
                const aiMessageIndex = localMessages.findIndex(msg => msg.id === aiMsg.id)
                if (aiMessageIndex >= 0) {
                  debugLog('loadSession: Found placeholder AI message, updating ID from', localMessages[aiMessageIndex].id, 'to', streamData.aiMessageId)
                  localMessages[aiMessageIndex].id = streamData.aiMessageId
                  localMessages[aiMessageIndex].content = streamData.streamingContent || ''
                  foundAiMessage = true
                  break
                }
              }
            }
          }

          // If no placeholder AI message found, add streaming AI message
          if (!foundAiMessage) {
            const streamingAiMessage = {
              id: streamData.aiMessageId,
              role: 'assistant',
              content: streamData.streamingContent || '',
              timestamp: new Date() // Use current time for streaming message
            }
            debugLog('loadSession: Adding streaming AI message with content length:',
                        streamingAiMessage.content.length,
                        'preview:', streamingAiMessage.content.substring(0, 50) || '(empty)')
            localMessages.push(streamingAiMessage)
          }
        }

        // Re-enable streaming state so UI updates resume
        // Only set streaming state, loading state is managed by streamMessage
        _streamingSessions.value[sessionId] = true
        // Don't set loading state here - it's managed by streamMessage
        // This prevents showing "AI is thinking..." alongside streaming content
      }

      debugLog('loadSession: Setting messages.value to', localMessages.length, 'messages')
      messages.value = localMessages
      debugLog('loadSession: Messages set, count:', messages.value.length)

      error.value = ''

      debugLog(`loadSession: Loaded ${sessionMessages.length} messages for session ${sessionId}`)
      debugLog('loadSession: Final state - messages count:', messages.value.length, 'currentSessionId:', currentSessionId.value)

      return messages.value
    } catch (err) {
      console.error('Error loading session:', err)
      error.value = `Failed to load session: ${err.message}`
      throw err
    } finally {
      // Only reset loading state if this session is not streaming
      // (streamMessage manages its own loading state for streaming sessions)
      if (!_streamingSessions.value[sessionId]) {
        _loadingSessions.value[sessionId] = false
      }
    }
  }

  const startNewSession = () => {
    // Allow starting new session even while streaming
    // The ongoing stream will continue in background for the original session
    debugLog('startNewSession: Clearing messages and setting currentSessionId to null',
                'isStreaming:', isStreaming.value, 'isLoading:', isLoading.value,
                'messages count before clear:', messages.value.length)
    messages.value = []
    currentSessionId.value = null
    error.value = ''
    _isNewSessionLoading.value = false
    debugLog('startNewSession: Completed, messages count after clear:', messages.value.length)
  }

  const clearMessages = () => {
    if (confirm('Clear all messages in this session?')) {
      messages.value = []
    }
  }

  const deleteCurrentSession = async () => {
    if (!currentSessionId.value) return

    try {
      await deleteSession(currentSessionId.value)
      await fetchSessions()
      startNewSession()
      return true
    } catch (err) {
      console.error('Error deleting session:', err)
      error.value = 'Failed to delete session'
      throw err
    }
  }

  const deleteSessionById = async (sessionId) => {
    if (!sessionId) return

    try {
      await deleteSession(sessionId)
      // If deleted current session, clear it
      if (sessionId === currentSessionId.value) {
        startNewSession()
      }
      return true
    } catch (err) {
      console.error('Error deleting session:', err)
      error.value = 'Failed to delete session'
      throw err
    }
  }

  const clearError = () => {
    error.value = ''
  }

  const stopStreaming = () => {
    const sessionId = currentSessionId.value
    if (!sessionId) return

    debugLog('stopStreaming: Attempting to stop streaming for session:', sessionId)

    // Find all active streams for this session
    let stoppedCount = 0
    for (const [aiMessageId, streamData] of Object.entries(_activeStreams.value)) {
      if (streamData.sessionId === sessionId || streamData.assignedSessionId === sessionId) {
        debugLog('stopStreaming: Found active stream for session', sessionId, 'aiMessageId:', aiMessageId)

        // Call cancel function if available
        if (streamData.cancel) {
          try {
            streamData.cancel()
            debugLog('stopStreaming: Cancel function called for stream', aiMessageId)
          } catch (e) {
            console.error('stopStreaming: Error calling cancel function:', e)
          }
        }

        // Mark as aborted
        streamData.aborted = true

        // Clean up state
        const stateKey = streamData.sessionId || aiMessageId
        _loadingSessions.value[stateKey] = false
        _streamingSessions.value[stateKey] = false
        _isNewSessionLoading.value = false

        // Remove from active streams
        delete _activeStreams.value[aiMessageId]
        stoppedCount++
      }
    }

    debugLog('stopStreaming: Stopped', stoppedCount, 'stream(s) for session', sessionId)
    return stoppedCount > 0
  }

  const setCharacter = (characterId) => {
    if (characters[characterId]) {
      currentCharacterId.value = characterId
      return true
    }
    return false
  }

  // Initialize: load sessions on store creation
  fetchSessions().catch(console.error)

  return {
    // State
    messages,
    currentSessionId,
    sessions,
    isLoading,
    isStreaming,
    error,
    currentModel,
    currentCharacterId,

    // Getters
    messageCount,
    hasMessages,
    currentSession,
    lastMessage,
    currentCharacter,
    systemPrompt,

    // Actions
    streamMessage,
    fetchSessions,
    loadSession,
    startNewSession,
    stopStreaming,
    clearMessages,
    deleteCurrentSession,
    deleteSession: deleteSessionById,
    clearError,
    setCharacter
  }
})