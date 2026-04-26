import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  fetchReview,
  pollReviewStatus,
  regenerateReview,
  fetchReviewQuestions,
  markReviewCompleted,
  fetchIntegratedReview,
  getSessionsWithReviews
} from '@/api'

export const useReviewStore = defineStore('review', () => {
  // State
  const currentReview = ref({
    session_id: null,
    summary: '',
    key_points: [],
    questions: [],
    recommendations: [],
    next_review_date: null,
    recent_entities: [],
    key_entities: []
  })
  const completedReviews = ref([])
  const isLoading = ref(false)
  const isPolling = ref(false)
  const error = ref('')
  const reviewSchedule = ref([])
  const generationStatus = ref({
    sessionId: null,
    status: 'idle', // 'idle', 'pending', 'generating', 'completed', 'failed'
    progress: 0,
    estimatedTime: 0,
    startTime: null,
    taskInfo: null
  })

  // Integrated review state - new structured format
  const integratedReview = ref({
    aggregated_summary: '',
    review_groups: [],  // Array of review groups, each with knowledge_cards and quiz_questions
    next_review_date: null,
    session_count: 0,
    total_groups: 0,
    total_knowledge_cards: 0,
    total_quiz_questions: 0,
    sessions: []
  })
  const isIntegratedLoading = ref(false)
  const sessionsWithReviews = ref([])

  // Getters
  const hasReviewData = computed(() => currentReview.value.session_id !== null)
  const questionCount = computed(() => currentReview.value.questions.length)
  const recommendationCount = computed(() => currentReview.value.recommendations.length)
  const upcomingReviews = computed(() =>
    reviewSchedule.value.filter(item => !item.completed)
  )
  const reviewProgress = computed(() => {
    const total = recommendationCount.value
    const completed = currentReview.value.recommendations.filter(r => r.completed).length
    return total > 0 ? Math.round((completed / total) * 100) : 0
  })

  // Integrated review getters
  const hasIntegratedReviewData = computed(() => integratedReview.value.review_groups?.length > 0)
  const integratedQuestionCount = computed(() => integratedReview.value.total_quiz_questions || 0)
  const integratedRecommendationCount = computed(() => integratedReview.value.total_knowledge_cards || 0)
  const integratedKeyPointsCount = computed(() => integratedReview.value.total_groups || 0)
  const integratedSessionsCount = computed(() => integratedReview.value.session_count || 0)
  const integratedProgress = computed(() => {
    // Calculate progress based on completed knowledge cards and quiz questions
    if (!integratedReview.value.review_groups || integratedReview.value.review_groups.length === 0) {
      return 0
    }

    let totalItems = 0
    let completedItems = 0

    for (const group of integratedReview.value.review_groups) {
      // Knowledge cards
      if (group.knowledge_cards) {
        totalItems += group.knowledge_cards.length
        completedItems += group.knowledge_cards.filter(card => card.is_learned).length
      }

      // Quiz questions
      if (group.quiz_questions) {
        totalItems += group.quiz_questions.length
        completedItems += group.quiz_questions.filter(question => question.is_completed).length
      }
    }

    return totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0
  })

  // Actions
  const fetchSessionReview = async (sessionId, api_key = null, base_url = null, model = null, recent_days = 3, top_n_recent = 3, max_questions = 10) => {
    if (!sessionId) {
      error.value = 'No session ID provided'
      return null
    }

    isLoading.value = true
    error.value = ''

    try {
      const result = await fetchReview(sessionId, api_key, base_url, model, recent_days, top_n_recent, max_questions)

      if (result.status === 'completed') {
        // Cached review available
        const reviewData = result.data
        currentReview.value = {
          session_id: sessionId,
          summary: reviewData.summary || '',
          key_points: reviewData.key_points || [],
          questions: reviewData.questions || [],
          recommendations: reviewData.recommendations || [],
          next_review_date: reviewData.next_review_date || null,
          recent_entities: reviewData.recent_entities || [],
          key_entities: reviewData.key_entities || []
        }
        return { status: 'completed', data: reviewData }
      } else if (result.status === 'pending') {
        // Review generation started, return task info for polling
        return { status: 'pending', taskInfo: result.taskInfo }
      } else {
        throw new Error(`Unexpected result status: ${result.status}`)
      }
    } catch (err) {
      console.error('Error fetching review:', err)
      error.value = `Failed to load review: ${err.message}`
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const fetchSessionQuestions = async (sessionId) => {
    try {
      const questions = await fetchReviewQuestions(sessionId)
      currentReview.value.questions = questions
      return questions
    } catch (err) {
      console.error('Error fetching review questions:', err)
      throw err
    }
  }

  const completeReviewItem = async (reviewItemId) => {
    if (!currentReview.value.session_id) {
      error.value = 'No active session'
      return false
    }

    try {
      await markReviewCompleted(currentReview.value.session_id, reviewItemId)

      // Update local state
      const itemIndex = currentReview.value.recommendations.findIndex(
        item => item.id === reviewItemId
      )
      if (itemIndex !== -1) {
        currentReview.value.recommendations[itemIndex].completed = true
      }

      // Add to completed reviews
      completedReviews.value.push({
        id: reviewItemId,
        session_id: currentReview.value.session_id,
        completed_at: new Date().toISOString()
      })

      return true
    } catch (err) {
      console.error('Error completing review item:', err)
      error.value = `Failed to mark review as completed: ${err.message}`
      throw err
    }
  }

  const generateReviewSchedule = () => {
    // Simulate generating a review schedule based on key points
    const schedule = []
    const now = new Date()

    currentReview.value.key_points.forEach((point, index) => {
      schedule.push({
        id: index + 1,
        knowledge_point: point,
        review_dates: [
          new Date(now.getTime() + 24 * 60 * 60 * 1000).toISOString(), // 1 day
          new Date(now.getTime() + 72 * 60 * 60 * 1000).toISOString(), // 3 days
          new Date(now.getTime() + 168 * 60 * 60 * 1000).toISOString(), // 7 days
          new Date(now.getTime() + 720 * 60 * 60 * 1000).toISOString()  // 30 days
        ],
        current_stage: 0,
        mastery_level: 'learning',
        completed: false
      })
    })

    reviewSchedule.value = schedule
    return schedule
  }

  const simulateReviewData = (sessionId = 'demo') => {
    // Generate demo review data
    currentReview.value = {
      session_id: sessionId,
      summary: 'This conversation covered fundamental concepts of artificial intelligence and machine learning. Key topics included neural networks, deep learning applications, and ethical considerations in AI development.',
      key_points: [
        'Artificial Intelligence vs Machine Learning',
        'Neural network architecture',
        'Deep learning applications',
        'Ethical considerations in AI'
      ],
      questions: [
        {
          id: 1,
          question: 'What is the difference between AI and Machine Learning?',
          options: [
            'AI is broader, ML is a subset of AI',
            'ML is broader, AI is a subset of ML',
            'They are the same thing',
            'AI deals with hardware, ML with software'
          ],
          correct_answer: 0,
          explanation: 'Artificial Intelligence is the broader concept of machines being able to carry out tasks in a way we would consider "smart". Machine Learning is a current application of AI based on the idea that we should give machines access to data and let them learn for themselves.',
          difficulty: 'easy'
        },
        {
          id: 2,
          question: 'What is a neural network?',
          options: [
            'A computer network for AI researchers',
            'A mathematical model inspired by the human brain',
            'A type of database for storing AI knowledge',
            'A programming language for AI'
          ],
          correct_answer: 1,
          explanation: 'A neural network is a series of algorithms that endeavors to recognize underlying relationships in a set of data through a process that mimics the way the human brain operates.',
          difficulty: 'medium'
        }
      ],
      recommendations: [
        {
          id: 1,
          type: 'quiz',
          title: 'Basic Concepts Quiz',
          description: 'Test your understanding of AI fundamentals',
          estimated_time: '5 minutes',
          due_date: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
          priority: 'high',
          completed: false
        },
        {
          id: 2,
          type: 'reading',
          title: 'Review Neural Networks',
          description: 'Re-read the section on neural network architecture',
          estimated_time: '10 minutes',
          due_date: new Date(Date.now() + 72 * 60 * 60 * 1000).toISOString(),
          priority: 'medium',
          completed: false
        }
      ],
      next_review_date: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString()
    }

    generateReviewSchedule()
    return currentReview.value
  }

  const clearReview = () => {
    currentReview.value = {
      session_id: null,
      summary: '',
      key_points: [],
      questions: [],
      recommendations: [],
      next_review_date: null
    }
    error.value = ''
  }

  const startPollingReviewStatus = async (sessionId) => {
    if (!sessionId) {
      error.value = 'No session ID provided'
      return
    }

    isPolling.value = true
    generationStatus.value = {
      sessionId,
      status: 'pending',
      progress: 0,
      estimatedTime: 120, // Default 2 minutes
      startTime: Date.now(),
      taskInfo: null
    }

    // Poll every 3 seconds for up to 5 minutes (100 attempts)
    const maxAttempts = 100
    let attempts = 0

    const pollInterval = setInterval(async () => {
      if (attempts >= maxAttempts || !isPolling.value) {
        clearInterval(pollInterval)
        isPolling.value = false
        if (attempts >= maxAttempts) {
          error.value = 'Review generation timeout'
        }
        return
      }

      attempts++
      try {
        const statusData = await pollReviewStatus(sessionId)
        const status = statusData.status || 'unknown'

        // Update progress based on elapsed time
        const elapsed = (Date.now() - generationStatus.value.startTime) / 1000
        generationStatus.value.progress = Math.min(95, (elapsed / generationStatus.value.estimatedTime) * 100)

        if (status === 'completed') {
          // Generation completed, fetch the review
          clearInterval(pollInterval)
          isPolling.value = false
          generationStatus.value.status = 'completed'
          generationStatus.value.progress = 100

          // Fetch the completed review
          await fetchSessionReview(sessionId)
        } else if (status === 'failed') {
          clearInterval(pollInterval)
          isPolling.value = false
          generationStatus.value.status = 'failed'
          error.value = statusData.error_message || 'Review generation failed'
        } else if (status === 'generating' || status === 'pending') {
          generationStatus.value.status = status
        }
      } catch (err) {
        console.error('Error polling review status:', err)
        // Continue polling on error (might be temporary network issue)
      }
    }, 3000) // Poll every 3 seconds
  }

  const stopPolling = () => {
    isPolling.value = false
  }

  const manuallyRegenerateReview = async (sessionId, api_key = null, base_url = null, model = null, recent_days = 3, top_n_recent = 3, max_questions = 10) => {
    try {
      isLoading.value = true
      const response = await regenerateReview(sessionId, api_key, base_url, model, recent_days, top_n_recent, max_questions)

      if (response.status === 202) {
        // Regeneration started, start polling
        await startPollingReviewStatus(sessionId)
        return { status: 'pending', taskInfo: response.data }
      } else {
        throw new Error('Unexpected response from regeneration endpoint')
      }
    } catch (err) {
      console.error('Error regenerating review:', err)
      error.value = `Failed to regenerate review: ${err.message}`
      throw err
    } finally {
      isLoading.value = false
    }
  }

  const clearError = () => {
    error.value = ''
  }

  // Integrated review actions
  const loadIntegratedReview = async (limit = 10, days = 7, forceRefresh = false, api_key = null, base_url = null, model = null) => {
    isIntegratedLoading.value = true
    error.value = ''

    try {
      const result = await fetchIntegratedReview(limit, days, forceRefresh, api_key, base_url, model)

      // Check the result status
      if (result.status === 'regenerating') {
        // Review regeneration started, return task info
        isIntegratedLoading.value = false
        return {
          status: 'regenerating',
          taskInfo: result.taskInfo,
          message: result.message
        }
      } else if (result.status === 'completed') {
        // Normal response with integrated review data
        const data = result.data

        // Update integrated review state with new structured format
        integratedReview.value = {
          aggregated_summary: data.aggregated_summary || '',
          review_groups: data.review_groups || [],
          next_review_date: data.next_review_date || null,
          session_count: data.session_count || 0,
          total_groups: data.total_groups || 0,
          total_knowledge_cards: data.total_knowledge_cards || 0,
          total_quiz_questions: data.total_quiz_questions || 0,
          sessions: data.sessions || []
        }

        isIntegratedLoading.value = false
        return {
          status: 'completed',
          data: integratedReview.value
        }
      } else {
        throw new Error(`Unexpected response status: ${result.status}`)
      }
    } catch (err) {
      console.error('Error fetching integrated review:', err)
      error.value = `Failed to load integrated review: ${err.message}`

      // Set empty integrated review on error (new structured format)
      integratedReview.value = {
        aggregated_summary: 'Error loading integrated review.',
        review_groups: [],
        next_review_date: null,
        session_count: 0,
        total_groups: 0,
        total_knowledge_cards: 0,
        total_quiz_questions: 0,
        sessions: []
      }

      isIntegratedLoading.value = false
      throw err
    }
  }

  const regenerateIntegratedReview = async (limit = 10, days = 7, api_key = null, base_url = null, model = null) => {
    isIntegratedLoading.value = true
    error.value = ''

    try {
      // Trigger regeneration with forceRefresh = true
      const result = await fetchIntegratedReview(limit, days, true, api_key, base_url, model)

      if (result.status === 'regenerating') {
        // Regeneration started, we could start polling here
        // For now, just return the task info
        isIntegratedLoading.value = false
        return {
          status: 'regenerating',
          taskInfo: result.taskInfo,
          message: result.message
        }
      } else if (result.status === 'completed') {
        // This shouldn't happen with forceRefresh=true, but handle it anyway
        const data = result.data
        integratedReview.value = {
          aggregated_summary: data.aggregated_summary || '',
          review_groups: data.review_groups || [],
          next_review_date: data.next_review_date || null,
          session_count: data.session_count || 0,
          total_groups: data.total_groups || 0,
          total_knowledge_cards: data.total_knowledge_cards || 0,
          total_quiz_questions: data.total_quiz_questions || 0,
          sessions: data.sessions || []
        }
        isIntegratedLoading.value = false
        return {
          status: 'completed',
          data: integratedReview.value
        }
      } else {
        throw new Error(`Unexpected response status: ${result.status}`)
      }
    } catch (err) {
      console.error('Error regenerating integrated review:', err)
      error.value = `Failed to regenerate integrated review: ${err.message}`
      isIntegratedLoading.value = false
      throw err
    }
  }

  const loadSessionsWithReviews = async () => {
    try {
      const data = await getSessionsWithReviews()
      sessionsWithReviews.value = data.sessions || []
      return sessionsWithReviews.value
    } catch (err) {
      console.error('Error loading sessions with reviews:', err)
      sessionsWithReviews.value = []
      throw err
    }
  }

  const clearIntegratedReview = () => {
    integratedReview.value = {
      aggregated_summary: '',
      review_groups: [],
      next_review_date: null,
      session_count: 0,
      total_groups: 0,
      total_knowledge_cards: 0,
      total_quiz_questions: 0,
      sessions: []
    }
    sessionsWithReviews.value = []
  }

  return {
    // State
    currentReview,
    completedReviews,
    isLoading,
    isPolling,
    error,
    reviewSchedule,
    generationStatus,
    integratedReview,
    isIntegratedLoading,
    sessionsWithReviews,

    // Getters
    hasReviewData,
    questionCount,
    recommendationCount,
    upcomingReviews,
    reviewProgress,
    hasIntegratedReviewData,
    integratedQuestionCount,
    integratedRecommendationCount,
    integratedKeyPointsCount,
    integratedSessionsCount,
    integratedProgress,

    // Actions
    fetchSessionReview,
    startPollingReviewStatus,
    stopPolling,
    manuallyRegenerateReview,
    fetchSessionQuestions,
    completeReviewItem,
    generateReviewSchedule,
    simulateReviewData,
    clearReview,
    clearError,
    loadIntegratedReview,
    regenerateIntegratedReview,
    loadSessionsWithReviews,
    clearIntegratedReview
  }
})