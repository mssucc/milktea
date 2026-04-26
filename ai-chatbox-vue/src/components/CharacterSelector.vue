<template>
  <div class="character-selector">
    <div class="selector-header">
      <span class="current-character">
        {{ currentCharacter.displayName }}
      </span>
      <button class="toggle-btn" @click="showDropdown = !showDropdown">
        {{ showDropdown ? '▲' : '▼' }}
      </button>
    </div>

    <div v-if="showDropdown" class="character-dropdown">
      <div
        v-for="char in availableCharacters"
        :key="char.id"
        :class="['character-option', { active: char.id === currentCharacterId }]"
        @click="selectCharacter(char.id)"
      >
        <img
          v-if="char.avatar"
          :src="char.avatar"
          :alt="char.displayName"
          class="option-avatar"
        />
        <div class="character-info">
          <div class="character-name">{{ char.displayName }}</div>
          <div class="character-desc">{{ char.description }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useChatStore } from '@/stores/chatStore'
import { getAvailableCharacters } from '@/config/characters'

const chatStore = useChatStore()
const showDropdown = ref(false)

const currentCharacterId = computed(() => chatStore.currentCharacterId)
const currentCharacter = computed(() => chatStore.currentCharacter)
const availableCharacters = getAvailableCharacters()

const selectCharacter = (characterId) => {
  chatStore.setCharacter(characterId)
  showDropdown.value = false
}
</script>

<style scoped>
.character-selector {
  position: relative;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
}

.selector-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 15px;
  cursor: pointer;
  background: #f8f9fa;
  transition: background 0.2s;
}

.selector-header:hover {
  background: #e9ecef;
}

.current-character {
  font-weight: 500;
  color: #495057;
}

.toggle-btn {
  background: none;
  border: none;
  color: #6c757d;
  cursor: pointer;
  font-size: 0.8rem;
  padding: 4px 8px;
}

.character-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 1px solid #e9ecef;
  border-top: none;
  border-radius: 0 0 8px 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 100;
  max-height: 200px;
  overflow-y: auto;
}

.character-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 15px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  transition: all 0.2s;
}

.character-option:last-child {
  border-bottom: none;
}

.character-option:hover {
  background: #f8f9fa;
}

.character-option.active {
  background: #e7f3ff;
}

.character-name {
  font-weight: 600;
  color: #495057;
  margin-bottom: 2px;
}

.character-option.active .character-name {
  color: #0066cc;
}

.character-desc {
  font-size: 0.85rem;
  color: #6c757d;
}

.option-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  object-fit: cover;
  flex-shrink: 0;
  border: 2px solid rgba(201, 160, 220, 0.3);
}
</style>
