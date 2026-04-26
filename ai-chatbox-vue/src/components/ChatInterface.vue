<template>
  <div class="chat-interface">
    <!-- Session Management Sidebar -->
    <div class="session-sidebar">
      <div class="sidebar-header">
        <h3>会话列表</h3>
        <button @click="createNewSession" class="new-session-btn" title="New Session">
          +
        </button>
      </div>

      <div class="session-list">
        <div
          v-for="session in sessions"
          :key="session.session_id"
          :class="['session-item', { active: currentSessionId === session.session_id }]"
          @click="handleSessionClick(session.session_id)"
        >
          <div class="session-icon"></div>
          <div class="session-info">
            <div class="session-name">
              {{ session.title || formatSessionId(session.session_id) }}
            </div>
            <div class="session-meta">
              {{ session.message_count }} messages · {{ formatDate(session.created_at) }}
            </div>
          </div>
          <button
            @click.stop="deleteSession(session.session_id)"
            class="delete-session-btn"
            title="Delete Session"
          >
            ×
          </button>
        </div>

        <div v-if="sessions.length === 0" class="empty-sessions">
          <div class="empty-icon"></div>
          <p>No sessions yet</p>
          <button @click="createNewSession" class="create-first-btn">
            Create First Session
          </button>
        </div>
      </div>

    </div>

    <!-- Main Chat Area -->
    <div class="chat-main">
      <!-- Chat Messages -->
      <div class="messages-container" ref="messagesContainer">
        <div v-if="!hasMessages" class="empty-chat">
          <div class="welcome-icon"></div>
          <h3>Welcome to AI Chatbox!</h3>
          <p>Start a conversation by typing a message below.</p>
          <div class="example-prompts">
            <button
              v-for="prompt in examplePrompts"
              :key="prompt"
              @click="useExamplePrompt(prompt)"
              class="prompt-btn"
            >
              {{ prompt }}
            </button>
          </div>
        </div>

        <div v-else class="messages-list">
          <div
            v-for="message in messages"
            :key="message.id"
            :class="['message', message.role]"
          >
            <div class="message-avatar" :class="message.role">
              <span v-if="message.role === 'user'" class="avatar-icon user"></span>
              <span v-else class="avatar-icon ai"></span>
            </div>
            <div class="message-content">
              <div class="message-header">
                <span class="message-role">{{ message.role === 'user' ? 'You' : 'AI Assistant' }}</span>
                <span class="message-time">
                  {{ formatTimestamp(message.timestamp) }}
                </span>
              </div>
              <div class="message-text" v-html="formatMessageContent(message.content)"></div>
            </div>
          </div>

          <div v-if="isLoading" class="loading-indicator">
            <div class="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <p>AI is thinking...</p>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="input-container">
        <div class="input-wrapper">
          <textarea
            v-model="inputMessage"
            @keydown.enter.exact.prevent="sendMessage"
            placeholder="Type your message here... (Press Enter to send, Shift+Enter for new line)"
            :disabled="isLoading"
            class="message-input"
            rows="3"
          ></textarea>
          <button
            @click="isStreaming ? stopStreaming() : sendMessage()"
            :disabled="(!inputMessage.trim() && !isStreaming) || (isLoading && !isStreaming)"
            class="send-btn"
            :class="{ 'stop-btn': isStreaming }"
          >
            <span v-if="isStreaming">Stop</span>
            <span v-else-if="!isLoading">Send</span>
            <span v-else class="sending">...</span>
          </button>
        </div>

        <div v-if="error" class="error-message">
          {{ error }}
          <button @click="clearError" class="dismiss-error">×</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUpdated, watch, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/chatStore'
import { marked } from 'marked'

// Configure marked
marked.setOptions({
  breaks: true,
  gfm: true,
  headerIds: false,
  mangle: false
})

// Chat store
const chatStore = useChatStore()

// Local state
const inputMessage = ref('')
const messagesContainer = ref<HTMLElement | null>(null)
const isUserAtBottom = ref(true) // Track if user is at bottom of chat

