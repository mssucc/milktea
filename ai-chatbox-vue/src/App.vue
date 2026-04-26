<template>
  <div id="app">
    <!-- Main Content -->
    <main class="app-main">
      <!-- Tab Navigation -->
      <div class="tab-navigation">
        <div class="tab-group">
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'chat' }"
            @click="activeTab = 'chat'"
          >
            Chat
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'graph' }"
            @click="activeTab = 'graph'"
          >
            Knowledge
          </button>
          <button
            class="tab-btn"
            :class="{ active: activeTab === 'review' }"
            @click="activeTab = 'review'"
          >
            Review
          </button>
        </div>
        <button @click="showSettings" class="config-btn">
          API 配置
        </button>
      </div>

      <!-- Tab Content -->
      <div class="tab-content">
        <div v-if="activeTab === 'chat'" class="tab-pane">
          <ChatInterface />
        </div>
        <div v-if="activeTab === 'graph'" class="tab-pane">
          <GraphView />
        </div>
        <div v-if="activeTab === 'review'" class="tab-pane">
          <ReviewPanel />
        </div>
      </div>
    </main>

    <!-- Settings Modal -->
    <Settings />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useChatStore } from './stores/chatStore'
import { useGraphStore } from './stores/graphStore'
import { useConfigStore } from './stores/configStore'
import ChatInterface from './components/ChatInterface.vue'
import GraphView from './components/GraphView.vue'
import ReviewPanel from './components/ReviewPanel.vue'
import Settings from './components/Settings.vue'

// Stores
const chatStore = useChatStore()
const graphStore = useGraphStore()
const configStore = useConfigStore()

// Local state
const activeTab = ref('chat')

// Methods
const showSettings = () => {
  configStore.showConfig()
}

// Initialize on mount
onMounted(() => {
  // Load initial data
  chatStore.fetchSessions().catch(console.error)
})
</script>

<style>
#app {
  height: 100vh;
  width: 100vw;
  display: flex;
  flex-direction: column;
  font-family: 'Inter', 'Segoe UI', 'Roboto', 'Helvetica Neue', Arial, sans-serif;
  background: linear-gradient(135deg, #F8F5F2 0%, #F0F0F0 100%);
  color: #333;
  transition: background 0.3s ease, color 0.3s ease;
  overflow: hidden;
}

#app[data-theme="dark"] {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: #f0f0f0;
}


.app-main {
  flex: 1;
  padding: 15px 20px;
  width: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  height: calc(100vh - 180px); /* Adjust based on header/footer height */
}

@media (max-width: 1200px) {
  .dashboard-grid {
    grid-template-columns: repeat(2, 1fr);
    grid-template-rows: auto auto;
  }

  .chat-column {
    grid-column: span 2;
  }
}

@media (max-width: 768px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
    height: auto;
  }

  .chat-column {
    grid-column: span 1;
  }
}

.dashboard-column {
  background: rgba(255, 255, 255, 0.9);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 10px 30px rgba(156, 137, 184, 0.1);
  display: flex;
  flex-direction: column;
  border: 1px solid #E0E0E0;
}

#app[data-theme="dark"] .dashboard-column {
  background: rgba(40, 40, 60, 0.9);
  border: 2px solid #4a4a6d;
}

.column-header {
  background: rgba(156, 137, 184, 0.1);
  padding: 15px 20px;
  border-bottom: 1px solid #E0E0E0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

#app[data-theme="dark"] .column-header {
  background: rgba(70, 70, 100, 0.2);
  border-bottom: 1px solid #4a4a6d;
}

.column-header h2 {
  margin: 0;
  color: #9C89B8;
  font-size: 1.4rem;
  font-weight: 600;
}

#app[data-theme="dark"] .column-header h2 {
  color: #B8D0EB;
}

.column-actions {
  display: flex;
  gap: 10px;
}

.action-btn {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #9C89B8;
  color: #9C89B8;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  cursor: pointer;
  font-family: inherit;
  font-size: 1.2rem;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn:hover {
  background: rgba(156, 137, 184, 0.1);
  transform: translateY(-2px);
}

.column-content {
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* Column-specific styles */
.chat-column .column-content {
  display: flex;
}

.graph-column {
  border-color: #87ceeb;
}

.graph-column .column-header {
  background: rgba(135, 206, 235, 0.2);
  border-bottom: 2px dashed #87ceeb;
}

.graph-column .column-header h2 {
  color: #1e90ff;
}

.graph-column .action-btn {
  border-color: #87ceeb;
  color: #1e90ff;
}

.review-column {
  border-color: #98fb98;
}

.review-column .column-header {
  background: rgba(152, 251, 152, 0.2);
  border-bottom: 2px dashed #98fb98;
}

.review-column .column-header h2 {
  color: #32cd32;
}

.review-column .action-btn {
  border-color: #98fb98;
  color: #32cd32;
}

.app-footer {
  background: rgba(255, 182, 193, 0.3);
  border-top: 3px dashed #ffb6c1;
  padding: 10px 30px;
  font-size: 0.9rem;
}

#app[data-theme="dark"] .app-footer {
  background: rgba(70, 70, 100, 0.3);
  border-top: 3px dashed #4a4a6d;
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding: 0 20px;
  color: #666;
}

#app[data-theme="dark"] .footer-content {
  color: #aaa;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 15px;
}

.footer-right span {
  color: #9C89B8;
}

#app[data-theme="dark"] .footer-right span {
  color: #B8D0EB;
}

/* Tab Navigation Styles */
.tab-navigation {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 15px;
  border-bottom: 1px solid #E0E0E0;
  padding-bottom: 10px;
  flex-shrink: 0;
}

.tab-group {
  display: flex;
  gap: 10px;
}

.config-btn {
  background: rgba(255, 255, 255, 0.9);
  border: 2px solid #9C89B8;
  color: #9C89B8;
  padding: 8px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-family: inherit;
  font-size: 0.9rem;
  font-weight: 500;
  transition: all 0.3s ease;
}

.config-btn:hover {
  background: rgba(156, 137, 184, 0.1);
  transform: translateY(-2px);
}

.tab-btn {
  background: transparent;
  border: none;
  padding: 10px 20px;
  border-radius: 8px;
  cursor: pointer;
  font-family: inherit;
  font-size: 1rem;
  font-weight: 500;
  color: #666;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 8px;
}

.tab-btn:hover {
  background: rgba(156, 137, 184, 0.1);
  color: #9C89B8;
}

.tab-btn.active {
  background: rgba(156, 137, 184, 0.15);
  color: #9C89B8;
  border-bottom: 2px solid #9C89B8;
}

.tab-content {
  flex: 1;
  background: white;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
}

.tab-pane {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* Dark mode tab styles */
#app[data-theme="dark"] .tab-navigation {
  border-bottom: 1px solid #4a4a6d;
}

#app[data-theme="dark"] .tab-btn {
  color: #aaa;
}

#app[data-theme="dark"] .tab-btn:hover {
  background: rgba(184, 208, 235, 0.1);
  color: #B8D0EB;
}

#app[data-theme="dark"] .tab-btn.active {
  background: rgba(184, 208, 235, 0.15);
  color: #B8D0EB;
  border-bottom: 2px solid #B8D0EB;
}

#app[data-theme="dark"] .tab-content {
  background: rgba(40, 40, 60, 0.9);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

#app[data-theme="dark"] .config-btn {
  background: rgba(40, 40, 60, 0.9);
  border-color: #4a4a6d;
  color: #B8D0EB;
}

#app[data-theme="dark"] .config-btn:hover {
  background: rgba(184, 208, 235, 0.1);
}
</style>