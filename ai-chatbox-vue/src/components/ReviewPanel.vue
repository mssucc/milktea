<template>
  <div class="review-panel">
    <!-- Panel Header with Anime Character -->
    <div class="review-header">
      <div class="anime-character">
        <div
          class="character-avatar"
          @click="refreshOnAvatarClick"
          @dblclick="regenerateOnAvatarDoubleClick"
          :class="{ 'clickable': isAvatarClickable }"
          :title="isAvatarClickable ? (reviewItems.length > 0 ? '单击刷新，双击重新生成复习内容' : '单击生成复习内容，双击重新生成') : (isLoading.value ? '正在加载...' : '正在生成中...')"
        >
          <img
            v-if="currentCharacter.avatar"
            :src="currentCharacter.avatar"
            alt="角色立绘"
            class="character-image"
          />
          <span v-else class="character-initial">{{ currentCharacter.displayName.charAt(0) }}</span>
          <div v-if="reviewItems.length > 0" class="avatar-refresh-badge">
            <svg class="refresh-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/>
            </svg>
          </div>
        </div>
        <div class="character-info">
          <h3 class="character-name">{{ currentCharacter.displayName }}</h3>
          <p class="character-greeting">{{ characterGreeting }}</p>
        </div>
      </div>
      <CharacterSelector />
    </div>



    <!-- Review Groups -->
    <div class="review-groups">
      <div v-for="group in (reviewData?.review_groups || [])" :key="group.id" class="review-group">
        <div class="group-header" @click="toggleGroupExpansion(group.id)">
          <div class="group-icon">
            <span class="group-icon-circle"></span>
          </div>
          <div class="group-info">
            <h4 class="group-title">{{ group.title }}</h4>
            <div class="group-meta">
              <span class="meta-item">{{ (group.knowledge_cards?.length || 0) + (group.quiz_questions?.length || 0) }}个复习项目</span>
              <span class="meta-item">{{ getGroupProgress(group) }}% 完成</span>
            </div>
          </div>
          <div class="group-expand">
            <span :class="['expand-icon', { 'expanded': expandedGroups.includes(group.id) }]">›</span>
          </div>
        </div>

        <div v-if="expandedGroups.includes(group.id)" class="group-items">
          <!-- Knowledge Cards Section -->
          <div v-if="group.knowledge_cards && group.knowledge_cards.length > 0" class="section-container">
            <div class="section-header">
              <h5 class="section-title">知识卡片</h5>
              <span class="section-count">{{ group.knowledge_cards.length }}个知识点</span>
            </div>
            <div class="knowledge-cards">
              <div v-for="card in group.knowledge_cards" :key="card.id" class="knowledge-card">
                <div class="card-header">
                  <label class="card-checkbox-label" :title="card.is_learned ? '标记为未学' : '标记为已学'">
                    <input
                      type="checkbox"
                      class="card-checkbox"
                      :checked="card.is_learned"
                      @change="toggleCardLearned(group.id, card.id, !card.is_learned)"
                    />
                    <span class="checkbox-custom"></span>
                  </label>
                  <div class="card-content">
                    <p>{{ card.content }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Quiz Questions Section -->
          <div v-if="group.quiz_questions && group.quiz_questions.length > 0" class="section-container">
            <div class="section-header">
              <h5 class="section-title">选择题</h5>
              <span class="section-count">{{ group.quiz_questions.length }}道题</span>
            </div>
            <div class="quiz-questions">
              <div v-for="question in group.quiz_questions" :key="question.id" class="quiz-question">
                <div class="question-header">
                  <span class="question-icon">Q</span>
                  <div class="question-content">
                    <h6>{{ question.question }}</h6>

                    <!-- Options display -->
                    <div v-if="question.is_completed" class="completed-question">
                      <div class="options-display">
                        <div v-for="(option, index) in question.options" :key="index"
                             :class="['option-item', {
                               'correct': index === question.correct_answer,
                               'incorrect': question.user_answer !== undefined && index === question.user_answer && !question.is_correct
                             }]">
                          <span class="option-label">{{ ['A', 'B', 'C', 'D'][index] }}.</span>
                          <span class="option-text">{{ option }}</span>
                          <span v-if="index === question.correct_answer" class="correct-mark">正确</span>
                          <span v-if="question.user_answer !== undefined && index === question.user_answer && !question.is_correct" class="incorrect-mark">错误</span>
                        </div>
                      </div>
                      <div class="explanation">
                        <strong>解析：</strong>{{ question.explanation }}
                      </div>
                    </div>

                    <!-- Options selection (if not completed) -->
                    <div v-else class="options-selection">
                      <div v-for="(option, index) in question.options" :key="index"
                           class="option-item selectable"
                           @click="selectAnswer(group.id, question.id, index)">
                        <span class="option-label">{{ ['A', 'B', 'C', 'D'][index] }}.</span>
                        <span class="option-text">{{ option }}</span>
                      </div>
                    </div>

                    <div class="question-meta">
                      <span class="difficulty-badge" :class="question.difficulty">{{
                        question.difficulty === 'easy' ? '简单' :
                        question.difficulty === 'medium' ? '中等' : '困难'
                      }}</span>
                      <span v-if="question.is_completed" class="completion-status">
                        {{ question.is_correct ? '回答正确' : '回答错误' }}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Group statistics -->
          <div class="group-statistics">
            <div class="stat-item">
              <span class="stat-label">相关会话数:</span>
              <span class="stat-value">{{ group.session_count }}</span>
            </div>
            <div class="stat-item">
              <span class="stat-label">出现频率:</span>
              <span class="stat-value">{{ group.frequency }}次</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="empty-state">
      <div class="empty-character">
        <div class="empty-avatar"></div>
      </div>
      <h4>加载复习内容中...</h4>
      <p>正在调用AI生成个性化复习推荐</p>
      <div class="loading-spinner"></div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="empty-state error-state">
      <div class="empty-character">
        <div class="empty-avatar error-avatar"></div>
      </div>
      <h4>加载失败</h4>
      <p>{{ error }}</p>
      <button @click="refreshReview" class="refresh-btn">重试</button>
    </div>

    <!-- Empty State -->
    <div v-else-if="reviewItems.length === 0" class="empty-state">
      <div class="empty-character">
        <div class="empty-avatar"></div>
      </div>
      <h4>暂无复习内容</h4>
      <p>继续学习聊天，系统会自动生成复习卡片</p>
      <button @click="regenerateReview" class="refresh-btn" :disabled="isRegenerating">
        {{ isRegenerating ? '生成中...' : '生成复习内容' }}
      </button>
    </div>

    <!-- Character Standee - draggable -->
    <div
      v-if="currentCharacter.avatar"
      ref="standeeRef"
      class="character-standee"
      :class="{ dragging: isDragging }"
      @mousedown="startDrag"
      @touchstart="startDrag"
      :style="{ left: position.x + 'px', top: position.y + 'px' }"
    >
      <!-- 动态阴影 -->
      <div class="character-shadow" :style="shadowStyle"></div>
      <div class="standee-wrapper">
        <img :src="currentCharacter.avatar" alt="角色立绘" class="standee-image" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useChatStore } from '@/stores/chatStore'
