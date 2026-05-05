import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { login as loginRequest, me as meRequest } from '@/api/auth'
import type { AppMode, AuthUser, UserRoleCode } from '@/types/auth'
import {
  clearStoredAuthState,
  getStoredAccessToken,
  getStoredPreferredMode,
  setStoredAccessToken,
  setStoredPreferredMode,
} from '@/utils/authStorage'

export type { AppMode, AuthUser, UserRoleCode } from '@/types/auth'

export function resolveRouteForMode(mode: AppMode) {
  if (mode === 'training') return { name: 'training-mode' as const }
  if (mode === 'monitor') return { name: 'monitor-dashboard' as const }
  return { name: 'dashboard' as const }
}

function normalizeMode(value: string | null | undefined): AppMode | null {
  if (value === 'training' || value === 'management' || value === 'monitor') {
    return value
  }
  return null
}

function resolveAllowedMode(
  requestedMode: AppMode | null,
  allowedModes: AppMode[],
  fallbackMode: AppMode,
): AppMode {
  if (requestedMode && allowedModes.includes(requestedMode)) {
    return requestedMode
  }
  if (allowedModes.includes(fallbackMode)) {
    return fallbackMode
  }
  return allowedModes[0] || 'training'
}

export const useAuthStore = defineStore('auth', () => {
  const accessToken = ref<string | null>(getStoredAccessToken())
  const currentUser = ref<AuthUser | null>(null)
  const currentMode = ref<AppMode>('training')
  const bootstrapped = ref(false)
  const bootstrappingPromise = ref<Promise<void> | null>(null)

  const isAuthenticated = computed(() => Boolean(accessToken.value && currentUser.value))
  const roleCode = computed<UserRoleCode | null>(() => currentUser.value?.role_code || null)
  const availableModes = computed<AppMode[]>(() => currentUser.value?.available_modes || [])
  const isTrainingMode = computed(() => currentMode.value === 'training')
  const isManagementMode = computed(() => currentMode.value === 'management')
  const isMonitorMode = computed(() => currentMode.value === 'monitor')
  const isAdmin = computed(() => roleCode.value === 'admin')
  const isCoach = computed(() => roleCode.value === 'coach')
  const isTraining = computed(() => roleCode.value === 'training')
  const canManageUsers = computed(() => Boolean(currentUser.value?.can_manage_users))
  const canManageSystem = computed(() => Boolean(currentUser.value?.can_manage_system))
  const homeRoute = computed(() => (isAuthenticated.value ? resolveRouteForMode(currentMode.value) : { name: 'login' as const }))

  function applyUser(user: AuthUser, options: { preferStoredMode: boolean }) {
    currentUser.value = user
    const fallbackMode = normalizeMode(user.mode) || 'training'
    const preferredMode = options.preferStoredMode ? getStoredPreferredMode() : null
    const nextMode = resolveAllowedMode(preferredMode, user.available_modes, fallbackMode)
    currentMode.value = nextMode
    setStoredPreferredMode(nextMode)
  }

  async function fetchMe(options: { preferStoredMode?: boolean } = {}) {
    const user = await meRequest()
    applyUser(user, { preferStoredMode: Boolean(options.preferStoredMode) })
    return user
  }

  async function bootstrap() {
    if (bootstrapped.value) return
    if (bootstrappingPromise.value) {
      await bootstrappingPromise.value
      return
    }

    bootstrappingPromise.value = (async () => {
      if (!accessToken.value) {
        currentUser.value = null
        currentMode.value = 'training'
        bootstrapped.value = true
        return
      }

      try {
        await fetchMe({ preferStoredMode: true })
      } catch {
        clearAuthState()
      } finally {
        bootstrapped.value = true
      }
    })()

    try {
      await bootstrappingPromise.value
    } finally {
      bootstrappingPromise.value = null
    }
  }

  function setMode(mode: AppMode) {
    if (!isAuthenticated.value || !currentUser.value) {
      currentMode.value = 'training'
      return
    }

    const fallbackMode = normalizeMode(currentUser.value.mode) || 'training'
    const nextMode = resolveAllowedMode(mode, availableModes.value, fallbackMode)
    currentMode.value = nextMode
    setStoredPreferredMode(nextMode)
  }

  function syncModeFromRoute(mode: AppMode) {
    setMode(mode)
  }

  function canUseMode(mode: AppMode) {
    return availableModes.value.includes(mode)
  }

  async function login(username: string, password: string) {
    const tokenResponse = await loginRequest(username.trim(), password)
    accessToken.value = tokenResponse.access_token
    setStoredAccessToken(tokenResponse.access_token)
    bootstrapped.value = false

    try {
      const user = await fetchMe({ preferStoredMode: false })
      bootstrapped.value = true
      return user
    } catch (error) {
      clearAuthState()
      throw error
    }
  }

  function clearAuthState() {
    accessToken.value = null
    currentUser.value = null
    currentMode.value = 'training'
    bootstrapped.value = true
    clearStoredAuthState()
  }

  function logout() {
    clearAuthState()
  }

  return {
    accessToken,
    currentUser,
    currentMode,
    bootstrapped,
    isAuthenticated,
    roleCode,
    availableModes,
    isTrainingMode,
    isManagementMode,
    isMonitorMode,
    isAdmin,
    isCoach,
    isTraining,
    canManageUsers,
    canManageSystem,
    homeRoute,
    bootstrap,
    fetchMe,
    login,
    logout,
    setMode,
    syncModeFromRoute,
    canUseMode,
  }
})
