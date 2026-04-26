<template>
  <div class="graph-view">
    <!-- Control Panel -->
    <div class="control-panel">
      <div class="panel-header">
        <h3>Knowledge Graph</h3>
        <div class="view-switch">
          <button
            @click="switchView('session')"
            :class="['view-btn', { active: currentView === 'session' }]"
            title="Session Graph"
          >
            Session
          </button>
          <button
            @click="switchView('global')"
            :class="['view-btn', { active: currentView === 'global' }]"
            title="Global Graph"
          >
            Global
          </button>
        </div>
      </div>

      <!-- Session Selection (only in session view) -->
      <div v-if="currentView === 'session'" class="session-selection-section">
        <div class="session-selection-header">
          <label class="session-label">Session:</label>
          <select
            v-model="chatStore.currentSessionId"
            @change="onSessionChange"
            class="session-select"
            :disabled="sessions.length === 0"
          >
            <option value="" disabled>Select a session</option>
            <option
              v-for="session in sessions"
              :key="session.session_id"
              :value="session.session_id"
            >
              {{ session.title || (session.session_id || '').substring(0, 8) + '...' }} ({{ formatSessionDate(session.created_at) }})
            </option>
          </select>
        </div>
        <div v-if="sessions.length === 0" class="no-sessions-message">
          No sessions available. Start chatting to create sessions.
        </div>
      </div>

      <!-- Search and Filter -->
      <div class="search-section">
        <div class="search-input-wrapper">
          <input
            v-model="searchQuery"
            @input="handleSearch"
            placeholder="Search nodes..."
            class="search-input"
          />
          <span class="search-icon"></span>
        </div>
        <div class="filter-section">
          <div class="filter-group">
            <label class="filter-label">Node Groups:</label>
            <div class="filter-options">
              <label v-for="group in availableGroups" :key="group" class="filter-option">
                <input
                  type="checkbox"
                  v-model="selectedGroups"
                  :value="group"
                  @change="applyFilters"
                />
                <span class="filter-label-text">{{ group }}</span>
                <span class="group-color" :style="{ backgroundColor: getGroupColor(group) }"></span>
              </label>
            </div>
          </div>
        </div>
      </div>

      <!-- Stats -->
      <div class="stats-section">
        <div class="stat-card">
          <div class="stat-icon">●</div>
          <div class="stat-info">
            <div class="stat-value">{{ nodeCount }}</div>
            <div class="stat-label">Nodes</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">➔</div>
          <div class="stat-info">
            <div class="stat-value">{{ edgeCount }}</div>
            <div class="stat-label">Edges</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon"></div>
          <div class="stat-info">
            <div class="stat-value">{{ lastUpdatedRelative }}</div>
            <div class="stat-label">Updated</div>
          </div>
        </div>
      </div>

      <!-- Selected Node Details -->
      <div v-if="selectedNode" class="node-details">
        <div class="details-header">
          <h4>Node Details</h4>
          <button @click="deselectNode" class="close-details" title="Close">×</button>
        </div>
        <div class="details-content">
          <div class="node-header">
            <div class="node-label-icon">
              <span class="node-label">{{ selectedNode.label }}</span>
            </div>
            <span class="node-group-badge" :style="{ backgroundColor: getGroupColor(selectedNode.group) }">
              {{ selectedNode.group }}
            </span>
          </div>
          <div v-if="selectedNode.title" class="node-description">
            {{ selectedNode.title }}
          </div>
          <div class="node-meta">
            <div class="meta-item">
              <span class="meta-label">ID:</span>
              <span class="meta-value">{{ selectedNode.id }}</span>
            </div>
            <div v-if="selectedNode.value" class="meta-item">
              <span class="meta-label">提及次数:</span>
              <span class="meta-value">{{ selectedNode.value }}</span>
            </div>
          </div>
          <div v-if="connectedNodes.length > 0" class="node-connections">
            <h5>Connections ({{ connectedNodes.length }})</h5>
            <div class="connections-list">
              <div
                v-for="edge in connectedEdges"
                :key="`${edge.from}-${edge.to}`"
                class="connection-item"
              >
                <div class="connection-info">
                  <span class="connection-label">{{ edge.label || 'related' }}</span>
                  <span class="connection-direction">→</span>
                  <span class="connection-node">{{ getNodeLabel(edge.to === selectedNode.id ? edge.from : edge.to) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>


      <!-- Neo4j Connection Test -->
      <div class="test-connection-section">
        <button
          @click="testNeo4jConnection"
          :disabled="isTestingConnection"
          class="test-btn"
          :class="{ success: neo4jStatus?.connected, error: neo4jStatus && !neo4jStatus.connected }"
        >
          <span v-if="isTestingConnection">Testing...</span>
          <span v-else-if="neo4jStatus">
            {{ neo4jStatus.connected ? '✓ Neo4j Connected' : '✗ Neo4j Disconnected' }}
          </span>
          <span v-else>Test Neo4j Connection</span>
        </button>
      </div>

      <!-- Manual Reanalysis Section -->
      <div class="reanalysis-section">
        <button
          @click="reanalyzeGraph"
          :disabled="isReanalyzing || !chatStore.currentSessionId"
          class="test-btn reanalysis-btn"
          title="手动重新构建当前会话的知识图谱（完整分析所有对话历史）"
        >
          <span v-if="isReanalyzing">正在重建...</span>
          <span v-else-if="chatStore.currentSessionId">Rebuild Session Graph</span>
          <span v-else>Select a Session</span>
        </button>
        <div v-if="reanalysisResult" class="reanalysis-result">
          <div class="reanalysis-stats">
            <div class="stat-row">
              <span class="stat-name">分析消息数:</span>
              <span class="stat-value">{{ reanalysisResult.total_messages }}</span>
            </div>
            <div class="stat-row">
              <span class="stat-name">提取实体:</span>
              <span class="stat-value" :class="{ 'has-data': reanalysisResult.entities_extracted > 0 }">
                {{ reanalysisResult.entities_extracted }}
              </span>
            </div>
            <div class="stat-row">
              <span class="stat-name">提取关系:</span>
              <span class="stat-value" :class="{ 'has-data': reanalysisResult.relationships_extracted > 0 }">
                {{ reanalysisResult.relationships_extracted }}
              </span>
            </div>
            <div class="stat-row">
              <span class="stat-name">耗时:</span>
              <span class="stat-value">{{ reanalysisResult.elapsed_time.toFixed(2) }}s</span>
            </div>
          </div>
        </div>
      </div>

    </div>

    <!-- Graph Container -->
    <div class="graph-container">
      <div ref="graphContainer" class="graph-canvas"></div>
      <div class="graph-controls">
        <button @click="fitGraph" class="graph-control-btn" title="Fit view to all nodes">
          <span class="control-icon">⎈</span>
          <span class="control-label">Fit View</span>
        </button>
      </div>
      <div v-if="!hasGraphData && !isLoading" class="empty-graph">
        <div class="empty-icon"></div>
        <h3>{{ emptyGraphTitle }}</h3>
        <p>{{ emptyGraphMessage }}</p>
        <button
          v-if="currentView === 'global' || (currentView === 'session' && chatStore.currentSessionId)"
          @click="loadDemoGraph"
          class="demo-btn"
        >
          Load Demo Graph
        </button>
      </div>
      <div v-if="graphError" class="error-message">
        {{ graphError }}
        <button @click="retryLoadGraph" class="retry-btn">Retry</button>
      </div>
      <div v-if="isLoading" class="loading-overlay">
        <div class="loading-spinner"></div>
        <p>Loading graph data...</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, shallowRef, computed, onMounted, onUnmounted, watch, markRaw } from 'vue'
import { Network } from 'vis-network/standalone'
import { DataSet } from 'vis-data'
import { useGraphStore } from '@/stores/graphStore'
import { useChatStore } from '@/stores/chatStore'
import { useConfigStore } from '@/stores/configStore'
import { checkNeo4jStatus, reanalyzeSessionGraph } from '@/api'

// Debug logging helper with module tag
const DEBUG = true // Set to true for debugging animation performance
const debugLog = (module: string, ...args: any[]) => {
  if (DEBUG) {
    console.log(`[GraphView:${module}]`, ...args)
  }
}
const debugWarn = (module: string, ...args: any[]) => {
  if (DEBUG) {
    console.warn(`[GraphView:${module}]`, ...args)
  }
}

// Stores
const graphStore = useGraphStore()
const chatStore = useChatStore()
const configStore = useConfigStore()

// Refs
const graphContainer = ref<HTMLElement | null>(null)
const network = shallowRef<any>(null)
const currentView = ref<'session' | 'global'>('session')
const searchQuery = ref('')
const selectedGroups = ref<string[]>([])
const selectedNode = ref<any>(null)


// Neo4j connection test state
const isTestingConnection = ref(false)
const neo4jStatus = ref<{ connected: boolean; message: string; uri?: string } | null>(null)

// Manual reanalysis state
const isReanalyzing = ref(false)
const reanalysisResult = ref<any>(null)

// Computed properties
const isLoading = computed(() => graphStore.isLoading)
const graphError = computed(() => graphStore.error)

// Active graph data based on current view
const activeGraphData = computed(() => {
  return currentView.value === 'global'
    ? graphStore.globalGraph
    : graphStore.currentGraph
})

const nodeCount = computed(() => activeGraphData.value.nodes?.length || 0)
const edgeCount = computed(() => activeGraphData.value.edges?.length || 0)
const hasGraphData = computed(() => nodeCount.value > 0)

const emptyGraphTitle = computed(() => {
  if (currentView.value === 'global') {
    return 'Global Knowledge Graph'
  } else {
    // Session view
    if (!chatStore.currentSessionId) {
      if (sessions.value.length === 0) {
        return 'No Sessions Available'
      } else {
        return 'Select a Session'
      }
    }
    return 'Session Knowledge Graph'
  }
})

const emptyGraphMessage = computed(() => {
  if (currentView.value === 'global') {
    return 'Global knowledge graph is empty. Chat in any session to add knowledge!'
  } else {
    // Session view
    if (!chatStore.currentSessionId) {
      if (sessions.value.length === 0) {
        return 'No sessions available. Start chatting to create a session!'
      } else {
        return 'Select a session to view its knowledge graph.'
      }
    }
    return 'Start chatting to build your knowledge graph!'
  }
})

const lastUpdatedRelative = computed(() => {
  if (!graphStore.lastUpdated) return 'Never'
  const now = new Date()
  const diffMs = now.getTime() - new Date(graphStore.lastUpdated).getTime()
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  return `${Math.floor(diffHours / 24)}d ago`
})

const availableGroups = computed(() => {
  const groups = new Set<string>()
  activeGraphData.value.nodes?.forEach((node: any) => {
    if (node.group) groups.add(node.group)
  })
  return Array.from(groups)
})

const sessions = computed(() => {
  const storeSessions = chatStore.sessions
  debugLog('computed', 'sessions computed called: storeSessions =', storeSessions, 'type:', typeof storeSessions, 'isArray:', Array.isArray(storeSessions))

  if (!storeSessions || !Array.isArray(storeSessions) || storeSessions.length === 0) {
    debugLog('computed', 'sessions computed: No sessions in store')
    return []
  }

  debugLog('computed', 'sessions computed: raw sessions count =', storeSessions.length, 'first session:', storeSessions[0])

  // Filter out any sessions without session_id
  const filtered = storeSessions.filter(session => {
    const hasId = session?.session_id
    if (!hasId) {
      debugWarn('computed', 'sessions computed: Session without id:', session)
    }
    return hasId
  })

  debugLog('computed', 'sessions computed: filtered count =', filtered.length)
  if (filtered.length === 0 && storeSessions.length > 0) {
    debugWarn('computed', 'sessions computed: All sessions filtered out! Raw sessions:', storeSessions)
  }

  return filtered
})

const connectedEdges = computed(() => {
  if (!selectedNode.value) return []
  return activeGraphData.value.edges.filter(
    (edge: any) => edge.from === selectedNode.value.id || edge.to === selectedNode.value.id
  )
})

const connectedNodes = computed(() => {
  if (!selectedNode.value) return []
  const nodeIds = new Set<number>()
  connectedEdges.value.forEach((edge: any) => {
    if (edge.from === selectedNode.value.id) nodeIds.add(edge.to)
    if (edge.to === selectedNode.value.id) nodeIds.add(edge.from)
  })
  return Array.from(nodeIds).map(id =>
    activeGraphData.value.nodes.find((node: any) => node.id === id)
  ).filter(Boolean)
})

// Methods
const getGroupColor = (group: string) => {
  const colorMap: Record<string, string> = {
    'concept': '#6B5B95',      // 深紫色
    'technique': '#4A7C9B',    // 深青蓝色
    'application': '#2E8B57',  // 深绿色
    'person': '#D2691E',       // 深橙色
    'organization': '#C44536', // 深红色
    'location': '#228B22',     // 森林绿
    'tool': '#5D4E75',         // 深紫灰
    'event': '#B8860B',        // 深金色
    'default': '#5A5A5A'       // 深灰色
  }
  return colorMap[group] || colorMap.default
}


const getNodeLabel = (nodeId: number) => {
  const node = activeGraphData.value.nodes.find((n: any) => n.id === nodeId)
  return node?.label || `Node ${nodeId}`
}

const formatSessionDate = (dateString: string | Date) => {
  if (!dateString) return ''
  const date = typeof dateString === 'string' ? new Date(dateString) : dateString
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

const onSessionChange = () => {
  debugLog('onSessionChange', 'onSessionChange called, currentSessionId:', chatStore.currentSessionId,
              'currentView:', currentView.value,
              'sessions count:', sessions.value.length)

  if (!chatStore.currentSessionId) {
    debugLog('onSessionChange', 'onSessionChange: No session selected')
    return
  }

  // Verify the selected session exists in sessions list
  const selectedSession = sessions.value.find(s => s.session_id === chatStore.currentSessionId)
  if (!selectedSession) {
    debugWarn('onSessionChange', 'onSessionChange: Selected session not found in sessions list:', chatStore.currentSessionId)
    debugWarn('onSessionChange', 'Available sessions:', sessions.value.map(s => s.session_id))
    return
  }

  debugLog('onSessionChange', 'onSessionChange: Loading session', chatStore.currentSessionId)

  // Load session messages into chat store
  chatStore.loadSession(chatStore.currentSessionId).catch(err => {
    debugWarn('onSessionChange', 'onSessionChange: Failed to load session messages:', err)
  })

  // Fetch graph data if in session view
  if (currentView.value === 'session') {
    debugLog('onSessionChange', 'onSessionChange: Fetching session graph for', chatStore.currentSessionId)
    graphStore.fetchSessionGraph(chatStore.currentSessionId)
  }
}

// Helper function to prepare graph data for vis-network
const prepareGraphData = (rawNodes: any[], rawEdges: any[]) => {
  // First, collect statistics about node values for adaptive sizing
  const allValues = rawNodes
    .map((node: any) => node.value || node.mention_count || 1)
    .filter((value: number) => value > 0)

  const maxValue = allValues.length > 0
    ? Math.max(...allValues)
    : 1
  const minValue = allValues.length > 0
    ? Math.min(...allValues)
    : 1

  // Adaptive sizing parameters based on data range
  const baseSize = 24
  const maxSize = 70
  let scaleFunction: (count: number) => number

  // Check if all values are the same (no variation)
  if (minValue === maxValue) {
    // All nodes have the same value - use middle size
    const fixedSize = baseSize + (maxSize - baseSize) / 2
    scaleFunction = () => fixedSize
  } else if (maxValue <= 3) {
    // For very small values (1-3), use linear scaling for maximum contrast
    const scale = (maxSize - baseSize) / (maxValue - minValue)
    scaleFunction = (value: number) => {
      const normalized = Math.max(minValue, Math.min(value, maxValue))
      return baseSize + (normalized - minValue) * scale
    }
  } else if (maxValue <= 10) {
    // For moderate values (4-10), use square root scaling
    const minSqrt = Math.sqrt(minValue)
    const maxSqrt = Math.sqrt(maxValue)
    const scale = (maxSize - baseSize) / (maxSqrt - minSqrt)
    scaleFunction = (value: number) => {
      const sqrtVal = Math.sqrt(Math.max(minValue, Math.min(value, maxValue)))
      return baseSize + (sqrtVal - minSqrt) * scale
    }
  } else {
    // For larger values, use logarithmic scaling (base 2)
    const minLog = Math.log2(minValue)
    const maxLog = Math.log2(maxValue)
    const scale = (maxSize - baseSize) / (maxLog - minLog)
    scaleFunction = (value: number) => {
      const logVal = Math.log2(Math.max(minValue, Math.min(value, maxValue)))
      return baseSize + (logVal - minLog) * scale
    }
  }

  // Prepare nodes
  const nodes = new DataSet<any>(
    rawNodes.map((node: any) => {
      const nodeValue = node.value || node.mention_count || 1
      let nodeSize = scaleFunction(nodeValue)
      nodeSize = Math.max(baseSize, Math.min(maxSize, nodeSize))

      return {
        ...node,
        color: {
          background: getGroupColor(node.group || 'default'),
          border: '#FFFFFF',
          highlight: {
            background: '#FFD700',
            border: '#FFA500'
          }
        },
        font: {
          color: '#000000',
          size: 16,
          face: 'Inter, "Segoe UI", Roboto, Arial, sans-serif',
          strokeWidth: 2,
          strokeColor: '#FFFFFF'
        },
        shape: 'dot',
        size: nodeSize,
        value: node.value,
        mention_count: node.mention_count,
        importance: node.importance,
        title: node.title +
          (node.mention_count ? `\n\nMentioned ${node.mention_count} time${node.mention_count > 1 ? 's' : ''}` : '') +
          (node.importance ? `\nImportance: ${node.importance.toFixed(1)}/5` : '')
      }
    })
  )

  // Prepare edges
  const edges = new DataSet<any>(
    rawEdges.map((edge: any) => ({
      ...edge,
      color: {
        color: '#9C89B8',
        highlight: '#7A6B9C',
        hover: '#B8D0EB'
      },
      arrows: 'to',
      smooth: true
    }))
  )

  return { nodes, edges }
}

const switchView = (view: 'session' | 'global') => {
  currentView.value = view
  graphStore.clearError()
  selectedNode.value = null  // Clear selected node when switching views

  if (view === 'session') {
    // Check if we have a current session
    if (chatStore.currentSessionId) {
      graphStore.fetchSessionGraph(chatStore.currentSessionId)
    } else if (sessions.value.length > 0) {
      // Auto-select first available session
      const firstSession = sessions.value[0]
      chatStore.currentSessionId = firstSession.session_id
      graphStore.fetchSessionGraph(firstSession.session_id)
    } else {
      // No sessions available, switch to global view
      currentView.value = 'global'
      graphStore.fetchGlobalGraphData()
    }
  } else if (view === 'global') {
    graphStore.fetchGlobalGraphData()
  }
}

const handleSearch = () => {
  debugLog('search', 'handleSearch called, query:', searchQuery.value)

  if (!network.value) {
    debugWarn('search', 'Network not initialized')
    // Try to initialize if we have data
    if (activeGraphData.value.nodes?.length > 0) {
      debugLog('search', 'Initializing network')
      initGraph()
    }
    return
  }

  if (searchQuery.value.trim() === '') {
    debugLog('search', 'Clearing selection (empty query)')
    try {
      network.value.setSelection({ nodes: [], edges: [] })
    } catch (err) {
      debugWarn('search', 'clear selection failed, error:', err)
      // Diagnostic on failure
      const diagnosis = diagnoseNetwork()
      debugLog('search', 'Network diagnosis after clear failure:', diagnosis)
    }
    return
  }

  const query = searchQuery.value.toLowerCase()
  const matchedNodes = activeGraphData.value.nodes.filter((node: any) =>
    node.label?.toLowerCase().includes(query) ||
    node.title?.toLowerCase().includes(query)
  )
  debugLog('search', 'Matched nodes:', matchedNodes.length)

  if (matchedNodes.length > 0) {
    const nodeIds = matchedNodes.map((node: any) => node.id)

    try {
      network.value.setSelection({ nodes: nodeIds, edges: [] })
      network.value.fit({ nodes: nodeIds, animation: true })
    } catch (err) {
      debugWarn('search', 'set selection and fit failed, error:', err)
      // Diagnostic on failure
      const diagnosis = diagnoseNetwork()
      debugLog('search', 'Network diagnosis after selection failure:', diagnosis)
      // Single retry attempt
      if (activeGraphData.value.nodes?.length > 0) {
        debugLog('search', 'Reinitializing network after selection failure')
        initGraph()
        if (network.value) {
          try {
            network.value.setSelection({ nodes: nodeIds, edges: [] })
            network.value.fit({ nodes: nodeIds, animation: true })
          } catch (retryErr) {
            debugWarn('search', 'set selection and fit failed after reinitialization, error:', retryErr)
          }
        }
      }
    }
  } else {
    debugLog('search', 'No nodes matched query')
    try {
      network.value.setSelection({ nodes: [], edges: [] })
    } catch (err) {
      debugWarn('search', 'clear selection failed (no matches), error:', err)
    }
  }
}

const applyFilters = () => {
  if (!network.value) return

  const nodes = new DataSet<any>(
    activeGraphData.value.nodes.map((node: any) => ({
      ...node,
      hidden: selectedGroups.value.length > 0 && !selectedGroups.value.includes(node.group)
    }))
  )

  // @ts-ignore
  network.value.setData({
    nodes,
    edges: new DataSet<any>(activeGraphData.value.edges)
  })
}


const fitGraph = () => {
  if (network.value) {
    network.value.fit({ animation: true })
  }
}


const loadDemoGraph = () => {
  graphStore.simulateGraphUpdate()
}

const retryLoadGraph = () => {
  graphStore.clearError()
  if (currentView.value === 'global') {
    graphStore.fetchGlobalGraphData()
  } else if (currentView.value === 'session' && chatStore.currentSessionId) {
    graphStore.fetchSessionGraph(chatStore.currentSessionId)
  }
}

const testNeo4jConnection = async () => {
  isTestingConnection.value = true
  neo4jStatus.value = null
  try {
    const result = await checkNeo4jStatus()
    neo4jStatus.value = result
  } catch (err: any) {
    neo4jStatus.value = {
      connected: false,
      message: `Connection failed: ${err.message || 'Unknown error'}`,
      uri: ''
    }
  } finally {
    isTestingConnection.value = false
  }
}

const reanalyzeGraph = async () => {
  if (!chatStore.currentSessionId) {
        return
  }

  isReanalyzing.value = true
  reanalysisResult.value = null

  try {
    const config = configStore.apiConfig
    debugLog('reanalyze', 'Reanalyze using config:', config)

    const result = await reanalyzeSessionGraph(
      chatStore.currentSessionId,
      50, // limit
      config.apiKey,
      config.baseUrl,
      config.model
    )
    debugLog('reanalyze', 'Reanalysis API result:', result)
    reanalysisResult.value = result

    // 重新加载图形数据
    await graphStore.fetchSessionGraph(chatStore.currentSessionId)
  } catch (err: any) {
    debugWarn('reanalyze', 'Reanalysis failed:', err)
  } finally {
    isReanalyzing.value = false
  }
}

// Enhanced network diagnosis function with multiple validation methods
const diagnoseNetwork = (): { valid: boolean; checks: Record<string, any> } => {
  const checks: Record<string, any> = {
    networkExists: !!network.value,
    containerExists: !!graphContainer.value,
    networkType: typeof network.value,
    isNetworkObject: network.value && typeof network.value === 'object',
    networkConstructor: network.value?.constructor?.name,
    timestamp: new Date().toISOString()
  }

  if (!network.value) {
    debugLog('diagnose', 'Network is null or undefined', checks)
    return { valid: false, checks }
  }

  // Check container state
  if (graphContainer.value) {
    checks.containerWidth = graphContainer.value.offsetWidth
    checks.containerHeight = graphContainer.value.offsetHeight
    checks.containerVisible = checks.containerWidth > 0 && checks.containerHeight > 0
    checks.containerParent = graphContainer.value.parentElement?.tagName
    checks.containerInDOM = document.body.contains(graphContainer.value)
  } else {
    checks.containerVisible = false
    checks.containerInDOM = false
  }

  // Test 1: Read property access test
  let readCheckPass = false
  try {
    // Try to read various properties
    const canvas = network.value.canvas
    const body = network.value.body
    const options = network.value.options
    checks.readCanvas = canvas !== undefined
    checks.readBody = body !== undefined
    checks.readOptions = options !== undefined
    checks.readCheckPass = true
    readCheckPass = true
    debugLog('diagnose-read', 'Read check PASS - successfully read network properties')
  } catch (err) {
    checks.readCheckPass = false
    checks.readError = (err as any)?.message || String(err)
    debugLog('diagnose-read', 'Read check FAIL - cannot read network properties:', err)
  }

  // Test 2: Method existence test
  let methodCheckPass = false
  try {
    checks.hasSetSelection = typeof network.value.setSelection === 'function'
    checks.hasFit = typeof network.value.fit === 'function'
    checks.hasSetData = typeof network.value.setData === 'function'
    checks.hasDestroy = typeof network.value.destroy === 'function'
    checks.hasGetSelection = typeof network.value.getSelection === 'function'
    methodCheckPass = checks.hasSetSelection && checks.hasFit && checks.hasSetData && checks.hasDestroy && checks.hasGetSelection
    checks.methodCheckPass = methodCheckPass
    if (methodCheckPass) {
      debugLog('diagnose-method', 'Method check PASS - all required methods exist')
    } else {
      debugLog('diagnose-method', 'Method check FAIL - missing some methods:', checks)
    }
  } catch (err) {
    checks.methodCheckPass = false
    checks.methodError = (err as any)?.message || String(err)
    debugLog('diagnose-method', 'Method check FAIL - error checking methods:', err)
  }

  // Test 3: Functional test - call getSelection (harmless)
  let functionalCheckPass = false
  try {
    const selection = network.value.getSelection()
    checks.getSelectionSucceeded = true
    checks.selection = selection
    functionalCheckPass = true
    debugLog('diagnose-functional', 'Functional check PASS - getSelection succeeded:', { selection })
  } catch (err) {
    checks.getSelectionSucceeded = false
    checks.getSelectionError = (err as any)?.message || String(err)
    checks.getSelectionErrorStack = (err as any)?.stack
    functionalCheckPass = false
    debugLog('diagnose-functional', 'Functional check FAIL - getSelection failed:', err)
  }

  // Test 4: Reflection test
  try {
    const keys = Object.keys(network.value)
    checks.publicKeysCount = keys.length
    checks.publicKeysSample = keys.slice(0, 10)
    checks.reflectionCheckPass = true
    debugLog('diagnose-reflection', 'Reflection check PASS - found', keys.length, 'public keys')
  } catch (err) {
    checks.reflectionCheckPass = false
    checks.reflectionError = (err as any)?.message || String(err)
    debugLog('diagnose-reflection', 'Reflection check FAIL:', err)
  }

  // Test 5: Internal state test (try to access private fields cautiously)
  try {
    // Check if network has data property
    const hasData = network.value.body?.data !== undefined
    checks.hasDataProperty = hasData
    checks.internalStateCheckPass = true
    debugLog('diagnose-internal', 'Internal state check PASS - data property exists:', hasData)
  } catch (err) {
    checks.internalStateCheckPass = false
    checks.internalStateError = (err as any)?.message || String(err)
    debugLog('diagnose-internal', 'Internal state check FAIL:', err)
  }

  // Overall validity determination
  const valid = checks.networkExists &&
                checks.containerVisible &&
                readCheckPass &&
                methodCheckPass &&
                functionalCheckPass

  checks.overallValid = valid
  checks.readCheckPass = readCheckPass
  checks.methodCheckPass = methodCheckPass
  checks.functionalCheckPass = functionalCheckPass

  // Log summary
  debugLog('diagnose', 'Network diagnosis result:', {
    valid,
    containerVisible: checks.containerVisible,
    readCheckPass,
    methodCheckPass,
    functionalCheckPass,
    reflectionCheckPass: checks.reflectionCheckPass,
    internalStateCheckPass: checks.internalStateCheckPass
  })

  // Log detailed checks for debugging
  debugLog('diagnose-details', 'Detailed diagnosis checks:', JSON.stringify(checks, null, 2))

  return { valid, checks }
}


const deselectNode = () => {
  selectedNode.value = null
  if (network.value) {
    network.value.setSelection({ nodes: [], edges: [] })
  }
}

// Initialize graph - creates a new network instance
const initGraph = () => {
  debugLog('initGraph', 'Called')
  debugLog('initGraph', 'Container exists:', !!graphContainer.value)
  debugLog('initGraph', 'Active nodes:', activeGraphData.value.nodes?.length || 0)

  try {
    // If network already exists, destroy it first (clean start)
    if (network.value) {
      debugLog('initGraph', 'Destroying existing network')
      try {
        network.value.destroy()
      } catch (err) {
        debugWarn('initGraph', 'Error destroying network:', err)
      }
      network.value = null
    }

    // Check prerequisites
    if (!graphContainer.value) {
      debugWarn('initGraph', 'Graph container ref is null')
      return
    }

    const container = graphContainer.value
    if (container.offsetWidth === 0 || container.offsetHeight === 0) {
      debugLog('initGraph', 'Container has zero dimensions, postponing')
      // Use requestAnimationFrame for better timing
      requestAnimationFrame(() => {
        if (container.offsetWidth > 0 && container.offsetHeight > 0) {
          debugLog('initGraph', 'Container now has dimensions, retrying')
          initGraph()
        } else {
          // If still zero, try one more time after a short delay
          setTimeout(() => {
            if (container.offsetWidth > 0 && container.offsetHeight > 0) {
              debugLog('initGraph', 'Container has dimensions after delay, retrying')
              initGraph()
            } else {
              debugWarn('initGraph', 'Container still has zero dimensions after retry')
            }
          }, 100)
        }
      })
      return
    }

    if (!activeGraphData.value.nodes || activeGraphData.value.nodes.length === 0) {
      debugLog('initGraph', 'No nodes to display')
      return
    }

    debugLog('initGraph', 'Creating network with', activeGraphData.value.nodes.length, 'nodes')

    // Use helper function to prepare graph data
    const { nodes, edges } = prepareGraphData(activeGraphData.value.nodes, activeGraphData.value.edges)

    const options = {
      nodes: {
        shape: 'dot',
        size: 20, // base size, will be overridden by node-specific size
        font: {
          size: 16,
          color: '#000000',
          face: 'Inter, "Segoe UI", Roboto, Arial, sans-serif',
          strokeWidth: 2,
          strokeColor: '#FFFFFF'
        },
        borderWidth: 2,
        borderWidthSelected: 3,
        scaling: {
          min: 24,
          max: 70,
          label: {
            enabled: true,
            min: 14,
            max: 24,
            maxVisible: 30,
            drawThreshold: 5
          }
        }
      },
      edges: {
        smooth: {
          enabled: true,
          type: 'continuous',
          roundness: 0.5
        },
        arrows: {
          to: {
            enabled: true,
            scaleFactor: 0.8
          }
        }
      },
      physics: {
        enabled: true,
        stabilization: {
          iterations: 50,  // Reduced from 100 for faster stabilization
          fit: true        // Fit view after stabilization
        },
        solver: 'barnesHut',
        barnesHut: {
          gravitationalConstant: -2000,  // Reduced magnitude for less strong attraction
          springConstant: 0.05,         // Reduced spring constant for smoother movement
          springLength: 150,            // Slightly shorter spring length
          centralGravity: 0.3,          // Add central gravity to keep nodes centered
          damping: 0.08                 // Add damping to reduce oscillations
        }
      },
      interaction: {
        dragNodes: true,
        dragView: true,
        hover: true,
        hoverConnectedEdges: true,
        tooltipDelay: 200,
        hideEdgesOnDrag: false,
        navigationButtons: false,
        selectable: true,
        selectConnectedEdges: true,
        multiselect: false,
        zoomView: true
      },
      layout: {
        improvedLayout: true
      }
    }

    network.value = markRaw(new Network(graphContainer.value, { nodes, edges }, options))
    debugLog('initGraph', 'Network created successfully')

    // Event listeners
    network.value.on('click', (params: any) => {
      if (params.nodes.length > 0) {
        const nodeId = params.nodes[0]
        const node = activeGraphData.value.nodes.find((n: any) => n.id === nodeId)
        selectedNode.value = node
        debugLog('network', 'Node clicked:', node?.label)
      } else {
        selectedNode.value = null
      }
    })

    network.value.on('doubleClick', (params: any) => {
      if (params.nodes.length > 0) {
        network.value.fit({ nodes: params.nodes, animation: true })
      }
    })

    // Fix for mouse drag state getting stuck
    network.value.on('dragEnd', (params: any) => {
      debugLog('network', 'dragEnd event fired', params)
      // Ensure drag state is properly cleared
      try {
        // Try to clear any ongoing selections or drag states
        if (network.value) {
          network.value.setSelection({ nodes: [], edges: [] })
        }
      } catch (err) {
        debugWarn('network', 'Error in dragEnd handler:', err)
      }
    })
  } catch (err) {
    console.error('Error in initGraph:', err)
    debugWarn('initGraph', 'Failed to create network:', err)
  }
}

// Function to update graph with new data - simple implementation
const updateGraphWithData = async (graphData: any) => {
  debugLog('updateGraph', 'Called:', {
    nodes: graphData.nodes?.length,
    edges: graphData.edges?.length,
    networkExists: !!network.value
  })

  // If network doesn't exist, initialize it
  if (!network.value) {
    debugLog('updateGraph', 'Network not exists, initializing')
    initGraph()
    return
  }

  try {
    // If empty data, clear network
    if (graphData.nodes?.length === 0) {
      debugLog('updateGraph', 'Empty graph data, clearing network')
      network.value.setData({ nodes: [], edges: [] })
    } else {
      // Update with new data
      debugLog('updateGraph', 'Updating existing network with new data')
      const { nodes, edges } = prepareGraphData(graphData.nodes || [], graphData.edges || [])
      network.value.setData({ nodes, edges })
      debugLog('updateGraph', 'Network updated successfully:', { nodes: nodes.length, edges: edges.length })
    }
  } catch (err) {
    debugWarn('updateGraph', 'Error updating graph:', err)
    // If any operation fails, reinitialize the network
    debugLog('updateGraph', 'Reinitializing network after failure')
    initGraph()
  }
}

// Lifecycle
onMounted(() => {
  // Fetch sessions list for the session selector
  debugLog('mounted', 'Fetching sessions, current sessions in store:', chatStore.sessions?.length || 0)
  chatStore.fetchSessions().then(sessions => {
    debugLog('mounted', 'Fetched sessions successfully, count:', sessions.length, 'sessions:', sessions)
    debugLog('mounted', 'Updated store sessions count:', chatStore.sessions.length)
    debugLog('mounted', 'Sessions computed value after fetch:', sessions.value?.length || 0)
  }).catch(err => {
    debugWarn('mounted', 'Failed to fetch sessions:', err)
  })

  // Load initial graph based on current view
  if (currentView.value === 'session') {
    // Check if we have a current session
    if (chatStore.currentSessionId) {
      graphStore.fetchSessionGraph(chatStore.currentSessionId)
    } else if (chatStore.sessions && chatStore.sessions.length > 0) {
      // Auto-select first available session
      const firstSession = chatStore.sessions[0]
      chatStore.currentSessionId = firstSession.session_id
      graphStore.fetchSessionGraph(firstSession.session_id)
    } else {
      // No sessions available, switch to global view
      currentView.value = 'global'
      graphStore.fetchGlobalGraphData()
    }
  } else {
    graphStore.fetchGlobalGraphData()
  }

  // Network will be initialized automatically when graph data arrives
  // via the watch on activeGraphData
})

onUnmounted(() => {
  if (network.value) {
    debugLog('unmounted', 'Destroying network')
    network.value.destroy()
    network.value = null
  }
})

// Watch for graph data changes - simple implementation
watch(activeGraphData, async (newVal) => {
  debugLog('graph-watch', 'Active graph data changed:', newVal)
  debugLog('graph-watch', 'Network exists:', !!network.value)
  debugLog('graph-watch', 'Nodes count:', newVal.nodes?.length)
  debugLog('graph-watch', 'Edges count:', newVal.edges?.length)

  try {
    await updateGraphWithData(newVal)
  } catch (err) {
    debugWarn('graph-watch', 'Error in graph update:', err)
  }
}, { deep: true })

// Watch for sessions changes
watch(sessions, (newSessions, oldSessions) => {
  debugLog('sessions-watch', 'Sessions changed:', {
    newCount: newSessions.length,
    oldCount: oldSessions?.length || 0,
    currentView: currentView.value,
    currentSessionId: chatStore.currentSessionId
  })

  if (currentView.value === 'session') {
    // Check if current session still exists
    if (chatStore.currentSessionId) {
      const sessionExists = newSessions.some(s => s.session_id === chatStore.currentSessionId)
      if (!sessionExists) {
        debugLog('sessions-watch', 'Current session no longer exists, clearing selection')
        chatStore.currentSessionId = ''
      }
    }

    // If no current session but we have sessions, auto-select first one
    if (!chatStore.currentSessionId && newSessions.length > 0) {
      const firstSession = newSessions[0]
      debugLog('sessions-watch', 'Auto-selecting first session:', firstSession.session_id)
      chatStore.currentSessionId = firstSession.session_id
      graphStore.fetchSessionGraph(firstSession.session_id)
    }
    // If no sessions at all, switch to global view
    else if (newSessions.length === 0) {
      debugLog('sessions-watch', 'No sessions available, switching to global view')
      currentView.value = 'global'
      graphStore.fetchGlobalGraphData()
    }
  }
}, { deep: true })

// Watch for session changes to update graph when session is switched from chat interface
watch(() => chatStore.currentSessionId, (newSessionId, oldSessionId) => {
  debugLog('session-change', 'currentSessionId watch triggered:', {
    oldSessionId,
    newSessionId,
    currentView: currentView.value,
    isSameSession: newSessionId === oldSessionId
  })

  // Skip if same session or no new session
  if (!newSessionId || newSessionId === oldSessionId) {
    debugLog('session-change', 'Same session or no session, skipping graph update')
    return
  }

  // Only update graph if in session view
  if (currentView.value === 'session') {
    debugLog('session-change', 'Session changed in chat, fetching graph for:', newSessionId)
    graphStore.fetchSessionGraph(newSessionId)
  } else {
    debugLog('session-change', 'Session changed but not in session view, skipping graph update')
  }
})
</script>

<style scoped>
.graph-view {
  display: flex;
  flex: 1;
  height: 100%;
  background: white;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(156, 137, 184, 0.1);
  font-family: 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
}

.control-panel {
  width: 320px;
  flex-shrink: 0;
  background: linear-gradient(135deg, #F8F5F2 0%, #F0F0F0 100%);
  border-right: 1px solid #E0E0E0;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  padding: 20px;
}

.panel-header {
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 2px solid rgba(156, 137, 184, 0.2);
}

.panel-header h3 {
  margin: 0 0 15px 0;
  color: #9C89B8;
  font-size: 1.4rem;
  font-weight: 600;
}

.view-switch {
  display: flex;
  gap: 10px;
}

.view-btn {
  flex: 1;
  background: rgba(255, 255, 255, 0.9);
  border: 2px solid #9C89B8;
  color: #9C89B8;
  padding: 8px 12px;
  border-radius: 15px;
  cursor: pointer;
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

.view-btn:hover {
  background: rgba(156, 137, 184, 0.1);
}

.view-btn.active {
  background: linear-gradient(135deg, #9C89B8 0%, #7A6B9C 100%);
  color: white;
  border-color: #7A6B9C;
}

.search-section {
  margin-bottom: 20px;
}

.search-input-wrapper {
  position: relative;
  margin-bottom: 15px;
}

.search-input {
  width: 100%;
  padding: 10px 15px 10px 40px;
  border: 2px solid #9C89B8;
  border-radius: 15px;
  font-family: inherit;
  font-size: 0.9rem;
  background: rgba(255, 255, 255, 0.9);
  transition: all 0.3s ease;
}

.search-input:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(156, 137, 184, 0.3);
}

.search-icon {
  position: absolute;
  left: 12px;
  top: 50%;
  transform: translateY(-50%);
  color: #9C89B8;
  font-size: 1rem;
}

.filter-section {
  background: rgba(255, 255, 255, 0.7);
  border-radius: 10px;
  padding: 15px;
}

.filter-group {
  margin-bottom: 10px;
}

.filter-label {
  display: block;
  margin-bottom: 8px;
  font-size: 0.9rem;
  color: #666;
  font-weight: 500;
}

.filter-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.filter-option {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  font-size: 0.85rem;
}

.filter-label-text {
  flex: 1;
  color: #555;
}

.group-color {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 1px solid rgba(0, 0, 0, 0.1);
}

.stats-section {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.stat-card {
  flex: 1;
  background: white;
  border-radius: 10px;
  padding: 12px;
  text-align: center;
  box-shadow: 0 3px 10px rgba(0, 0, 0, 0.05);
  border: 1px solid rgba(156, 137, 184, 0.2);
}

.stat-icon {
  font-size: 1.2rem;
  margin-bottom: 5px;
  color: #9C89B8;
}

.stat-value {
  font-size: 1.4rem;
  font-weight: bold;
  color: #9C89B8;
  margin-bottom: 2px;
}

.stat-label {
  font-size: 0.8rem;
  color: #888;
}

.graph-controls {
  position: absolute;
  bottom: 20px;
  right: 20px;
  z-index: 10;
}

.graph-control-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #9C89B8 0%, #B8D0EB 100%);
  color: white;
  border: none;
  padding: 10px 16px;
  border-radius: 10px;
  cursor: pointer;
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.3s ease;
  box-shadow: 0 3px 10px rgba(156, 137, 184, 0.3);
}

.graph-control-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(156, 137, 184, 0.4);
}

.control-icon {
  font-size: 1rem;
}

.control-label {
  font-size: 0.9rem;
}

.node-details {
  background: white;
  border-radius: 15px;
  padding: 15px;
  margin-bottom: 20px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.05);
  border: 2px solid rgba(156, 137, 184, 0.3);
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 10px;
  border-bottom: 1px solid #E0E0E0;
}

.details-header h4 {
  margin: 0;
  color: #9C89B8;
  font-size: 1rem;
}

.close-details {
  background: none;
  border: none;
  color: #9C89B8;
  font-size: 1.5rem;
  cursor: pointer;
  line-height: 1;
  padding: 0 5px;
}

.close-details:hover {
  color: #7A6B9C;
}

.node-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.node-label-icon {
  display: flex;
  align-items: center;
  gap: 8px;
}

.node-icon {
  font-size: 1.2rem;
}

.node-label {
  font-weight: bold;
  color: #333;
  font-size: 1.1rem;
}

.node-group-badge {
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 0.7rem;
  color: white;
  font-weight: 500;
  text-transform: uppercase;
}

.node-description {
  color: #666;
  font-size: 0.9rem;
  line-height: 1.4;
  margin-bottom: 10px;
  padding: 8px;
  background: rgba(156, 137, 184, 0.05);
  border-radius: 8px;
}

.node-meta {
  display: flex;
  gap: 15px;
  margin-bottom: 15px;
  font-size: 0.85rem;
}

.meta-item {
  display: flex;
  gap: 5px;
}

.meta-label {
  color: #888;
  font-weight: 500;
}

.meta-value {
  color: #333;
  font-family: monospace;
}

.node-connections h5 {
  margin: 0 0 10px 0;
  color: #9C89B8;
  font-size: 0.9rem;
}

.connections-list {
  max-height: 150px;
  overflow-y: auto;
}

.connection-item {
  padding: 8px;
  margin-bottom: 5px;
  background: rgba(156, 137, 184, 0.05);
  border-radius: 8px;
  border-left: 3px solid #9C89B8;
}

.connection-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.85rem;
}

.connection-label {
  color: #9C89B8;
  font-weight: 500;
  font-style: italic;
}

.connection-direction {
  color: #888;
}

.connection-node {
  color: #333;
  font-weight: 500;
}


.test-connection-section {
  margin-bottom: 20px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 10px;
}

.test-btn {
  width: 100%;
  padding: 10px 15px;
  border: 2px solid #9C89B8;
  border-radius: 10px;
  background: white;
  color: #9C89B8;
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.test-btn:hover:not(:disabled) {
  background: #9C89B8;
  color: white;
}

.test-btn.success {
  background: #28a745;
  border-color: #28a745;
  color: white;
}

.test-btn.error {
  background: #dc3545;
  border-color: #dc3545;
  color: white;
}

.test-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.connection-details {
  margin-top: 10px;
  padding: 10px;
  background: white;
  border-radius: 8px;
  font-size: 0.85rem;
}

.status-message {
  margin-bottom: 5px;
  font-weight: 500;
}

.status-message.success {
  color: #28a745;
}

.status-message.error {
  color: #dc3545;
}

/* Diagnostics Section */
.diagnostics-section {
  margin-bottom: 20px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 10px;
}

.diagnostics-btn {
  background: linear-gradient(135deg, #87CEB3 0%, #5DAE8B 100%);
  border-color: #87CEB3;
  color: white;
}

.diagnostics-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #5DAE8B 0%, #4A9A7A 100%);
}

.diagnostics-result {
  margin-top: 15px;
  padding: 12px;
  background: white;
  border-radius: 10px;
  font-size: 0.9rem;
}

.diagnostics-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
  background: rgba(156, 137, 184, 0.05);
  border-radius: 6px;
}

.stat-name {
  color: #666;
}

.stat-value {
  font-weight: 600;
  color: #888;
}

.stat-value.has-data {
  color: #28a745;
}

.diagnostics-error {
  color: #dc3545;
  text-align: center;
  padding: 10px;
}

/* Sessions List in Diagnostics */
.sessions-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(156, 137, 184, 0.2);
}