import { useConfigStore } from '@/stores/configStore'
import { useReviewStore } from '@/stores/reviewStore'
import { fetchIntegratedReviewProgress, saveIntegratedReviewProgress } from '@/api'
import CharacterSelector from './CharacterSelector.vue'

// Debug logging helper with module tag
const DEBUG = true // Set to true for debugging review module
const debugLog = (module: string, ...args: any[]) => {
  if (DEBUG) {
    console.log(`[ReviewPanel:${module}]`, ...args)
  }
}
const debugWarn = (module: string, ...args: any[]) => {
  if (DEBUG) {
    console.warn(`[ReviewPanel:${module}]`, ...args)
  }
}

// Stores
const chatStore = useChatStore()
const configStore = useConfigStore()
const reviewStore = useReviewStore()
const currentCharacter = computed(() => chatStore.currentCharacter)

// API data state - new structured review format
const reviewData = ref<IntegratedReviewData | null>(null)
const isLoading = ref(false)
const isRegenerating = ref(false)
const isPolling = ref(false)
const pollIntervalId = ref<NodeJS.Timeout | null>(null)
const pollAttempts = ref(0)
const MAX_POLL_ATTEMPTS = 60 // 最多轮询60次，每次3秒，总共3分钟
const POLL_INTERVAL = 3000 // 3秒轮询间隔
const reviewDays = ref(7) // 复习时间范围（天）
const error = ref('')
const customGreeting = ref('') // 临时自定义问候语
const expandedGroups = ref<string[]>([]) // 展开的组ID数组

// Draggable standee logic - using left/top positioning to avoid drift
const standeeRef = ref<HTMLElement | null>(null)
const isDragging = ref(false)
const position = ref({ x: 0, y: 0 }) // 使用 left/top 而不是 right/bottom
const startMouse = ref({ x: 0, y: 0 })
const startPos = ref({ x: 0, y: 0 })

// 计算阴影方向 - 光源在屏幕中心
const shadowStyle = computed(() => {
  const centerX = window.innerWidth / 2
  const centerY = window.innerHeight / 2
  const charCenterX = position.value.x + 110 // 人物中心X (width/2)
  const charCenterY = position.value.y + 220 // 人物中心Y (height/2)

  // 计算从光源到人物的方向向量
  const dx = charCenterX - centerX
  const dy = charCenterY - centerY

  // 计算距离比例
  const distance = Math.sqrt(dx * dx + dy * dy)
  const maxDistance = Math.sqrt(centerX * centerX + centerY * centerY)

  // 计算阴影倾斜 - 以足部为原点旋转
  // 光源在中心，人物位置决定倾斜方向和程度
  const distanceRatio = Math.min(distance / maxDistance, 1)  // 0~1

  // scaleY 压缩：光源越远阴影越"平"
  const shadowScaleY = 0.75 + distanceRatio * 0.15  // 0.75~0.9

  // skewX 倾斜：人物在左影子向左偏，人物在右影子向右偏
  const skewAngle = -(dx / centerX) * 15  // 最大±15度

  // 去掉translateX，保持底部对齐
  return {
    transform: `scale(1, ${shadowScaleY}) skewX(${skewAngle}deg)`,
    transformOrigin: 'bottom center'
  }
})

const startDrag = (e: MouseEvent | TouchEvent) => {
  isDragging.value = true
  const clientX = 'touches' in e && e.touches.length > 0 ? e.touches[0].clientX : (e as MouseEvent).clientX
  const clientY = 'touches' in e && e.touches.length > 0 ? e.touches[0].clientY : (e as MouseEvent).clientY

  // 记录鼠标起始位置
  startMouse.value = { x: clientX, y: clientY }

  // 记录元素当前位置（转换为 left/top）
  const rect = standeeRef.value?.getBoundingClientRect()
  if (rect) {
    startPos.value = { x: rect.left, y: rect.top }
  }

  document.addEventListener('mousemove', onDrag)
  document.addEventListener('mouseup', stopDrag)
  document.addEventListener('touchmove', onDrag, { passive: false })
  document.addEventListener('touchend', stopDrag)
}

const onDrag = (e: MouseEvent | TouchEvent) => {
  if (!isDragging.value) return
  e.preventDefault()

  const clientX = 'touches' in e && e.touches.length > 0 ? e.touches[0].clientX : (e as MouseEvent).clientX
  const clientY = 'touches' in e && e.touches.length > 0 ? e.touches[0].clientY : (e as MouseEvent).clientY

  // 计算鼠标移动距离
  const deltaX = clientX - startMouse.value.x
  const deltaY = clientY - startMouse.value.y

  // 新位置 = 起始位置 + 移动距离
  let newX = startPos.value.x + deltaX
  let newY = startPos.value.y + deltaY

  // 限制在视口范围内 - 使用实际容器尺寸320x540
  const maxX = window.innerWidth - 320
  const maxY = window.innerHeight - 540

  position.value = {
    x: Math.max(0, Math.min(newX, maxX)),
    y: Math.max(0, Math.min(newY, maxY))
  }
}

const stopDrag = () => {
  isDragging.value = false
  document.removeEventListener('mousemove', onDrag)
  document.removeEventListener('mouseup', stopDrag)
  document.removeEventListener('touchmove', onDrag)
  document.removeEventListener('touchend', stopDrag)
}

