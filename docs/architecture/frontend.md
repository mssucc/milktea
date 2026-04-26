# 前端架构设计

<!-- BEGIN_MODULE: frontend-architecture -->
<!-- BEGIN_TOC -->
## 目录
1. [项目结构](#project-structure)
2. [Vue 3组件架构](#vue-3-component-architecture)
3. [状态管理](#state-management)
4. [API集成](#api-integration)
5. [样式设计](#styling-design)
6. [复习系统前端](#review-system-frontend)
7. [开发工作流](#development-workflow)
<!-- END_TOC -->

<!-- BEGIN_SECTION: project-structure -->
## 1. 项目结构

```
ai-chatbox-vue/
├── src/
│   ├── components/           # Vue组件
│   │   ├── ChatInterface.vue # 主聊天界面（支持流式）
│   │   ├── ChatBox.vue       # 聊天消息显示组件
│   │   ├── GraphView.vue     # 交互式知识图谱可视化
│   │   ├── ReviewPanel.vue   # 复习推荐面板
│   │   ├── Settings.vue      # 设置面板
│   │   ├── CharacterSelector.vue # 角色选择器
│   │   └── Counter.vue       # 计数器示例组件
│   ├── stores/               # Pinia状态存储
│   │   ├── chatStore.js      # 聊天状态、消息、会话、流式状态
│   │   ├── graphStore.js     # 知识图谱数据
│   │   ├── reviewStore.js    # 复习推荐状态
│   │   └── configStore.js    # 应用配置
│   ├── api/                  # API客户端配置
│   │   └── index.js          # API客户端和端点配置
│   ├── assets/
│   │   ├── styles/
│   │   │   └── cute.css      # 动漫风格样式
│   │   └── images/           # 图片资源
│   ├── App.vue               # 根组件
│   └── main.js               # 应用入口点
├── index.html                # HTML模板
├── vite.config.js            # Vite配置
├── package.json              # 依赖配置
└── tauri/                    # Tauri桌面应用配置
```
<!-- END_SECTION: project-structure -->

<!-- BEGIN_SECTION: vue-3-component-architecture -->
## 2. Vue 3组件架构

### 2.1 Composition API
项目使用Vue 3 Composition API，推荐使用`<script setup>`语法：

```vue
<!-- ReviewPanel.vue示例 -->
<script setup>
import { ref, computed } from 'vue'
import { useReviewStore } from '@/stores/reviewStore'

const reviewStore = useReviewStore()
const expandedGroups = ref<string[]>([])

// 计算属性
const hasReviewData = computed(() => reviewStore.hasIntegratedReviewData)
const reviewGroups = computed(() => reviewStore.integratedReview.review_groups)

// 方法
const toggleGroupExpansion = (groupId) => {
  const index = expandedGroups.value.indexOf(groupId)
  if (index > -1) {
    expandedGroups.value.splice(index, 1)
  } else {
    expandedGroups.value.push(groupId)
  }
}
</script>
```

### 2.2 组件通信模式
1. **Props向下传递**：父组件向子组件传递数据
2. **Emit向上通知**：子组件通过事件通知父组件
3. **状态管理**：跨组件共享状态使用Pinia存储
4. **Provide/Inject**：深层嵌套组件使用（较少使用）

### 2.3 关键组件职责
- **ChatInterface.vue**：主聊天容器，管理聊天会话和消息流
- **ChatBox.vue**：显示单个聊天消息，支持markdown渲染
- **GraphView.vue**：集成vis-network的知识图谱可视化
- **ReviewPanel.vue**：显示结构化复习数据，支持交互
- **Settings.vue**：管理API配置和应用设置
<!-- END_SECTION: vue-3-component-architecture -->

<!-- BEGIN_SECTION: state-management -->
## 3. 状态管理

### 3.1 Pinia存储架构
每个功能领域有独立的Pinia存储：

```javascript
// stores/reviewStore.js示例
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchIntegratedReview } from '@/api'

export const useReviewStore = defineStore('review', () => {
  // State
  const integratedReview = ref({
    aggregated_summary: '',
    review_groups: [],
    next_review_date: null,
    session_count: 0,
    total_groups: 0,
    total_knowledge_cards: 0,
    total_quiz_questions: 0,
    sessions: []
  })
  
  const isLoading = ref(false)
  const error = ref('')
  
  // Getters
  const hasIntegratedReviewData = computed(() => 
    integratedReview.value.review_groups?.length > 0
  )
  
  const integratedProgress = computed(() => {
    // 计算复习进度
    if (!integratedReview.value.review_groups) return 0
    
    let totalItems = 0
    let completedItems = 0
    
    for (const group of integratedReview.value.review_groups) {
      totalItems += (group.knowledge_cards?.length || 0)
      totalItems += (group.quiz_questions?.length || 0)
      completedItems += (group.knowledge_cards?.filter(c => c.is_learned).length || 0)
      completedItems += (group.quiz_questions?.filter(q => q.is_completed).length || 0)
    }
    
    return totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0
  })
  
  // Actions
  const loadIntegratedReview = async (limit = 10, days = 7, forceRefresh = false) => {
    isLoading.value = true
    error.value = ''
    
    try {
      const result = await fetchIntegratedReview(limit, days, forceRefresh)
      // 处理结果...
    } catch (err) {
      error.value = `加载失败: ${err.message}`
    } finally {
      isLoading.value = false
    }
  }
  
  return {
    // State
    integratedReview,
    isLoading,
    error,
    
    // Getters
    hasIntegratedReviewData,
    integratedProgress,
    
    // Actions
    loadIntegratedReview
  }
})
```

### 3.2 存储组织
| 存储 | 职责 | 关键状态 |
|------|------|----------|
| **chatStore.js** | 聊天会话管理 | `messages`, `sessions`, `isStreaming`, `currentSessionId` |
| **graphStore.js** | 知识图谱数据 | `graphData`, `isLoading`, `selectedSessionId` |
| **reviewStore.js** | 复习系统 | `integratedReview`, `isLoading`, `error` |
| **configStore.js** | 应用配置 | `apiKey`, `baseUrl`, `model`, `character` |

### 3.3 响应式模式
- **ref**：用于基本类型和对象
- **computed**：用于派生状态
- **watch**：用于副作用和状态变化响应
- **storeToRefs**：在组件中解构存储状态
<!-- END_SECTION: state-management -->

<!-- BEGIN_SECTION: api-integration -->
## 4. API集成

### 4.1 API客户端配置
```javascript
// api/index.js
import axios from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api',
  timeout: 90000, // 90秒超时（复习生成可能较长）
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器：添加API配置
apiClient.interceptors.request.use((config) => {
  const configStore = useConfigStore()
  
  // 如果请求数据是对象，合并API配置
  if (config.data && typeof config.data === 'object') {
    config.data = {
      ...config.data,
      api_key: configStore.apiKey || undefined,
      base_url: configStore.baseUrl || undefined,
      model: configStore.model || undefined
    }
  }
  
  return config
})

// 导出API端点
export const fetchIntegratedReview = async (limit, days, forceRefresh = false, apiConfig = {}) => {
  const response = await apiClient.post('/review/integrated/overview', {
    limit,
    days,
    force_refresh: forceRefresh,
    ...apiConfig
  })
  return response.data
}

export const submitQuizAnswer = async (sessionId, questionId, answerIndex, apiConfig = {}) => {
  const response = await apiClient.post(`/review/${sessionId}/submit-quiz-answer`, {
    question_id: questionId,
    user_answer: answerIndex,
    ...apiConfig
  })
  return response.data
}
```

### 4.2 流式聊天处理
```javascript
// chatStore.js中的流式处理
async function streamChatMessage(message, sessionId = null) {
  isStreaming.value = true
  
  try {
    const configStore = useConfigStore()
    
    const response = await fetch(`${apiClient.defaults.baseURL}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        message,
        session_id: sessionId,
        api_key: configStore.apiKey,
        base_url: configStore.baseUrl,
        model: configStore.model
      })
    })
    
    // 流式解析响应
    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let fullResponse = ''
    
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      
      const chunk = decoder.decode(value)
      const lines = chunk.split('\n')
      
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6)
          if (data === '[DONE]') break
          
          try {
            const parsed = JSON.parse(data)
            // 处理会话ID或消息内容
            if (parsed.session_id) {
              currentSessionId.value = parsed.session_id
            } else if (parsed.content) {
              fullResponse += parsed.content
              // 更新UI
            }
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    }
    
    return fullResponse
  } finally {
    isStreaming.value = false
  }
}
```

### 4.3 错误处理
```javascript
// 统一的错误处理模式
try {
  const data = await apiClient.post('/some/endpoint', payload)
  return data
} catch (error) {
  if (error.response) {
    // 服务器响应错误
    console.error('API错误:', error.response.status, error.response.data)
    throw new Error(`服务器错误: ${error.response.data.detail || error.response.status}`)
  } else if (error.request) {
    // 请求发送但无响应
    console.error('网络错误:', error.message)
    throw new Error('网络连接失败，请检查网络设置')
  } else {
    // 请求配置错误
    console.error('请求错误:', error.message)
    throw new Error(`请求失败: ${error.message}`)
  }
}
```
<!-- END_SECTION: api-integration -->

<!-- BEGIN_SECTION: styling-design -->
## 5. 样式设计

### 5.1 动漫风格主题
```css
/* cute.css - 核心样式 */
:root {
  --primary-pink: #ff6b9d;
  --secondary-pink: #ff9ac8;
  --light-pink: #ffebf3;
  --accent-blue: #6bc5ff;
  --text-dark: #333333;
  --text-light: #666666;
  --bg-white: #ffffff;
  --bg-light: #fff9fb;
  --border-radius: 16px;
  --shadow-soft: 0 4px 12px rgba(255, 107, 157, 0.1);
}