.sessions-title {
  font-size: 0.85rem;
  color: #666;
  margin-bottom: 8px;
  font-weight: 500;
}

.sessions-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.session-btn {
  padding: 6px 10px;
  border: 1px solid #9C89B8;
  border-radius: 6px;
  background: white;
  color: #9C89B8;
  font-size: 0.8rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.session-btn:hover {
  background: rgba(156, 137, 184, 0.1);
}

.session-btn.active {
  background: #9C89B8;
  color: white;
}

.no-sessions {
  margin-top: 10px;
  padding: 10px;
  text-align: center;
  color: #888;
  font-size: 0.85rem;
  background: rgba(156, 137, 184, 0.05);
  border-radius: 6px;
}

/* Manual Reanalysis Section */
.reanalysis-section {
  margin-bottom: 20px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 10px;
}

.reanalysis-btn {
  background: linear-gradient(135deg, #FFA07A 0%, #FF7F50 100%);
  border-color: #FFA07A;
  color: white;
}

.reanalysis-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #FF7F50 0%, #FF6347 100%);
}

.reanalysis-result {
  margin-top: 15px;
  padding: 12px;
  background: white;
  border-radius: 10px;
  font-size: 0.9rem;
}

.reanalysis-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.error-message {
  background: rgba(220, 53, 69, 0.1);
  border: 1px solid #dc3545;
  color: #721c24;
  padding: 12px 16px;
  border-radius: 8px;
  margin: 10px 0;
  text-align: center;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.retry-btn {
  background: #dc3545;
  color: white;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.85rem;
  cursor: pointer;
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.retry-btn:hover {
  background: #c82333;
}


.graph-container {
  flex: 1;
  min-height: 0;
  position: relative;
  background: linear-gradient(135deg, #F8F5F2 0%, #F0F0F0 100%);
  display: flex;
  flex-direction: column;
}

.graph-canvas {
  flex: 1;
  width: 100%;
  height: 100%;
  min-height: 0;
}

.empty-graph {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
  color: #9C89B8;
}

.empty-icon {
  font-size: 4rem;
  margin-bottom: 20px;
  opacity: 0.5;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 0.5; }
  50% { opacity: 1; }
}

.empty-graph h3 {
  margin: 0 0 10px 0;
  font-size: 1.5rem;
}

.empty-graph p {
  margin: 0 0 20px 0;
  color: #888;
}

.demo-btn {
  background: linear-gradient(135deg, #9C89B8 0%, #B8D0EB 100%);
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 20px;
  cursor: pointer;
  font-family: inherit;
  transition: all 0.3s ease;
}

.demo-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(156, 137, 184, 0.4);
}

.loading-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(255, 255, 255, 0.9);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 10;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid rgba(156, 137, 184, 0.2);
  border-top: 4px solid #9C89B8;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 15px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

.loading-overlay p {
  color: #9C89B8;
  margin: 0;
}

@media (max-width: 1024px) {
  .graph-view {
    flex-direction: column;
    height: 100%;
  }

  .control-panel {
    width: 100%;
    max-height: 350px;
    border-right: none;
    border-bottom: 1px solid #E0E0E0;
  }

  .graph-container {
    min-height: 400px;
  }
}

@media (max-width: 768px) {
  .stats-section {
    flex-direction: column;
  }

  .view-switch {
    flex-direction: column;
  }

  .graph-controls {
    bottom: 10px;
    right: 10px;
  }

  .graph-control-btn {
    padding: 8px 12px;
    font-size: 0.85rem;
  }
}

/* Session Selection */
.session-selection-section {
  margin-bottom: 20px;
  padding: 15px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 10px;
}

.session-selection-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.session-label {
  font-size: 0.9rem;
  color: #666;
  font-weight: 500;
  white-space: nowrap;
}

.session-select {
  flex: 1;
  padding: 8px 12px;
  border: 2px solid #9C89B8;
  border-radius: 10px;
  background: white;
  color: #333;
  font-family: inherit;
  font-size: 0.9rem;
  transition: all 0.3s ease;
}

.session-select:focus {
  outline: none;
  box-shadow: 0 0 0 3px rgba(156, 137, 184, 0.3);
}

.session-select:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.no-sessions-message {
  padding: 10px;
  text-align: center;
  color: #888;
  font-size: 0.85rem;
  background: rgba(156, 137, 184, 0.05);
  border-radius: 6px;
}
</style>