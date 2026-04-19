import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

type ModeType = 'training' | 'management'

const MODE_STORAGE_KEY = 'training-platform-mode'

function resolveInitialMode(): ModeType {
  const savedMode = localStorage.getItem(MODE_STORAGE_KEY)
  return savedMode === 'management' ? 'management' : 'training'
}

export const useAuthStore = defineStore('auth', () => {
  const currentMode = ref<ModeType>(resolveInitialMode())

  const isTrainingMode = computed(() => currentMode.value === 'training')
  const isManagementMode = computed(() => currentMode.value === 'management')
  const homeRoute = computed(() => (isTrainingMode.value ? { name: 'training-mode' } : { name: 'dashboard' }))

  function setMode(mode: ModeType) {
    currentMode.value = mode
    localStorage.setItem(MODE_STORAGE_KEY, mode)
  }

  function toggleMode() {
    setMode(isTrainingMode.value ? 'management' : 'training')
  }

  return {
    currentMode,
    isTrainingMode,
    isManagementMode,
    homeRoute,
    setMode,
    toggleMode,
  }
})
