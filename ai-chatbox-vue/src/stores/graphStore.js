import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchGraph, fetchGlobalGraph } from '@/api'

export const useGraphStore = defineStore('graph', () => {
  // State
  const currentGraph = ref({
    nodes: [],
    edges: [],
    session_id: null
  })
  const globalGraph = ref({
    nodes: [],
    edges: [],
    total_nodes: 0,
    total_edges: 0
  })
  const isLoading = ref(false)
  const error = ref('')
  const lastUpdated = ref(null)

  // Getters
  const nodeCount = computed(() => currentGraph.value.nodes.length)
  const edgeCount = computed(() => currentGraph.value.edges.length)
  const hasGraphData = computed(() => nodeCount.value > 0)
  const graphStats = computed(() => ({
    nodes: nodeCount.value,
    edges: edgeCount.value,
    lastUpdated: lastUpdated.value
  }))

  // Actions
  const fetchSessionGraph = async (sessionId) => {
    if (!sessionId) {
      error.value = 'No session ID provided'
      isLoading.value = false
      return null
    }

    // Clear previous graph data immediately when loading new session
    if (currentGraph.value.session_id !== sessionId) {
      currentGraph.value = {
        nodes: [],
        edges: [],
        session_id: sessionId
      }
    }

    isLoading.value = true
    error.value = ''

    try {
      const graphData = await fetchGraph(sessionId)
      currentGraph.value = {
        ...graphData,
        session_id: sessionId
      }
      lastUpdated.value = new Date()
      return graphData
    } catch (err) {
      console.error('Error fetching graph:', err)
      error.value = `Failed to load graph: ${err.message}`
      // Ensure graph is empty on error
      currentGraph.value = {
        nodes: [],
        edges: [],
        session_id: sessionId
      }
    } finally {
      isLoading.value = false
    }
  }

  const fetchGlobalGraphData = async (limit = 100) => {
    // Clear global graph data immediately when loading
    globalGraph.value = {
      nodes: [],
      edges: [],
      total_nodes: 0,
      total_edges: 0
    }

    isLoading.value = true
    error.value = ''

    try {
      const graphData = await fetchGlobalGraph(limit)
      globalGraph.value = {
        nodes: graphData.nodes || [],
        edges: graphData.edges || [],
        total_nodes: graphData.total_nodes || 0,
        total_edges: graphData.total_edges || 0
      }
      lastUpdated.value = new Date()
      return graphData
    } catch (err) {
      console.error('Error fetching global graph:', err)
      error.value = `Failed to load global graph: ${err.message}`
      // Keep graph empty on error
    } finally {
      isLoading.value = false
    }
  }

  const clearGraph = () => {
    currentGraph.value = {
      nodes: [],
      edges: [],
      session_id: null
    }
    error.value = ''
  }

  const clearError = () => {
    error.value = ''
  }

  // Simulate graph update (for testing/demo)
  const simulateGraphUpdate = () => {
    const mockNodes = [
      {
        id: 1,
        label: 'AI',
        group: 'concept',
        title: 'Artificial Intelligence'
      },
      {
        id: 2,
        label: 'Machine Learning',
        group: 'concept',
        title: 'Subfield of AI'
      },
      {
        id: 3,
        label: 'Neural Network',
        group: 'technique',
        title: 'AI technique inspired by brain'
      }
    ]

    const mockEdges = [
      {
        from: 1,
        to: 2,
        label: 'includes',
        title: 'AI includes Machine Learning'
      },
      {
        from: 2,
        to: 3,
        label: 'uses',
        title: 'Machine Learning uses Neural Networks'
      }
    ]

    currentGraph.value = {
      nodes: mockNodes,
      edges: mockEdges,
      session_id: currentGraph.value.session_id || 'demo'
    }
    lastUpdated.value = new Date()
  }

  return {
    // State
    currentGraph,
    globalGraph,
    isLoading,
    error,
    lastUpdated,

    // Getters
    nodeCount,
    edgeCount,
    hasGraphData,
    graphStats,

    // Actions
    fetchSessionGraph,
    fetchGlobalGraphData,
    clearGraph,
    clearError,
    simulateGraphUpdate
  }
})