// Example prompts
const examplePrompts = ref([
  'Explain artificial intelligence in simple terms',
  'What is machine learning?',
  'Tell me a fun fact about technology',
  'How do neural networks work?',
  'What are the latest trends in AI?'
])

// Computed properties from store
const sessions = computed(() => chatStore.sessions)
const messages = computed(() => chatStore.messages)
const currentSessionId = computed(() => chatStore.currentSessionId)
const currentModel = computed(() => chatStore.currentModel)
const isLoading = computed(() => chatStore.isLoading)
const isStreaming = computed(() => chatStore.isStreaming)
const error = computed(() => chatStore.error)
const hasMessages = computed(() => chatStore.hasMessages)

// Methods
const scrollToBottom = () => {
  setTimeout(() => {
    if (messagesContainer.value && messagesContainer.value.scrollHeight && isUserAtBottom.value) {
      messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
    }
  }, 100)
}

// Handle scroll events to detect if user is at bottom
const handleScroll = () => {
  if (messagesContainer.value) {
    const container = messagesContainer.value
    const threshold = 50 // pixels from bottom to consider "at bottom"
    const distanceFromBottom = container.scrollHeight - container.scrollTop - container.clientHeight
    isUserAtBottom.value = distanceFromBottom <= threshold
  }
}

