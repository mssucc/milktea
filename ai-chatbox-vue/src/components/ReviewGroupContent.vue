<template>
  <div>
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
                @change="$emit('toggle-card', group.id, card.id, !card.is_learned)"
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
                     @click="$emit('select-answer', group.id, question.id, index)">
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

    <!-- Group statistics (conversation-based reviews only) -->
    <div v-if="group.session_count && group.session_count > 0" class="group-statistics">
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
</template>

<script setup lang="ts">
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
  frequency: number
  session_count: number
}

defineProps<{
  group: ReviewGroup
}>()

defineEmits<{
  'toggle-card': [groupId: string, cardId: string, isLearned: boolean]
  'select-answer': [groupId: string, questionId: string, answerIndex: number]
}>()
</script>

<style scoped>
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

/* Knowledge cards */
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

/* Checkbox */
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

/* Quiz questions */
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

/* Options */
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

/* Question meta */
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
</style>
