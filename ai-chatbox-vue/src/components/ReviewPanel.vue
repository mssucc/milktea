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
      <div class="header-actions">
        <button class="import-note-btn" @click="showImportDialog = true" title="从笔记导入复习内容">
          <svg class="import-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
            <line x1="12" y1="18" x2="12" y2="12"/>
            <polyline points="9 15 12 12 15 15"/>
          </svg>
        </button>
        <CharacterSelector />
      </div>
    </div>



    <!-- Review Groups — nested session accordion when session_groups available -->
    <div v-if="reviewData?.session_groups && reviewData.session_groups.length > 0" class="review-groups">
      <template v-for="sg in reviewData.session_groups" :key="sg.session_id">
        <!-- Single-group session: render group directly, no wrapper -->
        <template v-if="sg.group_count === 1">
          <div v-for="group in sg.groups" :key="group.id" class="review-group">
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
              <button class="delete-btn" :disabled="deletingSession === sg.session_id" @click.stop="handleDeleteSession(sg.session_id)" title="删除该会话复习">
                <span v-if="deletingSession === sg.session_id" class="delete-spinner"></span>
                <span v-else class="delete-icon">×</span>
              </button>
            </div>
            <div v-if="expandedGroups.includes(group.id)" class="group-items">
              <ReviewGroupContent :group="group" @toggle-card="toggleCardLearned" @select-answer="selectAnswer" />
            </div>
          </div>
        </template>

        <!-- Multi-group session: session wrapper with nested groups -->
        <div v-else class="session-wrapper">
          <div class="session-header" @click="toggleSessionExpansion(sg.session_id)">
            <div class="session-header-left">
              <span :class="['session-expand-icon', { 'expanded': expandedSessions.includes(sg.session_id) }]">›</span>
              <div class="session-title-group">
                <h4 class="session-title">{{ sg.title }}</h4>
                <span class="session-meta">{{ sg.group_count }}个题组</span>
              </div>
            </div>
            <button class="delete-btn" :disabled="deletingSession === sg.session_id" @click.stop="handleDeleteSession(sg.session_id)" title="删除该会话全部复习">
              <span v-if="deletingSession === sg.session_id" class="delete-spinner"></span>
              <span v-else class="delete-icon">×</span>
            </button>
          </div>
          <div v-if="expandedSessions.includes(sg.session_id)" class="session-groups">
            <div v-for="group in sg.groups" :key="group.id" class="review-group nested">
              <div class="group-header" @click="toggleGroupExpansion(group.id)">
                <div class="group-icon">
                  <span class="group-icon-circle small"></span>
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
                <button class="delete-btn small" :disabled="deletingGroup === group.id" @click.stop="handleDeleteGroup(sg.session_id, group.id)" title="删除该题组">
                  <span v-if="deletingGroup === group.id" class="delete-spinner"></span>
                  <span v-else class="delete-icon">×</span>
                </button>
              </div>
              <div v-if="expandedGroups.includes(group.id)" class="group-items">
                <ReviewGroupContent :group="group" @toggle-card="toggleCardLearned" @select-answer="selectAnswer" />
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Fallback: flat review_groups when no session_groups -->
    <div v-else class="review-groups">
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
          <ReviewGroupContent :group="group" @toggle-card="toggleCardLearned" @select-answer="selectAnswer" />
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

    <!-- Confirm Delete Dialog -->
    <div v-if="confirmDialog.show" class="import-overlay" @click.self="closeConfirm">
      <div class="import-dialog confirm-dialog">
        <div class="import-dialog-header">
          <h4>{{ confirmDialog.title }}</h4>
        </div>
        <p class="confirm-message">{{ confirmDialog.message }}</p>
        <div class="import-dialog-footer">
          <button @click="closeConfirm" class="dialog-btn cancel">取消</button>
          <button @click="executeConfirm" class="dialog-btn danger">确认删除</button>
        </div>
      </div>
    </div>

    <!-- Import Notes Dialog -->
    <div v-if="showImportDialog" class="import-overlay" @click.self="showImportDialog = false">
      <div class="import-dialog">
        <div class="import-dialog-header">
          <h4>导入笔记</h4>
          <p class="import-dialog-desc">从 Markdown 学习笔记生成复习卡片和题目</p>
        </div>
        <div class="import-mode-tabs">
          <button
            :class="['mode-tab', { active: importMode === 'file' }]"
            @click="importMode = 'file'"
          >单个文件</button>
          <button
            :class="['mode-tab', { active: importMode === 'directory' }]"
            @click="importMode = 'directory'"
          >目录</button>
        </div>
        <div class="import-path-input">
          <input
            v-model="importPath"
            type="text"
            :placeholder="importMode === 'file' ? 'Markdown 文件路径，如 D:\\notes\\topic.md' : '目录路径，如 D:\\Desktop\\vllm\\learn-vllm'"
            @keydown.enter="importNotes"
          />
        </div>
        <div v-if="importResults" class="import-results">
          <div v-for="r in importResults" :key="r.note_id" class="import-result-item">
            <span :class="['result-dot', r.status]"></span>
            <span class="result-name">{{ r.note_id }}</span>
            <span v-if="r.status === 'completed'" class="result-stats">
              {{ r.total_groups }}组 · {{ r.total_knowledge_cards }}卡片 · {{ r.total_quiz_questions }}题
            </span>
            <span v-else class="result-error">{{ r.error || 'failed' }}</span>
          </div>
        </div>
        <div class="import-dialog-footer">
          <button @click="showImportDialog = false" class="dialog-btn cancel">取消</button>
          <button @click="importNotes" class="dialog-btn confirm" :disabled="importingNotes || !importPath.trim()">
            {{ importingNotes ? '导入中...' : '导入' }}
          </button>
        </div>
      </div>
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
import { generateNotesReview } from '@/api'
import ReviewGroupContent from './ReviewGroupContent.vue'

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