const formatTimestamp = (timestamp: string | Date) => {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

const formatDate = (timestamp: string | Date) => {
  const date = typeof timestamp === 'string' ? new Date(timestamp) : timestamp
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

const formatMessageContent = (content: string) => {
  if (!content) return ''
  try {
    return marked.parse(content)
  } catch (e) {
    // Fallback to plain text if markdown parsing fails
    return content.replace(/\n/g, '<br>')
  }
}

const formatSessionId = (sessionId: string) => {
  return sessionId ? `${sessionId.substring(0, 8)}...` : 'New Session'
}

// Chat actions
const sendMessage = async () => {
  const message = inputMessage.value.trim()
  if (!message) return

  try {
    // When user sends a message, always scroll to bottom
    isUserAtBottom.value = true

    // If currently streaming, stop the current stream before sending new message
    if (isStreaming.value) {
      console.log('Stopping current stream before sending new message')
      chatStore.stopStreaming()
    }

    // Clear input immediately so user knows message was sent
    inputMessage.value = ''
    await chatStore.streamMessage(message)
    scrollToBottom()
  } catch (err) {
    console.error('Error sending message:', err)
  }
}

const stopStreaming = () => {
  console.log('Stop streaming button clicked')
  chatStore.stopStreaming()
}

const createNewSession = () => {
  // When creating new session, scroll to bottom
  isUserAtBottom.value = true
  chatStore.startNewSession()
}

const handleSessionClick = async (sessionId: string) => {
  if (DEBUG) {
    console.log('ChatInterface: handleSessionClick called with sessionId:', sessionId,
                'currentSessionId before:', chatStore.currentSessionId,
                'sessions count:', sessions.value.length)
  }

  try {
    // When switching sessions, scroll to bottom
    isUserAtBottom.value = true
    if (DEBUG) {
      console.log('ChatInterface: Calling chatStore.loadSession...')
    }
    await chatStore.loadSession(sessionId)
    if (DEBUG) {
      console.log('ChatInterface: chatStore.loadSession completed',
                  'currentSessionId after:', chatStore.currentSessionId,
                  'messages count:', chatStore.messages.length)
    }
    scrollToBottom()
  } catch (err) {
    console.error('ChatInterface: Error switching session:', err)
  }
}

const deleteSession = async (sessionId: string) => {
  if (!confirm('Delete this session and all its messages?')) return

  try {
    await chatStore.deleteSession(sessionId)
    // Refresh sessions list
    await chatStore.fetchSessions()
  } catch (err) {
    console.error('Error deleting session:', err)
  }
}

const refreshSessions = async () => {
  try {
    await chatStore.fetchSessions()
  } catch (err) {
    console.error('Error refreshing sessions:', err)
  }
}

const clearError = () => {
  chatStore.clearError()
}

const useExamplePrompt = (prompt: string) => {
  inputMessage.value = prompt
}

// Auto-scroll when messages change
watch(messages, () => {
  scrollToBottom()
}, { deep: true })

// Watch for session changes for debugging
const DEBUG = false // Set to true to enable verbose logging
watch(currentSessionId, (newId, oldId) => {
  if (DEBUG) {
    console.log('ChatInterface: currentSessionId changed from', oldId, 'to', newId,
                'sessions count:', sessions.value.length)
  }
}, { immediate: true })

// Debug: watch isStreaming changes to diagnose button state
watch(isStreaming, (newValue, oldValue) => {
  console.log('ChatInterface: isStreaming changed from', oldValue, 'to', newValue,
              'currentSessionId:', currentSessionId.value)
})

// Debug: watch isLoading changes
watch(isLoading, (newValue, oldValue) => {
  console.log('ChatInterface: isLoading changed from', oldValue, 'to', newValue,
              'isStreaming:', isStreaming.value)
})

// Initialize
onMounted(() => {
  // Load sessions if not already loaded
  if (sessions.value.length === 0) {
    chatStore.fetchSessions().catch(console.error)
  }
  scrollToBottom()

  // Add scroll event listener
  if (messagesContainer.value) {
    messagesContainer.value.addEventListener('scroll', handleScroll)
  }
})

// Clean up
onUnmounted(() => {
  if (messagesContainer.value) {
    messagesContainer.value.removeEventListener('scroll', handleScroll)
  }
})
</script>

<style scoped>
.chat-interface {
  display: flex;
  flex: 1;
  height: 100%;
  background: white;
  border-radius: 15px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(156, 137, 184, 0.1);
  font-family: 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
}

.session-sidebar {
  width: 300px;
  background: linear-gradient(135deg, #F8F5F2 0%, #F0F0F0 100%);
  border-right: 1px solid #E0E0E0;
  display: flex;
  flex-direction: column;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #E0E0E0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.sidebar-header h3 {
  margin: 0;
  color: #9C89B8;
  font-size: 1.2rem;
  font-weight: 600;
}

.new-session-btn {
  background: linear-gradient(135deg, #9C89B8 0%, #B8D0EB 100%);
  color: white;
  border: none;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 1.2rem;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.new-session-btn:hover {
  transform: scale(1.1);
  box-shadow: 0 5px 15px rgba(156, 137, 184, 0.4);
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
}

.session-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  margin-bottom: 10px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 15px;
  cursor: pointer;
  transition: all 0.3s ease;
  border: 2px solid transparent;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.9);
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(156, 137, 184, 0.2);
}

.session-item.active {
  background: rgba(156, 137, 184, 0.1);
  border-color: #9C89B8;
}

.session-item.active .session-icon {
  border-color: #9C89B8;
  background: rgba(156, 137, 184, 0.2);
}

.session-icon {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
  transition: all 0.3s ease;
  border: 2px solid rgba(156, 137, 184, 0.4);
  background: transparent;
}

.session-info {
  flex: 1;
  min-width: 0;
}

.session-name {
  font-weight: bold;
  color: #9C89B8;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-meta {
  font-size: 0.8rem;
  color: #888;
}

.delete-session-btn {
  background: none;
  border: none;
  color: #9C89B8;
  cursor: pointer;
  font-size: 1rem;
  opacity: 0.7;
  transition: all 0.3s ease;
  flex-shrink: 0;
  padding: 5px;
}

.delete-session-btn:hover {
  opacity: 1;
  transform: scale(1.2);
}

.empty-sessions {
  text-align: center;
  padding: 40px 20px;
  color: #6c757d;
}

.empty-icon {
  width: 48px;
  height: 48px;
  margin: 0 auto 15px;
  border-radius: 50%;
  background: #dee2e6;
  opacity: 0.5;
}

.empty-sessions p {
  margin-bottom: 20px;
}

.create-first-btn {
  background: linear-gradient(135deg, #9C89B8 0%, #B8D0EB 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 20px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.3s ease;
}

.create-first-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(156, 137, 184, 0.4);
}

.sidebar-footer {
  padding: 15px;
  border-top: 1px solid #E0E0E0;
  font-size: 0.9rem;
  color: #666;
}

.sidebar-footer > * {
  width: 100%;
}

.model-info {
  display: flex;
  gap: 5px;
}

.model-label {
  color: #888;
}

.model-name {
  color: #9C89B8;
  font-weight: bold;
}

.total-sessions {
  background: rgba(156, 137, 184, 0.1);
  padding: 4px 10px;
  border-radius: 10px;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #F8F5F2 0%, #F0F0F0 100%);
}

.messages-container {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: rgba(255, 255, 255, 0.7);
}

.empty-chat {
  text-align: center;
  padding: 60px 20px;
  color: #6c757d;
}

.welcome-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto 20px;
  border-radius: 50%;
  background: linear-gradient(135deg, #9C89B8 0%, #B8D0EB 100%);
  opacity: 0.8;
}

.empty-chat h3 {
  margin: 20px 0 10px;
  font-size: 1.5rem;
}

.empty-chat p {
  color: #888;
  margin-bottom: 30px;
}

.example-prompts {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  justify-content: center;
  max-width: 600px;
  margin: 0 auto;
}

.prompt-btn {
  background: rgba(156, 137, 184, 0.1);
  border: 1px solid #9C89B8;
  color: #9C89B8;
  padding: 10px 15px;
  border-radius: 15px;
  cursor: pointer;
  font-family: inherit;
  font-weight: 500;
  transition: all 0.3s ease;
  flex: 1;
  min-width: 150px;
  max-width: 250px;
}

.prompt-btn:hover {
  background: rgba(156, 137, 184, 0.2);
  transform: translateY(-2px);
}

.messages-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.message {
  display: flex;
  gap: 15px;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #f8f9fa;
  border: 2px solid #dee2e6;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}

.message-avatar.user {
  border-color: #495057;
  background: #495057;
}

.message-avatar.ai {
  border-color: #9C89B8;
  background: #9C89B8;
}

.avatar-icon {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: white;
}

.avatar-icon.user {
  background: white;
}

.avatar-icon.ai {
  background: white;
}

.message-content {
  flex: 1;
  background: white;
  padding: 15px;
  border-radius: 15px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
  max-width: 70%;
}

.message.user .message-content {
  background: linear-gradient(135deg, #e6f7ff 0%, #b3e0ff 100%);
  text-align: right;
}

.message-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  font-size: 0.9rem;
}

.message-role {
  font-weight: bold;
  color: #9C89B8;
}

.message.user .message-role {
  color: #5D8AA8;
}

.message-time {
  color: #888;
  font-size: 0.8rem;
}

.message-text {
  line-height: 1.6;
  color: #333;
}

.message-text :deep(code) {
  background: #f4f4f4;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'SF Mono', Monaco, Consolas, monospace;
  font-size: 0.85em;
  color: #e83e8c;
}

.message-text :deep(pre) {
  background: #2d2d2d;
  color: #f8f8f2;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 12px 0;
}

.message-text :deep(pre code) {
  background: transparent;
  color: inherit;
  padding: 0;
  font-size: 0.9em;
}

.message-text :deep(strong) {
  color: #7A6B9C;
  font-weight: 600;
}

.message-text :deep(em) {
  color: #9C89B8;
  font-style: italic;
}

.message-text :deep(h1),
.message-text :deep(h2),
.message-text :deep(h3),
.message-text :deep(h4),
.message-text :deep(h5),
.message-text :deep(h6) {
  margin: 16px 0 12px;
  color: #333;
  font-weight: 600;
}

.message-text :deep(h1) { font-size: 1.5em; }
.message-text :deep(h2) { font-size: 1.3em; }
.message-text :deep(h3) { font-size: 1.15em; }

.message-text :deep(p) {
  margin: 8px 0;
}

.message-text :deep(ul),
.message-text :deep(ol) {
  margin: 12px 0;
  padding-left: 24px;
}

.message-text :deep(li) {
  margin: 4px 0;
}

.message-text :deep(blockquote) {
  border-left: 4px solid #9C89B8;
  padding-left: 16px;
  margin: 12px 0;
  color: #666;
  font-style: italic;
}

.message-text :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
}

.message-text :deep(th),
.message-text :deep(td) {
  padding: 8px 12px;
  border: 1px solid #e0e0e0;
  text-align: left;
}

.message-text :deep(th) {
  background: #f8f5f2;
  font-weight: 600;
}

.message-text :deep(tr:nth-child(even)) {
  background: #fafafa;
}

.message-text :deep(a) {
  color: #9C89B8;
  text-decoration: none;
}

.message-text :deep(a:hover) {
  text-decoration: underline;
}

.message-text :deep(hr) {
  border: none;
  border-top: 1px solid #e0e0e0;
  margin: 16px 0;
}

.loading-indicator {
  text-align: center;
  padding: 20px;
  color: #9C89B8;
}

.typing-dots {
  display: inline-block;
  margin-right: 10px;
}

.typing-dots span {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #9C89B8;
  margin: 0 2px;
  animation: typing 1.4s infinite;
}

.typing-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.input-container {
  padding: 20px;
  background: linear-gradient(180deg, rgba(156, 137, 184, 0.05) 0%, rgba(156, 137, 184, 0.12) 100%);
  border-top: 1px solid rgba(156, 137, 184, 0.2);
  box-shadow: 0 -4px 20px rgba(156, 137, 184, 0.08);
}

.input-wrapper {
  position: relative;
  display: flex;
  flex-direction: column;
}

.message-input {
  width: 100%;
  padding: 15px 80px 15px 15px;
  border: 2px solid #9C89B8;
  border-radius: 15px;
  font-family: inherit;
  font-size: 1rem;
  resize: vertical;
  background: rgba(255, 255, 255, 0.9);
  transition: all 0.3s ease;
}

.message-input:focus {
  outline: none;
  border-color: #9C89B8;
  box-shadow: 0 0 0 3px rgba(156, 137, 184, 0.3);
}

.message-input:disabled {
  background: #f0f0f0;
  cursor: not-allowed;
}

.send-btn {
  position: absolute;
  bottom: 12px;
  right: 12px;
  padding: 8px 16px;
  border: none;
  border-radius: 10px;
  font-family: inherit;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.3s ease;
  background: linear-gradient(135deg, #9C89B8 0%, #7A6B9C 100%);
  color: white;
}

.send-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(156, 137, 184, 0.4);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.stop-btn {
  background: linear-gradient(135deg, #ff6b6b 0%, #ee5a52 100%) !important;
}

.stop-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #ff5252 0%, #e53935 100%) !important;
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(229, 57, 53, 0.4);
}

.error-message {
  background: rgba(156, 137, 184, 0.2);
  border: 1px solid #9C89B8;
  color: #d32f2f;
  padding: 12px;
  border-radius: 10px;
  margin-top: 10px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dismiss-error {
  background: none;
  border: none;
  color: #9C89B8;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0 5px;
}

@media (max-width: 1024px) {
  .chat-interface {
    flex-direction: column;
    height: auto;
  }

  .session-sidebar {
    width: 100%;
    height: 250px;
    border-right: none;
    border-bottom: 3px dashed #9C89B8;
  }

  .chat-main {
    height: calc(100vh - 430px);
  }
}

@media (max-width: 768px) {
  .chat-interface {
    border-radius: 0;
  }

  .message-content {
    max-width: 85%;
  }

  .example-prompts {
    flex-direction: column;
    align-items: center;
  }

  .prompt-btn {
    max-width: 100%;
  }

  .status-info {
    flex-direction: column;
    gap: 5px;
  }
}
</style>