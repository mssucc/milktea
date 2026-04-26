# 复习系统架构设计

<!-- BEGIN_MODULE: review-system -->
<!-- BEGIN_TOC -->
## 目录
1. [设计概览](#design-overview)
2. [数据结构](#data-structures)
3. [聚合算法](#aggregation-algorithm)
4. [生成流程](#generation-process)
5. [API接口](#api-interfaces)
6. [前端交互](#frontend-interaction)
7. [后台任务](#background-tasks)
8. [配置优化](#configuration-optimization)
<!-- END_TOC -->

<!-- BEGIN_SECTION: design-overview -->
## 1. 设计概览

### 1.1 设计目标
- **知识深度优先**：重点处理高频主题，提供详细内容覆盖
- **时效性辅助**：近期会话提供额外上下文权重
- **单提示词生成**：一次LLM调用生成所有结构化数据（知识卡片+选择题）
- **跨会话聚合**：智能分组多个对话中的相似主题
- **响应式交互**：支持知识卡片标记已学、选择题答题判题

### 1.2 核心原则
1. **简化设计**：只保留选择题和知识卡片，移除复杂进度追踪
2. **按知识点分组**：宏观知识点（如"Linux相关命令学习"）而非单个命令
3. **混合展示**：每个分组内知识卡片在前，选择题在后
4. **后台生成**：定期扫描和聚合，避免实时生成延迟
<!-- END_SECTION: design-overview -->

<!-- BEGIN_SECTION: data-structures -->
## 2. 数据结构

### 2.1 核心JSON结构
```json
{
  "session_id": "session_123",
  "aggregated_summary": "对话总体总结",
  "review_groups": [
    {
      "id": "linux_commands",
      "title": "Linux命令",
      "description": "关于Linux系统命令的学习",
      "knowledge_cards": [
        {
          "id": "ls_command",
          "content": "ls命令列出目录内容，常用选项包括-l（详细信息）、-a（显示隐藏文件）、-h（人类可读大小）",
          "is_learned": false
        }
      ],
      "quiz_questions": [
        {
          "id": "ls_quiz_1",
          "question": "Ubuntu的ls命令的主要功能是什么？",
          "options": ["列出目录内容", "创建新文件", "删除文件", "修改文件权限"],
          "correct_answer": 0,
          "explanation": "ls命令用于列出当前目录下的文件和子目录",
          "difficulty": "easy",
          "is_completed": false
        }
      ]
    }
  ],
  "total_groups": 1,
  "total_knowledge_cards": 1,
  "total_quiz_questions": 1,
  "next_review_date": "2026-04-15T10:00:00Z",
  "generated_at": "2026-04-15T10:00:00Z"
}
```

### 2.2 数据库模型 (ReviewData)
```python
class ReviewData(Base):
    __tablename__ = "review_data"
    
    # 核心数据字段
    session_id = Column(String, ForeignKey("sessions.id"), unique=True, index=True)
    review_groups = Column(JSON)  # 结构化分组数据
    aggregated_summary = Column(Text)  # 总体总结
    
    # 状态追踪
    generation_status = Column(String, default="pending")
    generated_at = Column(DateTime)
    expires_at = Column(DateTime)  # 24小时缓存有效期
    
    # 用户学习状态
    learned_cards = Column(JSON, default=[])  # 已学习的知识卡片ID
    completed_quizzes = Column(JSON, default=[])  # 已完成的题目ID
    last_reviewed_at = Column(DateTime)
    review_count = Column(Integer, default=0)
```
<!-- END_SECTION: data-structures -->

<!-- BEGIN_SECTION: aggregation-algorithm -->
## 3. 聚合算法

### 3.1 算法策略：知识深度优先 + 时效性辅助

#### 知识深度优先
1. **高频主题优先**：从Neo4j获取提及次数最多的实体节点（Top 20）
2. **会话关联分析**：获取高频节点关联的会话ID
3. **内容聚合**：按知识主题分组，高频主题提供更详细内容

#### 时效性辅助
1. **近期会话加权**：最近3天的会话获得额外权重
2. **时间衰减**：按时间指数衰减权重，平衡新旧内容

### 3.2 动态调整策略
根据用户交流频次动态调整处理范围：

| 交流频次 | 处理策略 | 会话限制 |
|----------|----------|----------|
| **高** (每天>10条消息) | 只处理Top 10高频节点 | 15个会话 |
| **中** (每天3-10条消息) | 处理Top 15高频节点 | 20个会话 |
| **低** (每天<3条消息) | 处理所有新消息会话 | 全部会话 |

### 3.3 算法实现 (crud.py)
```python
def aggregate_review_data(sessions_data, strategy="knowledge_depth_first"):
    """
    聚合多个会话的复习数据
    
    参数:
    - sessions_data: 多个会话的原始review数据
    - strategy: 聚合策略 ("knowledge_depth_first" 或 "recency_weighted")
    
    返回:
    - IntegratedReviewResponse格式的聚合数据
    """
    # 1. 知识主题识别和聚类
    # 2. 按策略权重计算
    # 3. 生成结构化分组
    # 4. 创建知识卡片和选择题
```
<!-- END_SECTION: aggregation-algorithm -->

<!-- BEGIN_SECTION: generation-process -->
## 4. 生成流程

### 4.1 单提示词生成
使用单个LLM prompt生成完整结构化数据：

```
你是一个专业的学习助手，请分析以下对话内容，生成结构化的复习材料。

对话内容: {conversation_text}

请按照以下格式生成：
1. 总体总结 (aggregated_summary)
2. 按知识主题分组 (review_groups)
   - 每个组包含: 标题(title), 描述(description)
   - 每个组包含知识卡片 (knowledge_cards): 简洁的知识点总结
   - 每个组包含选择题 (quiz_questions): 针对该知识点的选择题

要求:
- 选择题专注于科技常识，如Ubuntu的ls命令功能
- 知识卡片是会话核心内容的提炼
- 按宏观知识点分组，如"Linux相关命令学习"作为一个组
- 输出必须为有效的JSON格式
```

### 4.2 生成模块 (structured_review_generator.py)
```python
class StructuredReviewGenerator:
    def generate_structured_review(self, conversation_text, api_config=None):
        """使用单个prompt生成结构化复习数据"""
        prompt = self._build_prompt(conversation_text)
        llm_response = self._call_llm(prompt, api_config)
        return self._parse_response(llm_response)
```
<!-- END_SECTION: generation-process -->

<!-- BEGIN_SECTION: api-interfaces -->
## 5. API接口

### 5.1 核心端点

| 端点 | 方法 | 功能 | 响应码 |
|------|------|------|--------|
| `/api/review/integrated/overview` | POST | 获取集成复习数据 | 200: 成功, 202: 生成中 |
| `/api/review/integrated/sessions` | GET | 获取有复习数据的会话列表 | 200: 成功 |
| `/api/review/{session_id}/submit-quiz-answer` | POST | 提交选择题答案 | 200: 成功 |
| `/api/review/{session_id}/mark-card-learned` | POST | 标记知识卡片为已学 | 200: 成功 |

### 5.2 请求/响应模型
```python
class IntegratedReviewRequest(BaseModel):
    """集成复习请求模型"""
    session_ids: Optional[List[str]] = None
    limit: int = Field(default=10, ge=1, le=50)

class IntegratedReviewResponse(BaseModel):
    """集成复习响应模型"""
    aggregated_summary: str
    review_groups: List[ReviewGroup]
    total_groups: int
    total_knowledge_cards: int
    total_quiz_questions: int
    next_review_date: Optional[str]
    generated_at: str
```
<!-- END_SECTION: api-interfaces -->

<!-- BEGIN_SECTION: frontend-interaction -->
## 6. 前端交互

### 6.1 ReviewPanel.vue组件
**核心状态管理**：
```typescript
// 展开的分组状态
const expandedGroups = ref<string[]>([])

// 切换分组展开
const toggleGroupExpansion = (groupId: string) => {
  const index = expandedGroups.value.indexOf(groupId)
  if (index > -1) {
    expandedGroups.value.splice(index, 1)
  } else {
    expandedGroups.value.push(groupId)
  }
}

// 标记知识卡片为已学
const toggleCardLearned = (groupId: string, cardId: string) => {
  // 调用API并更新本地状态
}

// 选择答案
const selectAnswer = (groupId: string, questionId: string, answerIndex: number) => {
  // 提交答案并显示结果
}
```

### 6.2 显示逻辑
1. **分组列表**：显示所有知识主题分组
2. **展开/收起**：点击分组标题展开显示内容
3. **知识卡片**：显示卡片内容，点击checkbox标记已学
4. **选择题**：显示题目和选项，选择后显示正确答案和解释

### 6.3 进度计算
```typescript
// 计算分组进度（知识卡片+选择题）
const getGroupProgress = (group: any): number => {
  const totalItems = (group.knowledge_cards?.length || 0) + 
                    (group.quiz_questions?.length || 0)
  const completedItems = (group.knowledge_cards?.filter(c => c.is_learned).length || 0) +
                        (group.quiz_questions?.filter(q => q.is_completed).length || 0)
  return totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0
}
```
<!-- END_SECTION: frontend-interaction -->

<!-- BEGIN_SECTION: background-tasks -->
## 7. 后台任务

### 7.1 调度策略
- **频率**：每12小时（08:00和20:00）
- **扫描范围**：基于高频节点和动态调整策略
- **超时设置**：每个生成任务5分钟
- **重试机制**：指数退避（1min, 5min, 30min, 24h）

### 7.2 任务类型
1. **定时扫描任务**：自动检测需要生成的会话
2. **即时触发任务**：用户访问未缓存数据时触发
3. **手动重生成任务**：用户点击刷新按钮触发

### 7.3 任务执行 (review_generation.py)
```python
async def generate_integrated_review_background(limit=10, days=7, force_refresh=False):
    """后台生成集成复习数据"""
    # 1. 选择会话
    session_ids = select_sessions_for_review_generation(limit, days)
    
    # 2. 获取会话内容
    sessions_data = fetch_sessions_content(session_ids)
    
    # 3. 生成结构化复习
    review_data = structured_review_generator.generate(sessions_data)
    
    # 4. 存储到数据库
    save_integrated_review(review_data)
```
<!-- END_SECTION: background-tasks -->

<!-- BEGIN_SECTION: configuration-optimization -->
## 8. 配置优化

### 8.1 环境配置
```env
# 复习系统配置
REVIEW_CACHE_TTL_HOURS=24
REVIEW_GENERATION_TIMEOUT=300
REVIEW_SCAN_FREQUENCY_HOURS=12
REVIEW_MAX_SESSIONS=20
```

### 8.2 性能优化
1. **缓存策略**：24小时缓存有效期
2. **增量更新**：只处理有新消息的会话
3. **并行处理**：多个会话可以并行生成
4. **结果复用**：相同内容的会话复用已有结果

### 8.3 监控指标
- 生成成功率
- 平均生成时间
- 缓存命中率
- 用户交互率（卡片标记、答题完成）
<!-- END_SECTION: configuration-optimization -->

## 相关文档
- [复习API文档](../api/review-api.md)
- [数据模型文档](../database/models.md)
- [前端架构文档](frontend.md)

---
<!-- END_MODULE: review-system -->

*文档最后更新：2026-04-15*