// API data state
const reviewData = ref<IntegratedReviewData | null>(null)
const isLoading = ref(false)
const isRegenerating = ref(false)
const reviewDays = ref(7)
const error = ref('')
const customGreeting = ref('')
const expandedGroups = ref<string[]>([])
const pollTimer = ref<ReturnType<typeof setInterval> | null>(null)
const generationInProgress = ref(false)
const batchProgress = ref<{ total: number; completed: number } | null>(null)
const expandedSessions = ref<string[]>([])

// Notes import dialog
const showImportDialog = ref(false)
const importMode = ref<'file' | 'directory'>('file')
const importPath = ref('')
const importingNotes = ref(false)
const importResults = ref<any[] | null>(null)

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

// Fetch integrated review data
const fetchReviewData = async (forceRefresh = false) => {
  isLoading.value = true
  error.value = ''

  try {
    debugLog('fetch', 'Loading integrated review data...', { forceRefresh })

    const { apiKey, baseUrl, model } = configStore.apiConfig
    debugLog('fetch', '使用API配置:', { baseUrl, model, hasApiKey: !!apiKey })

    const result = await reviewStore.loadIntegratedReview(10, reviewDays.value, forceRefresh, apiKey, baseUrl, model)
    debugLog('fetch', 'Integrated review result received:', result)

    const data = result.data
    reviewData.value = data
    error.value = ''

    // Track generation progress for polling
    generationInProgress.value = result.generation_in_progress || false
    batchProgress.value = result.batch_progress || null

    // Poll while batch is running to pick up incremental results
    if (generationInProgress.value) {
      startPolling()
    } else {
      stopPolling()
    }

    // Load saved progress and apply to the data
    try {
      const progressData = await fetchIntegratedReviewProgress(reviewDays.value)
      if (progressData) {
        const learnedCards = progressData.learned_cards || []
        const completedQuizzes = progressData.completed_quizzes || []
        applyProgress(data, learnedCards, completedQuizzes)
      }
    } catch (progressErr) {
      debugWarn('fetch', 'Failed to load progress:', progressErr)
    }
  } catch (err: any) {
    const errorObj = err.originalError || err
    let errorMessage = '获取整合复习数据失败'
    let errorDetails = ''

    if (errorObj.response) {
      const status = errorObj.response.status
      const data = errorObj.response.data || {}
      errorMessage = `服务器错误 (${status})`
      errorDetails = data.detail || data.message || JSON.stringify(data)
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
      errorMessage = '网络错误：服务器无响应'
      errorDetails = '请检查后端服务器是否运行'
      if (errorObj.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
        errorMessage = '请求超时'
        errorDetails = '后端处理过慢或LLM调用失败'
      }
    } else {
      errorMessage = err.message || '未知错误'
    }

    error.value = `${errorMessage}${errorDetails ? `: ${errorDetails}` : ''}`
    debugWarn('fetch', 'Error:', errorMessage, errorDetails)
  } finally {
    isLoading.value = false
  }
}

// Poll while batch generation is running to pick up incremental results
const startPolling = () => {
  if (pollTimer.value) return  // already polling
  debugLog('poll', 'Starting poll for incremental review results')
  pollTimer.value = setInterval(() => {
    debugLog('poll', 'Polling for updated review data...')
    fetchReviewData(false)
  }, 5000)
}