// Fetch integrated review data (not dependent on current session)
const fetchReviewData = async (forceRefresh = false) => {
  isLoading.value = true
  error.value = ''

  try {
    debugLog('fetch', 'Loading integrated review data...', { forceRefresh })

    // Get API configuration from config store
    const { apiKey, baseUrl, model } = configStore.apiConfig
    debugLog('fetch', '使用API配置:', { baseUrl, model, hasApiKey: !!apiKey })

    // Call store method to load integrated review data
    const result = await reviewStore.loadIntegratedReview(10, reviewDays.value, forceRefresh, apiKey, baseUrl, model)
    debugLog('fetch', 'Integrated review result received:', result)

    // Check the result status
    if (result.status === 'regenerating') {
      // Review regeneration started
      debugLog('fetch', 'Review regeneration started:', result.taskInfo)

      // Show regeneration message
      error.value = '复习内容正在重新生成中，请稍后刷新...'

      // Schedule automatic refresh after 10 seconds
      setTimeout(() => {
        debugLog('fetch', 'Auto-refreshing after regeneration delay')
        fetchReviewData(false) // Refresh without force
      }, 10000)
    } else if (result.status === 'completed') {
      // Normal response with integrated review data
      const data = result.data
      debugLog('fetch', 'Integrated review data:', data)

      // Store the integrated review data
      reviewData.value = data
      error.value = ''

      // Load saved progress and apply to the data
      try {
        const progressData = await fetchIntegratedReviewProgress(reviewDays.value)
        debugLog('fetch', 'Progress data from server:', progressData)
        if (progressData) {
          const learnedCards = progressData.learned_cards || []
          const completedQuizzes = progressData.completed_quizzes || []
          const totalCards = data.review_groups?.reduce((sum, g) => sum + (g.knowledge_cards?.length || 0), 0) || 0
          const totalQuestions = data.review_groups?.reduce((sum, g) => sum + (g.quiz_questions?.length || 0), 0) || 0
          debugLog('fetch', 'Applying progress:', { learnedCards, completedQuizzes, totalCards, totalQuestions })
          applyProgress(data, learnedCards, completedQuizzes)
          const card1 = data.review_groups?.[0]?.knowledge_cards?.find(c => c.id === 'card_1')
          debugLog('fetch', 'After applyProgress, card_1 is_learned:', card1?.is_learned)
        } else {
          debugWarn('fetch', 'progressData is falsy')
        }
      } catch (progressErr) {
        debugWarn('fetch', 'Failed to load progress:', progressErr)
      }
    } else {
      throw new Error(`Unexpected result status: ${result.status}`)
    }
  } catch (err: any) {
    // Error handling for integrated review
    const errorObj = err.originalError || err
    let errorMessage = '获取整合复习数据失败'
    let errorDetails = ''

    debugWarn('fetch', 'Error details:', {
      message: err.message,
      originalError: err.originalError ? 'present' : 'absent',
      response: errorObj.response ? `status: ${errorObj.response.status}` : 'none',
      request: errorObj.request ? 'present' : 'none',
      code: errorObj.code,
      isAxiosError: errorObj.isAxiosError
    })

    if (errorObj.response) {
      // Server responded with error status
      const status = errorObj.response.status
      const data = errorObj.response.data || {}
      errorMessage = `服务器错误 (${status})`
      errorDetails = data.detail || data.message || JSON.stringify(data)
      debugWarn('fetch', `Server error ${status}:`, errorDetails)

      if (status === 500) {
        errorMessage = '服务器内部错误，请检查后端日志'
      } else if (status === 404) {
        errorMessage = '整合复习API不存在，请确认后端路由正确'
      } else if (status === 422) {
        errorMessage = '请求参数错误，请检查API配置'
      } else if (status === 400) {
        errorMessage = '请求错误，请检查参数'
      }
    } else if (errorObj.request) {
      // Request made but no response
      errorMessage = '网络错误：服务器无响应'
      errorDetails = '请检查后端服务器是否运行 (uv run python -m backend.main)'
      debugWarn('fetch', 'Network error, no response:', errorObj.request)

      if (errorObj.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        errorMessage = '请求超时 (30秒)'
        errorDetails = '后端处理过慢或LLM调用失败。检查：1) 后端日志 2) API配置是否正确 3) Ollama服务是否运行'
      }
    } else {
      // Something else happened
      errorMessage = err.message || '未知错误'
      errorDetails = errorObj.toString()
      debugWarn('fetch', 'Other error:', errorObj)
    }

    error.value = `${errorMessage}${errorDetails ? `: ${errorDetails}` : ''}`
  } finally {
    isLoading.value = false
  }
}

// Types for new structured review format
interface KnowledgeCard {
  id: string
  content: string
  is_learned: boolean
}

interface QuizQuestion {
  id: string
  question: string
  options: string[]
  correct_answer: number
  explanation: string
  difficulty: 'easy' | 'medium' | 'hard'
  is_completed: boolean
  user_answer?: number
  is_correct?: boolean
}

interface ReviewGroup {
  id: string
  title: string
  description: string
  knowledge_cards: KnowledgeCard[]
  quiz_questions: QuizQuestion[]
  frequency: number  // How many sessions mentioned this topic
  session_count: number  // Number of sessions contributing to this group
}

interface SessionInfo {
  session_id: string
  generated_at?: string
  recency_weight?: number
  message_count?: number
}

interface IntegratedReviewData {
  aggregated_summary: string
  review_groups: ReviewGroup[]
  next_review_date: string
  session_count: number
  total_groups: number
  total_knowledge_cards: number
  total_quiz_questions: number
  sessions: SessionInfo[]
}

// Legacy review items for compatibility
const reviewItems = computed<any[]>(() => {
  if (reviewData.value && reviewData.value.review_groups && reviewData.value.review_groups.length > 0) {
    // Return a dummy array to indicate there is review content
    return [{}]
  }
  return []
})

// Computed properties
const pendingCount = computed(() => {
  return reviewItems.value.filter(item => item.status === 'pending').length
})

const masteredCount = computed(() => {
  return reviewItems.value.filter(item => item.status === 'reviewed').length
})

const progressPercentage = computed(() => {
  if (reviewItems.value.length === 0) return 0
  const totalProgress = reviewItems.value.reduce((sum, item) => sum + item.progress, 0)
  return Math.round(totalProgress / reviewItems.value.length)
})

// Review groups from new structured data format
// (directly uses reviewData.review_groups in template, no wrapper computed needed)

const isAvatarClickable = computed(() => {
  return !isLoading.value && !isRegenerating.value
})

// Integrated review statistics
const sessionCount = computed(() => {
  return reviewData.value?.session_count || 0
})


const summaryText = computed(() => {
  return reviewData.value?.aggregated_summary || ''
})

const characterGreeting = computed(() => {
  if (customGreeting.value) {
    return customGreeting.value
  }
  const greetings = currentCharacter.value.greetings
  return greetings[Math.floor(Math.random() * greetings.length)]
})

// Methods
const getCategoryColor = (category: string) => {
  const colorMap: Record<string, string> = {
    'ai': '#c9a0dc',
    'deep-learning': '#9C89B8',
    'nlp': '#B8D0EB',
    'cv': '#87ceeb',
    'math': '#dda0dd',
    'programming': '#dda0dd',
    'quiz': '#ffb6c1',
    'general': '#c9a0dc',
    'summary': '#98fb98'
  }
  return colorMap[category] || '#c9a0dc'
}

const getStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    'pending': '待复习',
    'reviewing': '进行中',
    'reviewed': '已掌握'
  }
  return statusMap[status] || status
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  const now = new Date()
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return '今天'
  if (diffDays === 1) return '昨天'
  if (diffDays < 7) return `${diffDays}天前`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}周前`
  return `${Math.floor(diffDays / 30)}月前`
}

const getGroupProgress = (group: ReviewGroup): number => {
  const totalCards = group.knowledge_cards?.length || 0
  const totalQuestions = group.quiz_questions?.length || 0
  const totalItems = totalCards + totalQuestions

  if (totalItems === 0) return 0

  // 计算已学习的知识卡片
  const learnedCards = group.knowledge_cards?.filter(card => card.is_learned).length || 0

  // 计算已完成的选择题
  const completedQuestions = group.quiz_questions?.filter(question => question.is_completed).length || 0

  const completedItems = learnedCards + completedQuestions

  // 计算进度百分比
  return Math.round((completedItems / totalItems) * 100)
}

const toggleGroupExpansion = (groupId: string) => {
  debugLog('groups', '切换组展开状态:', groupId, '当前状态:', expandedGroups.value.includes(groupId))

  const index = expandedGroups.value.indexOf(groupId)
  if (index > -1) {
    // Remove from array if already expanded
    expandedGroups.value.splice(index, 1)
  } else {
    // Add to array if not expanded
    expandedGroups.value.push(groupId)
  }

  debugLog('groups', '更新后状态:', expandedGroups.value)
}

const startReview = (item: ReviewItem) => {
  debugLog('review', '开始复习:', item.title)
  // TODO: 实现复习逻辑
  item.status = 'reviewing'
  // 在实际应用中，这里会跳转到复习界面或弹出复习对话框
}

const refreshReview = () => {
  fetchReviewData(false)
}

const refreshOnAvatarClick = () => {
  if (isLoading.value || isRegenerating.value) {
    debugLog('avatar', '正在加载或生成中，请稍候')
    return
  }

  debugLog('avatar', '点击头像刷新/生成复习内容')

  // 添加点击反馈动画
  const avatar = document.querySelector('.character-avatar')
  if (avatar) {
    avatar.classList.add('avatar-clicked')
    setTimeout(() => avatar.classList.remove('avatar-clicked'), 300)
  }

  if (reviewItems.length > 0) {
    // 有数据：刷新现有数据
    refreshReview()
  } else {
    // 无数据：重新生成
    regenerateReview()
  }
}

const regenerateOnAvatarDoubleClick = () => {
  if (isRegenerating.value || isLoading.value) {
    debugLog('avatar', '正在重新生成中，请稍候')
    return
  }

  debugLog('avatar', '双击头像触发重新生成复习内容')

  // 设置自定义问候语（樱岛麻衣口吻）
  customGreeting.value = '学姐看看你最近都学了些什么...'

  // 添加双击反馈动画
  const avatar = document.querySelector('.character-avatar')
  if (avatar) {
    avatar.classList.add('avatar-double-clicked')
    setTimeout(() => avatar.classList.remove('avatar-double-clicked'), 500)
  }

  // 触发重新生成
  regenerateReview()

  // 5秒后恢复默认问候语
  setTimeout(() => {
    customGreeting.value = ''
    debugLog('avatar', '恢复默认问候语')
  }, 5000)
}

const regenerateReview = async () => {
  if (isRegenerating.value) return

  debugLog('regenerate', '触发整合复习重新生成')
  isRegenerating.value = true
  error.value = ''

  try {
    // Get API configuration from config store
    const { apiKey, baseUrl, model } = configStore.apiConfig
    debugLog('regenerate', '使用API配置:', { baseUrl, model, hasApiKey: !!apiKey })

    const result = await reviewStore.regenerateIntegratedReview(10, reviewDays.value, apiKey, baseUrl, model)

    if (result.status === 'regenerating') {
      // 重新生成已触发，显示消息
      debugLog('regenerate', '重新生成已触发:', result.taskInfo)

      // 显示重新生成中的状态
      // 不设置 error，保持现有界面内容可见

      // 启动轮询，等待生成完成
      startPollingForReviewData()

    } else if (result.status === 'completed') {
      // 直接返回了数据（不太可能发生）
      debugLog('regenerate', '重新生成完成，数据已更新')
      reviewData.value = result.data
      isRegenerating.value = false
    }
  } catch (err: any) {
    debugWarn('regenerate', '重新生成失败:', err)
    error.value = `重新生成失败: ${err.message}`
    isRegenerating.value = false
  }
}

const startPollingForReviewData = () => {
  if (isPolling.value) {
    debugLog('polling', '轮询已在进行中')
    return
  }

  debugLog('polling', '开始轮询复习数据')
  isPolling.value = true
  pollAttempts.value = 0

  pollIntervalId.value = setInterval(async () => {
    pollAttempts.value++

    if (pollAttempts.value >= MAX_POLL_ATTEMPTS) {
      // 轮询超时
      debugWarn('polling', `轮询超时，已达最大尝试次数: ${MAX_POLL_ATTEMPTS}`)
      stopPolling()
      error.value = '复习内容生成超时，请稍后手动刷新'
      isRegenerating.value = false
      return
    }

    debugLog('polling', `轮询尝试 ${pollAttempts.value}/${MAX_POLL_ATTEMPTS}`)

    try {
      // 获取API配置
      const { apiKey, baseUrl, model } = configStore.apiConfig

      // 调用store方法检查数据
      const result = await reviewStore.loadIntegratedReview(10, reviewDays.value, false, apiKey, baseUrl, model)


      if (result.status === 'completed') {
        const data = result.data
        debugLog('polling', '获取到复习数据:', data)

        // 检查是否有实际数据（不仅仅是占位符）
        const hasActualData = data.aggregated_summary !== 'No review data available.' &&
          data.review_groups?.length > 0

        if (hasActualData) {
          // 有实际数据，停止轮询
          debugLog('polling', '检测到实际数据，停止轮询')
          reviewData.value = data
          error.value = ''

          // Load saved progress
          try {
            const progressData = await fetchIntegratedReviewProgress(reviewDays.value)
            debugLog('polling', 'Progress data from server:', progressData)
            if (progressData) {
              applyProgress(data, progressData.learned_cards || [], progressData.completed_quizzes || [])
            }
          } catch (progressErr) {
            debugWarn('polling', 'Failed to load progress:', progressErr)
          }

          stopPolling()
          isRegenerating.value = false
        } else {
          debugLog('polling', '无实际数据，继续轮询')
        }
      } else if (result.status === 'regenerating') {
        // 仍在生成中，继续轮询
        debugLog('polling', '仍在生成中，继续轮询')
      } else {
        debugWarn('polling', '意外的响应状态:', result.status)
      }
    } catch (err: any) {
      debugWarn('polling', '轮询时出错:', err)
      // 继续轮询，不停止
    }
  }, POLL_INTERVAL)
}

const stopPolling = () => {
  if (pollIntervalId.value) {
    clearInterval(pollIntervalId.value)
    pollIntervalId.value = null
  }
  isPolling.value = false
  debugLog('polling', '轮询已停止')
}

const generateReview = () => {
  debugLog('review', '智能生成复习内容')
  // TODO: 调用API生成复习内容
}

const exportReview = () => {
  debugLog('review', '导出复习笔记')
  // TODO: 实现导出功能
}

// Apply saved progress to review data
const applyProgress = (data: IntegratedReviewData, learnedCards: string[], completedQuizzes: string[]) => {
  if (!data?.review_groups) return

  for (const group of data.review_groups) {
    // Apply learned card status (qualified ID: "groupId:cardId")
    if (group.knowledge_cards) {
      for (const card of group.knowledge_cards) {
        if (learnedCards.includes(card.id) || learnedCards.includes(`${group.id}:${card.id}`)) {
          card.is_learned = true
        }
      }
    }

    // Apply completed quiz status (qualified ID: "groupId:questionId")
    if (group.quiz_questions) {
      for (const question of group.quiz_questions) {
        if (completedQuizzes.includes(question.id) || completedQuizzes.includes(`${group.id}:${question.id}`)) {
          question.is_completed = true
        }
      }
    }
  }
}

// Save current progress to server
const saveProgress = async () => {
  if (!reviewData.value?.review_groups) return

  const learnedCards: string[] = []
  const completedQuizzes: string[] = []

  for (const group of reviewData.value.review_groups) {
    if (group.knowledge_cards) {
      for (const card of group.knowledge_cards) {
        if (card.is_learned) {
          learnedCards.push(`${group.id}:${card.id}`) // qualified ID to avoid cross-group collisions
        }
      }
    }
    if (group.quiz_questions) {
      for (const question of group.quiz_questions) {
        if (question.is_completed) {
          completedQuizzes.push(`${group.id}:${question.id}`)
        }
      }
    }
  }

  try {
    await saveIntegratedReviewProgress(reviewDays.value, learnedCards, completedQuizzes)
    debugLog('progress', 'Progress saved:', { learnedCards: learnedCards.length, completedQuizzes: completedQuizzes.length })
  } catch (err) {
    debugWarn('progress', 'Failed to save progress:', err)
  }
}

// Toggle knowledge card learned status
const toggleCardLearned = (groupId: string, cardId: string, isLearned: boolean) => {
  debugLog('cards', '切换知识卡片学习状态:', { groupId, cardId, isLearned })

  if (!reviewData.value) return

  // Find the card in the specified group only
  const group = reviewData.value.review_groups.find(g => g.id === groupId)
  if (!group?.knowledge_cards) return
  const card = group.knowledge_cards.find(c => c.id === cardId)
  if (!card) return

  card.is_learned = isLearned
  saveProgress()
}

// Handle quiz question answer selection
const selectAnswer = (groupId: string, questionId: string, answerIndex: number) => {
  debugLog('quiz', '选择答案:', { groupId, questionId, answerIndex })

  if (!reviewData.value) return

  // Find the question in the specified group only
  const group = reviewData.value.review_groups.find(g => g.id === groupId)
  if (!group?.quiz_questions) return
  const question = group.quiz_questions.find(q => q.id === questionId)
  if (!question) return

  // Mark as completed and check correctness
  question.is_completed = true
  question.user_answer = answerIndex
  question.is_correct = answerIndex === question.correct_answer

  // Save progress to server
  saveProgress()
}

// Lifecycle
onMounted(() => {
  // 初始化人物位置
  if (position.value.x === 0 && position.value.y === 0) {
    position.value = {
      x: window.innerWidth - 340,
      y: window.innerHeight - 620
    }
  }

  // 初始获取整合复习数据（不依赖当前session）
  fetchReviewData(false)
})

onUnmounted(() => {
  stopDrag()
  stopPolling()
})
</script>

<style scoped>
.review-panel {
  background: linear-gradient(135deg, #faf8ff 0%, #f5f0fa 100%);
  border-radius: 20px;
  padding: 25px;
  box-shadow: 0 10px 30px rgba(156, 137, 184, 0.15);
  font-family: 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
  height: 100%;
  overflow-y: auto;
  color: #4a4a6d;
  position: relative;
}

.review-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
  padding-bottom: 20px;
  border-bottom: 2px solid rgba(201, 160, 220, 0.5);
}

.anime-character {
  display: flex;
  align-items: center;
  gap: 15px;
}

.character-standee {
  position: fixed;
  width: 320px;
  height: 540px;
  z-index: 100;
  pointer-events: auto;
  opacity: 1;
  transition: transform 0.2s ease;
  user-select: none;
  -webkit-user-drag: none;
  /* 内部内容居中，给阴影留出空间 */
  display: flex;
  align-items: center;
  justify-content: center;
  margin-left: -50px;
  margin-top: -50px;
}

.character-standee:hover {
  transform: scale(1.01);
}

.character-standee.dragging {
  transform: scale(1.03);
  z-index: 1000;
  transition: none;
}

.character-standee.dragging .character-shadow {
  opacity: 0.5;
  filter: blur(15px) brightness(0);
}

.standee-wrapper {
  position: relative;
  width: 260px;
  height: 440px;
}

/* 地面投影 - 点光源效果，光源在屏幕中心 */
/* 注意：图片底部有约20px透明空隙，阴影需要上移对齐实际足部 */
.character-shadow {
  position: absolute;
  bottom: 60px; /* 上移补偿图片底部透明区域 */
  left: 50%;
  width: 220px;
  height: 420px; /* 高度相应减小 */
  margin-left: -110px; /* 宽度一半，水平居中 */
  background: url('/Sakuraji_Mai02.webp') no-repeat center bottom;
  background-size: contain;
  filter: blur(6px) brightness(0);
  opacity: 0.55;
  transform-origin: bottom center;
  z-index: -1;
  pointer-events: none;
  /* 头部淡化渐变，底部更实 */
  -webkit-mask-image: linear-gradient(
    to bottom,
    transparent 0%,
    rgba(0, 0, 0, 0.2) 15%,
    rgba(0, 0, 0, 0.6) 30%,
    black 50%,
    black 100%
  );
  mask-image: linear-gradient(
    to bottom,
    transparent 0%,
    rgba(0, 0, 0, 0.2) 15%,
    rgba(0, 0, 0, 0.6) 30%,
    black 50%,
    black 100%
  );
  transition: transform 0.1s ease-out;
}

.standee-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  object-position: bottom;
  /* 轻微的人物边缘阴影 */
  filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.3));
  pointer-events: none;
  position: relative;
  z-index: 1;
}

@media (max-width: 1200px) {
  .character-standee {
    width: 240px;
    height: 420px;
  }
  .standee-wrapper {
    width: 160px;
    height: 320px;
  }
  .character-shadow {
    width: 160px;
    height: 300px; /* 补偿底部空隙 */
    margin-left: -80px;
    bottom: 20px;
  }
}

@media (max-width: 768px) {
  .character-standee {
    width: 180px;
    height: 340px;
  }
  .standee-wrapper {
    width: 120px;
    height: 240px;
  }
  .character-shadow {
    width: 120px;
    height: 220px; /* 补偿底部空隙 */
    margin-left: -60px;
    bottom: 20px;
  }
}

.character-avatar {
  width: 70px;
  height: 70px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  box-shadow: 0 8px 20px rgba(201, 160, 220, 0.4);
  animation: float 3s ease-in-out infinite;
  border: 3px solid rgba(201, 160, 220, 0.5);
}

.character-initial {
  color: white;
  font-weight: bold;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

.character-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: top center;
  border-radius: 50%;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}

.character-name {
  margin: 0;
  color: #7a6a9d;
  font-size: 1.4rem;
  font-weight: 600;
}

.character-greeting {
  margin: 5px 0 0 0;
  color: #777;
  font-size: 0.9rem;
  font-style: italic;
}

.review-stats {
  display: flex;
  gap: 25px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
}

.stat-label {
  font-size: 0.85rem;
  color: #666;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: bold;
  color: #9C89B8;
}

.progress-section {
  margin-bottom: 25px;
}

.progress-label {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 0.95rem;
  color: #555;
}

.progress-value {
  font-weight: bold;
  color: #9C89B8;
}

.progress-bar {
  height: 10px;
  background: rgba(201, 160, 220, 0.15);
  border-radius: 5px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #c9a0dc 0%, #9C89B8 100%);
  border-radius: 5px;
  transition: width 0.5s ease;
}

.review-cards {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 25px;
}

.review-card {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 15px;
  padding: 20px;
  box-shadow: 0 5px 15px rgba(156, 137, 184, 0.1);
  border: 1px solid rgba(201, 160, 220, 0.3);
  transition: all 0.3s ease;
}

.review-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(201, 160, 220, 0.2);
  border-color: rgba(201, 160, 220, 0.5);
  background: rgba(255, 255, 255, 1);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 15px;
  margin-bottom: 15px;
}

.card-character {
  flex-shrink: 0;
}

.character-icon {
  display: inline-block;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: transparent;
  border: 2px solid rgba(201, 160, 220, 0.8);
  box-shadow: 0 0 5px rgba(201, 160, 220, 0.3);
}

.card-info {
  flex: 1;
  min-width: 0;
}

.card-title {
  margin: 0 0 5px 0;
  color: #7a6a9d;
  font-size: 1.1rem;
  font-weight: 600;
}

.card-meta {
  display: flex;
  gap: 15px;
  font-size: 0.85rem;
  color: #666;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.card-status {
  flex-shrink: 0;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 500;
}

.status-badge.pending {
  background: rgba(255, 152, 0, 0.1);
  color: #f57c00;
  border: 1px solid rgba(255, 152, 0, 0.3);
}

.status-badge.reviewing {
  background: rgba(33, 150, 243, 0.1);
  color: #2196f3;
  border: 1px solid rgba(33, 150, 243, 0.3);
}

.status-badge.reviewed {
  background: rgba(76, 175, 80, 0.1);
  color: #4caf50;
  border: 1px solid rgba(76, 175, 80, 0.3);
}

.card-content {
  margin-bottom: 15px;
}

.card-description {
  margin: 0 0 10px 0;
  color: #666;
  line-height: 1.5;
  font-size: 0.95rem;
}

.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  background: rgba(201, 160, 220, 0.2);
  color: #8a7aad;
  padding: 4px 10px;
  border-radius: 15px;
  font-size: 0.8rem;
  border: 1px solid rgba(201, 160, 220, 0.4);
}

.card-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-progress {
  display: flex;
  align-items: center;
  gap: 10px;
}

.mini-progress-bar {
  width: 100px;
  height: 6px;
  background: rgba(201, 160, 220, 0.15);
  border-radius: 3px;
  overflow: hidden;
}

.mini-progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #c9a0dc 0%, #9C89B8 100%);
  border-radius: 3px;
  transition: width 0.5s ease;
}

.progress-text {
  font-size: 0.9rem;
  color: #9C89B8;
  font-weight: 500;
  min-width: 40px;
}

.review-btn {
  background: linear-gradient(135deg, #c9a0dc 0%, #9C89B8 100%);
  color: white;
  border: none;
  padding: 8px 20px;
  border-radius: 20px;
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
}

.review-btn:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(201, 160, 220, 0.4);
}

.review-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Review Groups Styles */
.review-groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 25px;
}

.review-group {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  border: 1px solid rgba(201, 160, 220, 0.3);
  overflow: hidden;
  transition: all 0.3s ease;
}

.review-group:hover {
  border-color: rgba(201, 160, 220, 0.5);
  box-shadow: 0 4px 12px rgba(201, 160, 220, 0.15);
}

.group-header {
  display: flex;
  align-items: center;
  padding: 16px 20px;
  background: rgba(201, 160, 220, 0.05);
  transition: background 0.2s ease;
}


.group-icon {
  flex-shrink: 0;
  margin-right: 12px;
}

.group-icon-circle {
  display: inline-block;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid rgba(201, 160, 220, 0.8);
  background: transparent;
}

.group-info {
  flex: 1;
  min-width: 0;
}

.group-title {
  margin: 0 0 4px 0;
  color: #7a6a9d;
  font-size: 1rem;
  font-weight: 600;
}

.group-meta {
  display: flex;
  gap: 12px;
  font-size: 0.85rem;
  color: #666;
}

.group-expand {
  flex-shrink: 0;
  margin-left: 12px;
}

.expand-icon {
  display: inline-block;
  font-size: 1.5rem;
  color: #9C89B8;
  transition: transform 0.3s ease;
  transform: rotate(0deg);
}

.expand-icon.expanded {
  transform: rotate(90deg);
}

.group-items {
  padding: 0 20px 16px 20px;
  border-top: 1px solid rgba(201, 160, 220, 0.1);
}

.group-item {
  padding: 12px 0;
  border-bottom: 1px solid rgba(201, 160, 220, 0.05);
}

.group-item:last-child {
  border-bottom: none;
}

/* Section containers for knowledge cards and quiz questions */
.section-container {
  margin: 16px 0;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(201, 160, 220, 0.2);
  overflow: hidden;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: rgba(201, 160, 220, 0.05);
  border-bottom: 1px solid rgba(201, 160, 220, 0.1);
}

.section-title {
  margin: 0;
  color: #7a6a9d;
  font-size: 1rem;
  font-weight: 600;
}

.section-count {
  font-size: 0.85rem;
  color: #666;
}

/* Knowledge cards styles */
.knowledge-cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
}

.knowledge-card {
  background: white;
  border-radius: 8px;
  border: 1px solid rgba(201, 160, 220, 0.3);
  padding: 12px;
  transition: all 0.2s ease;
}

.knowledge-card:hover {
  border-color: rgba(201, 160, 220, 0.5);
  box-shadow: 0 3px 8px rgba(201, 160, 220, 0.1);
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.card-icon {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #c9a0dc 0%, #9C89B8 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.9rem;
}

.card-content {
  flex: 1;
  min-width: 0;
}

.card-content p {
  margin: 0;
  color: #666;
  line-height: 1.5;
  font-size: 0.95rem;
}

/* Checkbox for card learned status */
.card-checkbox-label {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  cursor: pointer;
  padding: 4px;
  position: relative;
}

.card-checkbox {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.checkbox-custom {
  width: 22px;
  height: 22px;
  border-radius: 6px;
  border: 2px solid rgba(201, 160, 220, 0.4);
  background: rgba(255, 255, 255, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  position: relative;
}

.card-checkbox:checked + .checkbox-custom {
  background: linear-gradient(135deg, #9C89B8 0%, #7c6a9e 100%);
  border-color: #9C89B8;
}

.card-checkbox:checked + .checkbox-custom::after {
  content: '✓';
  color: white;
  font-size: 14px;
  font-weight: bold;
}

.card-checkbox-label:hover .checkbox-custom {
  border-color: rgba(201, 160, 220, 0.8);
  box-shadow: 0 0 8px rgba(201, 160, 220, 0.3);
}

#app[data-theme="dark"] .checkbox-custom {
  background: rgba(40, 40, 60, 0.8);
  border-color: rgba(184, 208, 235, 0.4);
}

#app[data-theme="dark"] .card-checkbox:checked + .checkbox-custom {
  background: linear-gradient(135deg, #B8D0EB 0%, #8aacd4 100%);
  border-color: #B8D0EB;
}

#app[data-theme="dark"] .card-checkbox-label:hover .checkbox-custom {
  border-color: rgba(184, 208, 235, 0.8);
  box-shadow: 0 0 8px rgba(184, 208, 235, 0.3);
}

/* Quiz questions styles */
.quiz-questions {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
}

.quiz-question {
  background: white;
  border-radius: 8px;
  border: 1px solid rgba(156, 137, 184, 0.3);
  padding: 16px;
}

.question-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 16px;
}

.question-icon {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #9C89B8 0%, #7a6a9d 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 0.9rem;
}

.question-content {
  flex: 1;
  min-width: 0;
}

.question-content h6 {
  margin: 0 0 12px 0;
  color: #5a5a7d;
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.4;
}

/* Options display */
.options-display, .options-selection {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.option-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: 6px;
  background: rgba(201, 160, 220, 0.05);
  border: 1px solid rgba(201, 160, 220, 0.1);
}

.option-item.selectable {
  cursor: pointer;
  transition: all 0.2s ease;
}

.option-item.selectable:hover {
  background: rgba(201, 160, 220, 0.1);
  border-color: rgba(201, 160, 220, 0.3);
}

.option-item.correct {
  background: rgba(76, 175, 80, 0.1);
  border-color: rgba(76, 175, 80, 0.3);
}

.option-item.incorrect {
  background: rgba(244, 67, 54, 0.1);
  border-color: rgba(244, 67, 54, 0.3);
}

.option-label {
  flex-shrink: 0;
  font-weight: 600;
  color: #7a6a9d;
  width: 20px;
}

.option-text {
  flex: 1;
  color: #666;
  font-size: 0.9rem;
}

.correct-mark, .incorrect-mark {
  flex-shrink: 0;
  font-size: 0.8rem;
  font-weight: 600;
  padding: 2px 6px;
  border-radius: 4px;
}

.correct-mark {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}

.incorrect-mark {
  background: rgba(244, 67, 54, 0.2);
  color: #f44336;
}

.completed-question .explanation {
  padding: 12px;
  background: rgba(201, 160, 220, 0.05);
  border-radius: 6px;
  border-left: 3px solid #c9a0dc;
  font-size: 0.9rem;
  color: #666;
  line-height: 1.4;
}

.explanation strong {
  color: #7a6a9d;
}

/* Question meta info */
.question-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(201, 160, 220, 0.1);
}

.difficulty-badge {
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
}

.difficulty-badge.easy {
  background: rgba(76, 175, 80, 0.1);
  color: #4caf50;
}

.difficulty-badge.medium {
  background: rgba(255, 152, 0, 0.1);
  color: #f57c00;
}

.difficulty-badge.hard {
  background: rgba(244, 67, 54, 0.1);
  color: #f44336;
}

.completion-status {
  font-size: 0.85rem;
  font-weight: 600;
}

.completion-status {
  color: #4caf50;
}

/* Group statistics */
.group-statistics {
  display: flex;
  gap: 20px;
  padding: 12px 16px;
  background: rgba(201, 160, 220, 0.05);
  border-radius: 8px;
  margin-top: 16px;
  border: 1px solid rgba(201, 160, 220, 0.1);
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stat-label {
  font-size: 0.85rem;
  color: #666;
}

.stat-value {
  font-size: 1rem;
  font-weight: 600;
  color: #9C89B8;
}

.item-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}

.item-character {
  flex-shrink: 0;
  margin-top: 2px;
}

.item-info {
  flex: 1;
  min-width: 0;
}

.item-title {
  margin: 0 0 4px 0;
  color: #5a5a7d;
  font-size: 0.95rem;
  font-weight: 500;
}

.item-description {
  margin: 0 0 8px 0;
  color: #666;
  font-size: 0.85rem;
  line-height: 1.4;
}

.item-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.item-status {
  flex-shrink: 0;
}

.item-actions {
  display: flex;
  justify-content: flex-end;
}

.empty-state {
  text-align: center;
  padding: 40px 20px;
  color: #9C89B8;
}

.empty-character {
  margin-bottom: 20px;
}

.empty-avatar {
  width: 80px;
  height: 80px;
  margin: 0 auto;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(201, 160, 220, 0.4) 0%, rgba(156, 137, 184, 0.4) 100%);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 0.7; }
  50% { transform: scale(1.05); opacity: 1; }
}

.empty-state h4 {
  margin: 0 0 10px 0;
  font-size: 1.3rem;
  color: #7a6a9d;
}

.empty-state p {
  margin: 0 0 20px 0;
  color: #888;
}

.refresh-btn {
  background: linear-gradient(135deg, #c9a0dc 0%, #9C89B8 100%);
  color: white;
  border: none;
  padding: 10px 25px;
  border-radius: 20px;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.3s ease;
}

.refresh-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(201, 160, 220, 0.4);
}

.quick-actions {
  display: flex;
  gap: 10px;
  justify-content: center;
  padding-top: 20px;
  border-top: 2px solid rgba(201, 160, 220, 0.2);
}

.action-btn {
  background: rgba(201, 160, 220, 0.1);
  border: 2px solid rgba(201, 160, 220, 0.3);
  color: #c9a0dc;
  padding: 8px 15px;
  border-radius: 20px;
  cursor: pointer;
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

.action-btn:hover {
  background: rgba(201, 160, 220, 0.2);
  border-color: rgba(201, 160, 220, 0.5);
  transform: translateY(-2px);
}

/* Summary header actions */
.summary-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.summary-title-row h4 {
  margin: 0;
  color: #7a6a9d;
  font-size: 1.1rem;
  font-weight: 600;
}

.summary-actions {
  display: flex;
  gap: 10px;
}

.summary-actions .action-btn {
  padding: 6px 12px;
  font-size: 0.85rem;
}

.summary-actions .refresh-btn {
  background: rgba(156, 137, 184, 0.1);
  border-color: rgba(156, 137, 184, 0.3);
  color: #9C89B8;
}

.summary-actions .regenerate-btn {
  background: rgba(201, 160, 220, 0.15);
  border-color: rgba(201, 160, 220, 0.4);
  color: #c9a0dc;
  font-weight: 600;
}

.summary-actions .regenerate-btn:hover {
  background: rgba(201, 160, 220, 0.25);
  border-color: rgba(201, 160, 220, 0.6);
}

.summary-actions .action-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

/* Integrated Review Summary Styles */
.integrated-summary {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 15px;
  padding: 20px;
  margin-bottom: 25px;
  box-shadow: 0 5px 15px rgba(156, 137, 184, 0.1);
  border: 1px solid rgba(201, 160, 220, 0.3);
  transition: all 0.3s ease;
}

.integrated-summary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(201, 160, 220, 0.15);
  border-color: rgba(201, 160, 220, 0.5);
}

.summary-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  padding-bottom: 15px;
  border-bottom: 2px solid rgba(201, 160, 220, 0.2);
}

.summary-header h4 {
  margin: 0;
  color: #7a6a9d;
  font-size: 1.1rem;
  font-weight: 600;
}

.summary-stats {
  display: flex;
  gap: 20px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
}

.stat-label {
  font-size: 0.8rem;
  color: #666;
  font-weight: 500;
}

.stat-value {
  font-size: 1.3rem;
  font-weight: bold;
  color: #9C89B8;
}

.summary-content {
  color: #666;
  line-height: 1.5;
}

.summary-text {
  margin: 0 0 15px 0;
  font-size: 0.95rem;
}

.key-points h5 {
  margin: 0 0 10px 0;
  color: #7a6a9d;
  font-size: 0.95rem;
  font-weight: 600;
}

.tags-container {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.keypoint-tag {
  background: rgba(201, 160, 220, 0.15);
  color: #8a7aad;
  padding: 6px 12px;
  border-radius: 15px;
  font-size: 0.85rem;
  border: 1px solid rgba(201, 160, 220, 0.3);
  transition: all 0.3s ease;
}

.keypoint-tag:hover {
  background: rgba(201, 160, 220, 0.25);
  transform: translateY(-1px);
}

.more-tag {
  background: rgba(156, 137, 184, 0.1);
  color: #9C89B8;
  padding: 6px 12px;
  border-radius: 15px;
  font-size: 0.85rem;
  font-style: italic;
  border: 1px dashed rgba(156, 137, 184, 0.3);
}

/* Avatar refresh styles */
.character-avatar.clickable {
  cursor: pointer;
  position: relative;
  transition: all 0.3s ease;
}

.character-avatar.clickable:hover {
  transform: scale(1.05);
  box-shadow: 0 12px 25px rgba(201, 160, 220, 0.5);
}

.character-avatar.avatar-clicked {
  animation: avatarPulse 0.3s ease;
}

@keyframes avatarPulse {
  0% { transform: scale(1); }
  50% { transform: scale(0.95); }
  100% { transform: scale(1); }
}

.character-avatar.avatar-double-clicked {
  animation: avatarDoubleClick 0.5s ease;
}

@keyframes avatarDoubleClick {
  0% { transform: scale(1); box-shadow: 0 8px 20px rgba(201, 160, 220, 0.4); }
  25% { transform: scale(0.9); box-shadow: 0 15px 30px rgba(201, 160, 220, 0.6); }
  50% { transform: scale(1.1); box-shadow: 0 20px 40px rgba(201, 160, 220, 0.8); }
  75% { transform: scale(0.95); box-shadow: 0 15px 30px rgba(201, 160, 220, 0.6); }
  100% { transform: scale(1); box-shadow: 0 8px 20px rgba(201, 160, 220, 0.4); }
}

.avatar-refresh-badge {
  position: absolute;
  bottom: -5px;
  right: -5px;
  width: 24px;
  height: 24px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.2);
  border: 2px solid #c9a0dc;
}

.refresh-icon {
  width: 14px;
  height: 14px;
  color: #9C89B8;
  animation: spinSlow 3s linear infinite;
}

@keyframes spinSlow {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Hide refresh badge on mobile for cleaner look */
@media (max-width: 768px) {
  .avatar-refresh-badge {
    width: 20px;
    height: 20px;
    bottom: -3px;
    right: -3px;
  }

  .refresh-icon {
    width: 12px;
    height: 12px;
  }
}

@media (max-width: 768px) {
  .review-header {
    flex-direction: column;
    gap: 20px;
    align-items: stretch;
  }

  .review-stats {
    justify-content: space-around;
  }

  .character-avatar {
    width: 60px;
    height: 60px;
    font-size: 2rem;
  }

  .character-name {
    font-size: 1.2rem;
  }

  .card-header {
    flex-wrap: wrap;
  }

  .card-status {
    order: -1;
    width: 100%;
    margin-bottom: 10px;
  }

  .status-badge {
    width: fit-content;
  }

  .review-panel {
    padding: 15px;
  }

  .character-avatar {
    width: 60px;
    height: 60px;
  }

  /* Integrated summary responsive styles */
  .integrated-summary {
    padding: 15px;
    margin-bottom: 20px;
  }

  .summary-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }

  .summary-stats {
    width: 100%;
    justify-content: space-between;
    gap: 10px;
  }

  .stat-item {
    flex: 1;
    min-width: 0;
  }

  .stat-label {
    font-size: 0.75rem;
  }

  .stat-value {
    font-size: 1.1rem;
  }

  .summary-text {
    font-size: 0.9rem;
  }

  .key-points h5 {
    font-size: 0.9rem;
  }

  .keypoint-tag, .more-tag {
    font-size: 0.8rem;
    padding: 5px 10px;
  }

  /* Loading spinner */
  .loading-spinner {
    width: 40px;
    height: 40px;
    margin: 20px auto;
    border: 3px solid rgba(201, 160, 220, 0.3);
    border-top: 3px solid #c9a0dc;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }

  /* Error state */
  .error-state .empty-avatar {
    background: linear-gradient(135deg, rgba(255, 87, 87, 0.4) 0%, rgba(255, 137, 184, 0.4) 100%);
  }

  .error-state h4 {
    color: #f57c00;
  }

  .error-state p {
    color: #f57c00;
    font-size: 0.9rem;
    margin: 10px 0 20px 0;
    max-width: 300px;
    margin-left: auto;
    margin-right: auto;
  }


  /* Hide refresh badge on mobile for cleaner look */
  @media (max-width: 768px) {
    .avatar-refresh-badge {
      width: 20px;
      height: 20px;
      bottom: -3px;
      right: -3px;
    }

    .refresh-icon {
      width: 12px;
      height: 12px;
    }
  }
}
</style>