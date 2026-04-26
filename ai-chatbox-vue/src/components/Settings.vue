<template>
  <div class="settings-overlay" v-if="isVisible" @click.self="hide">
    <div class="settings-panel anime-card">
      <div class="settings-header">
        <h2 class="anime-title">API 配置</h2>
        <button class="close-btn" @click="hide">✕</button>
      </div>

      <div class="settings-content">
        <!-- Provider Selection - Simplified -->
        <div class="settings-section">
          <h3 class="anime-subtitle">API 配置</h3>
          <p class="section-hint">配置您的 AI 服务提供商信息</p>
        </div>

        <!-- Configuration Form -->
        <div class="settings-section">
          <h3 class="anime-subtitle">配置详情</h3>
          <form @submit.prevent="save">
            <div class="form-group">
              <label for="configName" class="anime-label">配置名称</label>
              <input
                id="configName"
                type="text"
                v-model="configName"
                placeholder="例如：DeepSeek 官方、本地 Ollama"
                class="anime-input"
              />
            </div>

            <div class="form-group">
              <label for="apiKey" class="anime-label">
                API 密钥
                <span class="hint">（可选）</span>
              </label>
              <input
                id="apiKey"
                type="password"
                v-model="apiKey"
                placeholder="输入您的 API 密钥"
                class="anime-input"
              />
            </div>

            <div class="form-group">
              <label for="baseUrl" class="anime-label">API 基础 URL</label>
              <input
                id="baseUrl"
                type="text"
                v-model="baseUrl"
                placeholder="https://api.openai.com/v1"
                class="anime-input"
              />
              <small class="hint">必须是 OpenAI 兼容的 API 端点</small>
            </div>

            <div class="form-group">
              <label for="model" class="anime-label">模型名称</label>
              <input
                id="model"
                type="text"
                v-model="model"
                placeholder="例如：deepseek-chat, gpt-3.5-turbo, llama2"
                class="anime-input"
              />
              <small class="hint">输入您的模型名称，如 deepseek-chat、gpt-4 等</small>
            </div>

            <div class="form-actions">
              <button type="button" class="anime-btn secondary" @click="reset">
                重置
              </button>
              <button
                type="button"
                class="anime-btn test"
                :disabled="!canTest || isTesting"
                @click="testConfig"
              >
                <span v-if="isTesting">测试中...</span>
                <span v-else>测试连接</span>
              </button>
              <button type="submit" class="anime-btn primary" :disabled="!isConfigured">
                保存配置
              </button>
            </div>

            <!-- Test Result -->
            <div v-if="testResult" class="test-result" :class="{ success: testResult.success, error: !testResult.success }">
              {{ testResult.message }}
            </div>
          </form>
        </div>

        <!-- Saved Configs List -->
        <div class="settings-section" v-if="hasConfigs">
          <h3 class="anime-subtitle">已保存的配置</h3>
          <div class="config-list">
            <div
              v-for="config in savedConfigs"
              :key="config.id"
              :class="['config-item', { active: config.id === currentConfigId }]"
            >
              <div class="config-info" @click="switchConfig(config.id)">
                <div class="config-name">{{ config.name }}</div>
                <div class="config-details">{{ config.model }} @ {{ config.baseUrl }}</div>
              </div>
              <button class="delete-config-btn" @click="deleteConfig(config.id)" title="删除">
                ×
              </button>
            </div>
          </div>
          <button class="anime-btn secondary new-config-btn" @click="createNewConfig">
            + 新建配置
          </button>
        </div>

        <!-- Status -->
        <div class="settings-section status-section" :class="{ configured: isConfigured }">
          <h3 class="anime-subtitle">状态</h3>
          <div class="status-indicator">
            <span class="status-icon">{{ isConfigured ? '●' : '○' }}</span>
            <span class="status-text">
              {{ isConfigured ? '配置已完成，可以开始聊天！' : '请完成配置以启用聊天功能' }}
            </span>
          </div>
          <div v-if="isConfigured" class="config-summary">
            <p><strong>模型：</strong> {{ model }}</p>
            <p><strong>端点：</strong> {{ baseUrl }}</p>
            <p v-if="apiKey"><strong>API Key：</strong> 已配置</p>
          </div>
        </div>
      </div>

      <div class="settings-footer">
        <p class="hint">配置保存在本地存储</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useConfigStore } from '@/stores/configStore'
import { storeToRefs } from 'pinia'
import { testApiConfig } from '@/api'

const configStore = useConfigStore()

const {
  savedConfigs,
  currentConfigId,
  configName,
  apiKey,
  baseUrl,
  model,
  isConfigVisible: isVisible,
  isConfigured,
  hasConfigs
} = storeToRefs(configStore)

const {
  saveCurrentConfig,
  hideConfig: hide,
  resetToDefaults: reset,
  switchConfig,
  deleteConfig,
  createNewConfig
} = configStore

// Test state
const isTesting = ref(false)
const testResult = ref(null)

// Can test if baseUrl and model are provided
const canTest = computed(() => {
  return baseUrl.value?.trim() !== '' && model.value?.trim() !== ''
})

const testConfig = async () => {
  if (!canTest.value || isTesting.value) return

  isTesting.value = true
  testResult.value = null

  try {
    const result = await testApiConfig({
      api_key: apiKey.value,
      base_url: baseUrl.value,
      model: model.value
    })
    testResult.value = result
  } catch (err) {
    testResult.value = {
      success: false,
      message: err.message || '测试失败'
    }
  } finally {
    isTesting.value = false
  }
}

