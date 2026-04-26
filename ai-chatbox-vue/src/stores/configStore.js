import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useConfigStore = defineStore('config', () => {
  // State - support multiple saved configs
  const savedConfigs = ref([])
  const currentConfigId = ref(null)
  const isConfigVisible = ref(false)

  // Form state for editing
  const configName = ref('')
  const apiKey = ref('')
  const baseUrl = ref('')
  const model = ref('')

  // Getters
  const isConfigured = computed(() => {
    return baseUrl.value.trim() !== '' && model.value.trim() !== ''
  })

  const apiConfig = computed(() => ({
    apiKey: apiKey.value,
    baseUrl: baseUrl.value,
    model: model.value
  }))

  const activeConfig = computed(() => {
    return savedConfigs.value.find(c => c.id === currentConfigId.value) || null
  })

  const hasConfigs = computed(() => savedConfigs.value.length > 0)

  // Actions
  const loadFromLocalStorage = () => {
    try {
      const saved = localStorage.getItem('ai_chatbox_configs')
      if (saved) {
        const data = JSON.parse(saved)
        savedConfigs.value = data.configs || []
        currentConfigId.value = data.currentConfigId || null

        // Load active config to form
        if (currentConfigId.value) {
          loadConfigToForm(currentConfigId.value)
        }
      }
    } catch (err) {
      console.error('Failed to load configs from localStorage:', err)
    }
  }

  const saveToLocalStorage = () => {
    try {
      const data = {
        configs: savedConfigs.value,
        currentConfigId: currentConfigId.value
      }
      localStorage.setItem('ai_chatbox_configs', JSON.stringify(data))
    } catch (err) {
      console.error('Failed to save configs to localStorage:', err)
    }
  }

  const loadConfigToForm = (configId) => {
    const config = savedConfigs.value.find(c => c.id === configId)
    if (config) {
      configName.value = config.name
      apiKey.value = config.apiKey
      baseUrl.value = config.baseUrl
      model.value = config.model
    }
  }

  const saveCurrentConfig = () => {
    if (!isConfigured.value) return false

    const configData = {
      id: currentConfigId.value || Date.now().toString(),
      name: configName.value.trim() || `配置 ${savedConfigs.value.length + 1}`,
      apiKey: apiKey.value,
      baseUrl: baseUrl.value,
      model: model.value,
      updatedAt: new Date().toISOString()
    }

    const existingIndex = savedConfigs.value.findIndex(c => c.id === configData.id)
    if (existingIndex >= 0) {
      savedConfigs.value[existingIndex] = configData
    } else {
      savedConfigs.value.push(configData)
    }

    currentConfigId.value = configData.id
    saveToLocalStorage()
    return true
  }

  const switchConfig = (configId) => {
    const config = savedConfigs.value.find(c => c.id === configId)
    if (config) {
      currentConfigId.value = configId
      loadConfigToForm(configId)
      saveToLocalStorage()
      return true
    }
    return false
  }

  const deleteConfig = (configId) => {
    const index = savedConfigs.value.findIndex(c => c.id === configId)
    if (index >= 0) {
      savedConfigs.value.splice(index, 1)

      // If deleted current config, clear form or switch to another
      if (currentConfigId.value === configId) {
        if (savedConfigs.value.length > 0) {
          switchConfig(savedConfigs.value[0].id)
        } else {
          currentConfigId.value = null
          resetForm()
        }
      }

      saveToLocalStorage()
      return true
    }
    return false
  }

  const createNewConfig = () => {
    currentConfigId.value = null
    resetForm()
  }

  const resetForm = () => {
    configName.value = ''
    apiKey.value = ''
    baseUrl.value = ''
    model.value = ''
  }

  const resetToDefaults = () => {
    resetForm()
  }

  const showConfig = () => {
    isConfigVisible.value = true
  }

  const hideConfig = () => {
    isConfigVisible.value = false
  }

  const toggleConfig = () => {
    isConfigVisible.value = !isConfigVisible.value
  }

  // Initialize: load saved configs
  loadFromLocalStorage()

  return {
    // State
    savedConfigs,
    currentConfigId,
    configName,
    apiKey,
    baseUrl,
    model,
    isConfigVisible,

    // Getters
    isConfigured,
    apiConfig,
    activeConfig,
    hasConfigs,

    // Actions
    loadFromLocalStorage,
    saveToLocalStorage,
    loadConfigToForm,
    saveCurrentConfig,
    switchConfig,
    deleteConfig,
    createNewConfig,
    resetForm,
    resetToDefaults,
    showConfig,
    hideConfig,
    toggleConfig
  }
})