const stopPolling = () => {
  if (pollTimer.value) {
    debugLog('poll', 'Stopping poll')
    clearInterval(pollTimer.value)
    pollTimer.value = null
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

interface SessionGroup {
  session_id: string
  title: string
  generated_at?: string
  groups: ReviewGroup[]
  group_count: number
}

interface IntegratedReviewData {
  aggregated_summary: string
  review_groups: ReviewGroup[]
  session_groups: SessionGroup[]
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

const toggleSessionExpansion = (sessionId: string) => {
  const index = expandedSessions.value.indexOf(sessionId)
  if (index > -1) {
    expandedSessions.value.splice(index, 1)
  } else {
    expandedSessions.value.push(sessionId)
  }
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

const deletingSession = ref<string | null>(null)
const deletingGroup = ref<string | null>(null)

// Confirm dialog state
const confirmDialog = ref<{
  show: boolean
  title: string
  message: string
  onConfirm: () => void
}>({ show: false, title: '', message: '', onConfirm: () => {} })

const showConfirm = (title: string, message: string, onConfirm: () => void) => {
  confirmDialog.value = { show: true, title, message, onConfirm }
}

const closeConfirm = () => {
  confirmDialog.value = { show: false, title: '', message: '', onConfirm: () => {} }
}

const executeConfirm = () => {
  const cb = confirmDialog.value.onConfirm
  closeConfirm()
  cb()
}

const handleDeleteSession = (sessionId: string) => {
  showConfirm('删除会话复习', '将删除该会话的全部复习题组和卡片，此操作不可撤销。', async () => {
    try {
      deletingSession.value = sessionId
      await reviewStore.removeSessionReview(sessionId)
      if (reviewStore.integratedReview.session_groups.length === 0) {
        reviewStore.clearIntegratedReview()
      }
    } catch (err: any) {
      debugWarn('delete', '删除会话复习失败:', err)
    } finally {
      deletingSession.value = null
    }
  })
}

const handleDeleteGroup = (sessionId: string, groupId: string) => {
  showConfirm('删除题组', '将删除该题组及其包含的所有卡片和题目，此操作不可撤销。', async () => {
    try {
      deletingGroup.value = groupId
      await reviewStore.removeReviewGroup(sessionId, groupId)
      if (reviewStore.integratedReview.session_groups.length === 0) {
        reviewStore.clearIntegratedReview()
      }
    } catch (err: any) {
      debugWarn('delete', '删除题组失败:', err)
    } finally {
      deletingGroup.value = null
    }
  })
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

  if (generationInProgress.value) {
    debugLog('avatar', '后台正在生成复习内容，忽略双击触发')
    customGreeting.value = '学姐正在帮你整理复习内容呢，稍等一下...'
    setTimeout(() => { customGreeting.value = '' }, 3000)
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

  // Skip if a background batch is already running
  if (generationInProgress.value) {
    debugLog('regenerate', '后台正在生成复习内容，忽略主动触发')
    return
  }

  debugLog('regenerate', '触发整合复习重新生成')
  isRegenerating.value = true
  error.value = ''
  stopPolling()

  try {
    const { apiKey, baseUrl, model } = configStore.apiConfig
    debugLog('regenerate', '使用API配置:', { baseUrl, model, hasApiKey: !!apiKey })

    // Trigger regeneration (backend fires-and-forgets, returns existing data immediately)
    await reviewStore.regenerateIntegratedReview(10, reviewDays.value, apiKey, baseUrl, model)

    // Refresh display data after a short delay to pick up any newly generated content
    setTimeout(() => {
      fetchReviewData(false)
    }, 5000)
  } catch (err: any) {
    debugWarn('regenerate', '重新生成失败:', err)
    error.value = `重新生成失败: ${err.message}`
  } finally {
    isRegenerating.value = false
  }
}

const importNotes = async () => {
  if (!importPath.value.trim()) return

  importingNotes.value = true
  importResults.value = null

  try {
    const { apiKey, baseUrl, model } = configStore.apiConfig
    const results = await generateNotesReview({
      mode: importMode.value,
      path: importPath.value.trim(),
      api_key: apiKey,
      base_url: baseUrl,
      model,
    })
    importResults.value = results
    showImportDialog.value = false

    // Refresh review data to show newly imported content
    setTimeout(() => fetchReviewData(false), 1000)
  } catch (err: any) {
    debugWarn('notes', 'Import failed:', err)
    importResults.value = [{ status: 'failed', note_id: 'error', error: err.message }]
  } finally {
    importingNotes.value = false
  }
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

  fetchReviewData(false)
})

onUnmounted(() => {
  stopDrag()
  stopPolling()
})

// Apply saved progress to review data (both merged groups and session_groups)
const applyProgress = (data: IntegratedReviewData, learnedCards: string[], completedQuizzes: string[]) => {
  const applyToGroups = (groups: ReviewGroup[]) => {
    for (const group of groups) {
      if (group.knowledge_cards) {
        for (const card of group.knowledge_cards) {
          if (learnedCards.includes(card.id) || learnedCards.includes(`${group.id}:${card.id}`)) {
            card.is_learned = true
          }
        }
      }
      if (group.quiz_questions) {
        for (const question of group.quiz_questions) {
          if (completedQuizzes.includes(question.id) || completedQuizzes.includes(`${group.id}:${question.id}`)) {
            question.is_completed = true
          }
        }
      }
    }
  }

  if (data?.review_groups) {
    applyToGroups(data.review_groups)
  }
  if (data?.session_groups) {
    for (const sg of data.session_groups) {
      applyToGroups(sg.groups)
    }
  }
}

// Save current progress to server
const saveProgress = async () => {
  const learnedCards: string[] = []
  const completedQuizzes: string[] = []

  const collectFromGroups = (groups: ReviewGroup[]) => {
    for (const group of groups) {
      if (group.knowledge_cards) {
        for (const card of group.knowledge_cards) {
          if (card.is_learned) {
            learnedCards.push(`${group.id}:${card.id}`)
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
  }

  if (reviewData.value?.review_groups) {
    collectFromGroups(reviewData.value.review_groups)
  }
  if (reviewData.value?.session_groups) {
    for (const sg of reviewData.value.session_groups) {
      collectFromGroups(sg.groups)
    }
  }

  if (learnedCards.length === 0 && completedQuizzes.length === 0) return

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

  // Search in review_groups and session_groups
  const findAndUpdate = (groups: ReviewGroup[]) => {
    const group = groups.find(g => g.id === groupId)
    if (!group?.knowledge_cards) return false
    const card = group.knowledge_cards.find(c => c.id === cardId)
    if (card) {
      card.is_learned = isLearned
      return true
    }
    return false
  }

  let found = findAndUpdate(reviewData.value.review_groups)
  if (!found && reviewData.value.session_groups) {
    for (const sg of reviewData.value.session_groups) {
      if (findAndUpdate(sg.groups)) { found = true; break }
    }
  }

  if (found) saveProgress()
}

// Handle quiz question answer selection
const selectAnswer = (groupId: string, questionId: string, answerIndex: number) => {
  debugLog('quiz', '选择答案:', { groupId, questionId, answerIndex })

  if (!reviewData.value) return

  const findAndUpdate = (groups: ReviewGroup[]) => {
    const group = groups.find(g => g.id === groupId)
    if (!group?.quiz_questions) return false
    const question = group.quiz_questions.find(q => q.id === questionId)
    if (question) {
      question.is_completed = true
      question.user_answer = answerIndex
      question.is_correct = answerIndex === question.correct_answer
      return true
    }
    return false
  }

  let found = findAndUpdate(reviewData.value.review_groups)
  if (!found && reviewData.value.session_groups) {
    for (const sg of reviewData.value.session_groups) {
      if (findAndUpdate(sg.groups)) { found = true; break }
    }
  }

  if (found) saveProgress()
}

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

/* Session wrapper for nested accordion */
.session-wrapper {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 12px;
  border: 1px solid rgba(156, 137, 184, 0.3);
  overflow: hidden;
  transition: all 0.3s ease;
}

.session-wrapper:hover {
  border-color: rgba(156, 137, 184, 0.5);
  box-shadow: 0 4px 12px rgba(156, 137, 184, 0.1);
}

.session-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 20px;
  background: rgba(156, 137, 184, 0.06);
  cursor: pointer;
  transition: background 0.2s ease;
  user-select: none;
}

.session-header:hover {
  background: rgba(156, 137, 184, 0.12);
}

.session-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.session-expand-icon {
  display: inline-block;
  font-size: 1.4rem;
  color: #9C89B8;
  transition: transform 0.3s ease;
  transform: rotate(0deg);
  flex-shrink: 0;
}

.session-expand-icon.expanded {
  transform: rotate(90deg);
}

.session-title-group {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  flex: 1;
}

.session-title {
  margin: 0;
  color: #6a5a8d;
  font-size: 1rem;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.session-meta {
  font-size: 0.8rem;
  color: #888;
}

.session-groups {
  padding: 8px 12px 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Nested group inside session wrapper */
.review-group.nested {
  border-color: rgba(156, 137, 184, 0.15);
  margin-left: 0;
}

.review-group.nested .group-header {
  padding: 12px 16px;
}

.group-icon-circle.small {
  width: 18px;
  height: 18px;
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

/* Header actions group */
.header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

/* Import note button in header */
.import-note-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  background: rgba(156, 137, 184, 0.08);
  border: 1px solid rgba(156, 137, 184, 0.2);
  border-radius: 8px;
  color: #9c89b8;
  cursor: pointer;
  transition: all 0.2s;
}

.import-note-btn:hover {
  background: rgba(156, 137, 184, 0.15);
  border-color: rgba(156, 137, 184, 0.35);
  color: #7c6aa0;
}

.import-note-btn .import-icon {
  flex-shrink: 0;
}

/* Import dialog overlay */
.import-overlay {
  position: fixed;
  inset: 0;
  background: rgba(74, 74, 109, 0.2);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.import-dialog {
  background: #fff;
  border-radius: 16px;
  padding: 28px;
  width: 460px;
  max-width: 90vw;
  box-shadow: 0 16px 48px rgba(156, 137, 184, 0.2);
  color: #4a4a6d;
}

.import-dialog-header {
  margin-bottom: 20px;
}

.import-dialog-header h4 {
  margin: 0 0 4px;
  font-size: 18px;
  font-weight: 600;
  color: #4a4a6d;
}

.import-dialog-desc {
  margin: 0;
  font-size: 13px;
  color: #8e8ea0;
}

/* Mode tabs */
.import-mode-tabs {
  display: flex;
  gap: 0;
  margin-bottom: 16px;
  background: #f5f0fa;
  border-radius: 10px;
  padding: 3px;
}

.mode-tab {
  flex: 1;
  padding: 8px 0;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #8e8ea0;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-tab.active {
  background: #fff;
  color: #4a4a6d;
  box-shadow: 0 1px 3px rgba(156, 137, 184, 0.15);
}

/* Path input */
.import-path-input {
  margin-bottom: 16px;
}

.import-path-input input {
  width: 100%;
  padding: 10px 14px;
  background: #faf8ff;
  border: 1px solid #e0d8f0;
  border-radius: 10px;
  color: #4a4a6d;
  font-size: 13px;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.import-path-input input:focus {
  outline: none;
  border-color: #9c89b8;
}

.import-path-input input::placeholder {
  color: #c0b8d0;
}

/* Footer */
.import-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.dialog-btn {
  padding: 8px 20px;
  border-radius: 10px;
  border: none;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.dialog-btn.cancel {
  background: #f5f0fa;
  color: #8e8ea0;
}

.dialog-btn.cancel:hover {
  background: #ebe4f5;
  color: #4a4a6d;
}

.dialog-btn.confirm {
  background: linear-gradient(135deg, #9c89b8, #b8a0d8);
  color: #fff;
}

.dialog-btn.confirm:hover {
  background: linear-gradient(135deg, #8b78a7, #a78fc7);
}

.dialog-btn.confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dialog-btn.danger {
  background: linear-gradient(135deg, #e06060, #d04848);
  color: #fff;
}

.dialog-btn.danger:hover {
  background: linear-gradient(135deg, #c85050, #b84040);
}

/* Confirm dialog */
.confirm-dialog {
  width: 380px;
}

.confirm-message {
  margin: 0 0 24px 0;
  font-size: 14px;
  color: #6a6a80;
  line-height: 1.6;
}

/* Results list */
.import-results {
  margin-bottom: 16px;
  max-height: 150px;
  overflow-y: auto;
}

.import-result-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 0;
  font-size: 13px;
  border-bottom: 1px solid #f0ecf5;
}

.import-result-item:last-child {
  border-bottom: none;
}

.result-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.result-dot.completed {
  background: #7bc89c;
}

.result-dot.failed {
  background: #e09090;
}

.result-stats {
  color: #b0a8c0;
  font-size: 12px;
  margin-left: auto;
}

.result-error {
  color: #d08080;
  font-size: 12px;
  margin-left: auto;
}

/* Delete buttons for session and group */
.delete-btn {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: #b0a0c0;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  font-size: 18px;
  line-height: 1;
  padding: 0;
  margin-left: 8px;
}

.delete-btn:hover {
  background: rgba(244, 67, 54, 0.1);
  color: #e06060;
}

.delete-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.delete-btn.small {
  width: 24px;
  height: 24px;
  font-size: 16px;
}

.delete-icon {
  line-height: 1;
}

.delete-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid rgba(224, 96, 96, 0.2);
  border-top-color: #e06060;
  border-radius: 50%;
  animation: delete-spin 0.6s linear infinite;
}

@keyframes delete-spin {
  to { transform: rotate(360deg); }
}

</style>