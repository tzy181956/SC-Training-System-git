import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export type AppMode = 'training' | 'management' | 'monitor'

const MODE_STORAGE_KEY = 'training-platform-mode'

export function resolveRouteForMode(mode: AppMode) {
  if (mode === 'training') return { name: 'training-mode' as const }
  if (mode === 'monitor') return { name: 'monitor-dashboard' as const }
  return { name: 'dashboard' as const }
}

function resolveInitialMode(): AppMode {
  const savedMode = localStorage.getItem(MODE_STORAGE_KEY)
  if (savedMode === 'management' || savedMode === 'monitor') {
    return savedMode
  }
  return 'training'
}

export const useAuthStore = defineStore('auth', () => {
  const currentMode = ref<AppMode>(resolveInitialMode())

  const isTrainingMode = computed(() => currentMode.value === 'training')
  const isManagementMode = computed(() => currentMode.value === 'management')
  const isMonitorMode = computed(() => currentMode.value === 'monitor')
  const homeRoute = computed(() => resolveRouteForMode(currentMode.value))

  function setMode(mode: AppMode) {
    currentMode.value = mode
    localStorage.setItem(MODE_STORAGE_KEY, mode)
  }

  function toggleMode() {
    if (currentMode.value === 'monitor') {
      setMode('training')
      return
    }
    setMode(isTrainingMode.value ? 'management' : 'training')
  }

  return {
    currentMode,
    isTrainingMode,
    isManagementMode,
    isMonitorMode,
    homeRoute,
    setMode,
    toggleMode,
  }
})