/* 字体设置 */
body {
  font-family: 'Comic Sans MS', 'Arial Rounded MT Bold', 'Segoe UI', sans-serif;
  background-color: var(--bg-light);
  color: var(--text-dark);
}

/* 按钮样式 */
.cute-button {
  background: linear-gradient(135deg, var(--primary-pink), var(--secondary-pink));
  color: white;
  border: none;
  border-radius: var(--border-radius);
  padding: 10px 20px;
  font-size: 16px;
  font-weight: bold;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: var(--shadow-soft);
}

.cute-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(255, 107, 157, 0.2);
}

/* 卡片样式 */
.cute-card {
  background: white;
  border-radius: var(--border-radius);
  padding: 20px;
  box-shadow: var(--shadow-soft);
  border: 2px solid var(--light-pink);
  transition: transform 0.2s;
}

.cute-card:hover {
  transform: translateY(-4px);
}

/* 输入框样式 */
.cute-input {
  border: 2px solid var(--light-pink);
  border-radius: 12px;
  padding: 12px 16px;
  font-size: 16px;
  background: white;
  transition: border-color 0.2s;
}

.cute-input:focus {
  outline: none;
  border-color: var(--primary-pink);
}
```

### 5.2 组件样式模式
1. **作用域样式**：组件内使用`<style scoped>`
2. **CSS模块**：复杂组件使用CSS模块化
3. **工具类**：常用样式提取为工具类
4. **主题变量**：使用CSS变量统一设计系统

### 5.3 响应式设计
```css
/* 响应式断点 */
@media (max-width: 768px) {
  .container {
    padding: 10px;
  }
  
  .cute-card {
    padding: 15px;
  }
}