const save = () => {
  saveCurrentConfig()
  hide()
}
</script>

<style scoped>
.settings-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  animation: fadeIn 0.3s ease;
}

.settings-panel {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  border-radius: 16px;
  width: 90%;
  max-width: 700px;
  max-height: 90vh;
  overflow-y: auto;
  border: 1px solid #dee2e6;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  animation: slideUp 0.4s ease;
}

.settings-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 25px;
  border-bottom: 1px solid #dee2e6;
  background: #ffffff;
  border-radius: 16px 16px 0 0;
}

.anime-title {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: #495057;
  margin: 0;
  font-size: 1.6rem;
  font-weight: 600;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  color: #6c757d;
  cursor: pointer;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.3s;
}

.close-btn:hover {
  background-color: rgba(108, 117, 125, 0.1);
  transform: scale(1.1);
  color: #495057;
}

.settings-content {
  padding: 25px;
}

.settings-section {
  margin-bottom: 24px;
  padding: 20px;
  background: #ffffff;
  border-radius: 12px;
  border: 1px solid #e9ecef;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.02);
}

.anime-subtitle {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color: #495057;
  margin-top: 0;
  margin-bottom: 15px;
  font-size: 1.2rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-hint {
  color: #888;
  font-size: 0.95rem;
  margin-top: -10px;
  margin-bottom: 10px;
}

.form-group {
  margin-bottom: 20px;
}

.anime-label {
  display: block;
  margin-bottom: 8px;
  color: #495057;
  font-weight: 600;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.hint {
  font-size: 0.85rem;
  color: #888;
  margin-left: 5px;
}

.anime-input,
.anime-select {
  width: 100%;
  padding: 12px 15px;
  border: 1px solid #ced4da;
  border-radius: 8px;
  font-size: 1rem;
  background: white;
  transition: all 0.2s;
  box-sizing: border-box;
}

.anime-input:focus,
.anime-select:focus {
  outline: none;
  border-color: #495057;
  box-shadow: 0 0 0 3px rgba(73, 80, 87, 0.1);
}

.anime-input:disabled {
  background: #f5f5f5;
  cursor: not-allowed;
}

.mt-1 {
  margin-top: 8px;
}

.form-actions {
  display: flex;
  gap: 10px;
  margin-top: 25px;
}

.anime-btn.test {
  background: #17a2b8;
  color: white;
  flex: 1;
}

.anime-btn.test:hover:not(:disabled) {
  background: #138496;
  transform: translateY(-2px);
}

.anime-btn.test:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.test-result {
  margin-top: 15px;
  padding: 12px 15px;
  border-radius: 8px;
  font-size: 0.95rem;
  text-align: center;
}

.test-result.success {
  background: rgba(40, 167, 69, 0.1);
  border: 1px solid #28a745;
  color: #155724;
}

.test-result.error {
  background: rgba(220, 53, 69, 0.1);
  border: 1px solid #dc3545;
  color: #721c24;
}

.anime-btn {
  flex: 1;
  padding: 12px 20px;
  border: none;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s;
  font-family: 'Comic Sans MS', sans-serif;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.anime-btn.primary {
  background: #495057;
  color: white;
}

.anime-btn.primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(73, 80, 87, 0.3);
  background: #343a40;
}

.anime-btn.primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.anime-btn.secondary {
  background: white;
  border: 1px solid #ced4da;
  color: #6c757d;
}

.anime-btn.secondary:hover {
  background: #f8f9fa;
  border-color: #adb5bd;
  color: #495057;
}

.status-section {
  text-align: center;
}

.status-section.configured {
  background: rgba(40, 167, 69, 0.08);
  border-color: #28a745;
}

.status-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 15px;
  margin-bottom: 15px;
}

.status-icon {
  font-size: 2rem;
}

.status-text {
  font-size: 1.1rem;
  font-weight: bold;
  color: #333;
}

.config-summary {
  text-align: left;
  background: rgba(255, 255, 255, 0.7);
  padding: 15px;
  border-radius: 10px;
  margin-top: 15px;
}

.config-summary p {
  margin: 8px 0;
  color: #555;
}

.settings-footer {
  padding: 15px 25px;
  text-align: center;
  border-top: 1px solid #e9ecef;
  background: #f8f9fa;
  border-radius: 0 0 16px 16px;
}

.config-list {
  margin-bottom: 15px;
}

.config-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 15px;
  margin-bottom: 8px;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.config-item:hover {
  background: #e9ecef;
  border-color: #adb5bd;
}

.config-item.active {
  background: #e7f3ff;
  border-color: #0066cc;
}

.config-info {
  flex: 1;
  min-width: 0;
}

.config-name {
  font-weight: 600;
  color: #495057;
  margin-bottom: 2px;
}

.config-item.active .config-name {
  color: #0066cc;
}

.config-details {
  font-size: 0.85rem;
  color: #6c757d;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.delete-config-btn {
  background: none;
  border: none;
  color: #dc3545;
  font-size: 1.5rem;
  cursor: pointer;
  padding: 0 8px;
  opacity: 0.6;
  transition: opacity 0.2s;
}

.delete-config-btn:hover {
  opacity: 1;
}

.new-config-btn {
  width: 100%;
  margin-top: 10px;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(50px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 768px) {
  .settings-panel {
    width: 95%;
  }
}
</style>