/* 移动端优化 */
.mobile-optimized {
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
```
<!-- END_SECTION: styling-design -->

<!-- BEGIN_SECTION: review-system-frontend -->
## 6. 复习系统前端

### 6.1 ReviewPanel.vue组件结构
```vue
<!-- ReviewPanel.vue简化结构 -->
<template>
  <div class="review-panel">
    <!-- 标题和控制 -->
    <div class="panel-header">
      <h2>知识复习</h2>
      <button @click="refreshReview" :disabled="isLoading">
        {{ isLoading ? '加载中...' : '刷新' }}
      </button>
    </div>
    
    <!-- 错误显示 -->
    <div v-if="error" class="error-message">
      {{ error }}
    </div>
    
    <!-- 内容区域 -->
    <div v-if="hasReviewData" class="review-content">
      <!-- 总体总结 -->
      <div class="summary-section">
        <h3>总体总结</h3>
        <p>{{ aggregatedSummary }}</p>
      </div>
      
      <!-- 分组列表 -->
      <div v-for="group in reviewGroups" :key="group.id" class="review-group">
        <!-- 分组标题（可点击展开） -->
        <div class="group-header" @click="toggleGroupExpansion(group.id)">
          <h4>{{ group.title }}</h4>
          <span class="expansion-icon">
            {{ isGroupExpanded(group.id) ? '▼' : '▶' }}
          </span>
        </div>
        
        <!-- 展开内容 -->
        <div v-if="isGroupExpanded(group.id)" class="group-content">
          <!-- 知识卡片 -->
          <div v-if="group.knowledge_cards" class="knowledge-cards">
            <h5>知识卡片</h5>
            <div v-for="card in group.knowledge_cards" :key="card.id" class="knowledge-card">
              <input type="checkbox" 
                     :checked="card.is_learned" 
                     @change="toggleCardLearned(group.id, card.id)">
              <p>{{ card.content }}</p>
            </div>
          </div>
          
          <!-- 选择题 -->
          <div v-if="group.quiz_questions" class="quiz-questions">
            <h5>选择题</h5>
            <div v-for="question in group.quiz_questions" :key="question.id" class="quiz-question">
              <p class="question-text">{{ question.question }}</p>
              <div class="options">
                <div v-for="(option, index) in question.options" 
                     :key="index"
                     class="option"
                     :class="{ 
                       'selected': selectedAnswers[question.id] === index,
                       'correct': question.user_answer !== undefined && index === question.correct_answer
                     }"
                     @click="selectAnswer(group.id, question.id, index)">
                  {{ option }}
                </div>
              </div>
              <!-- 答案解释 -->
              <div v-if="question.user_answer !== undefined" class="explanation">
                <p>{{ question.is_correct ? '✓ 正确' : '✗ 错误' }}</p>
                <p>{{ question.explanation }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 空状态 -->
    <div v-else class="empty-state">
      <p>暂无复习内容，开始聊天后系统会自动生成复习材料。</p>
    </div>
  </div>
</template>
```

### 6.2 复习交互逻辑
```typescript
// ReviewPanel.vue中的关键方法
const toggleCardLearned = async (groupId: string, cardId: string) => {
  try {
    await reviewStore.toggleCardLearned(groupId, cardId)
  } catch (error) {
    console.error('标记卡片失败:', error)
  }
}

const selectAnswer = async (groupId: string, questionId: string, answerIndex: number) => {
  try {
    await reviewStore.submitQuizAnswer(groupId, questionId, answerIndex)
  } catch (error) {
    console.error('提交答案失败:', error)
  }
}

const getGroupProgress = (group: any): number => {
  const totalItems = (group.knowledge_cards?.length || 0) + 
                    (group.quiz_questions?.length || 0)
  const completedItems = (group.knowledge_cards?.filter(c => c.is_learned).length || 0) +
                        (group.quiz_questions?.filter(q => q.is_completed).length || 0)
  return totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0
}
```

### 6.3 状态同步策略
1. **乐观更新**：用户操作后立即更新本地状态
2. **API同步**：后台发送API请求更新服务器状态
3. **错误回滚**：API失败时恢复本地状态
4. **本地持久化**：关键状态可考虑localStorage缓存
<!-- END_SECTION: review-system-frontend -->

<!-- BEGIN_SECTION: development-workflow -->
## 7. 开发工作流

### 7.1 开发命令
```bash
# 启动开发服务器
npm run dev

# 类型检查
npm run type-check

# 生产构建
npm run build

# 预览生产构建
npm run preview

# Tauri桌面应用开发
npm run tauri dev
npm run tauri build
```

### 7.2 调试工具
1. **Vue DevTools**：组件树和状态检查
2. **浏览器DevTools**：网络请求和性能分析
3. **调试日志**：通过存储中的`DEBUG`标志控制
4. **热重载**：Vite提供的即时更新

### 7.3 最佳实践
1. **组件单一职责**：每个组件专注于一个功能
2. **状态集中管理**：跨组件状态使用Pinia
3. **类型安全**：使用TypeScript和接口定义
4. **错误边界**：组件级别错误处理
5. **性能优化**：合理使用计算属性和侦听器
<!-- END_SECTION: development-workflow -->

## 相关文档
- [复习系统架构](review-system.md)
- [后端架构](backend.md)
- [API文档](../api/overview.md)

---
<!-- END_MODULE: frontend-architecture -->

*文档最后更新：2026-04-15*