import type { AppMode } from '@/types/auth'

const ACCESS_TOKEN_STORAGE_KEY = 'training-platform-access-token'
const MODE_STORAGE_KEY = 'training-platform-mode'

function readStorageValue(key: string): string | null {
  const value = localStorage.getItem(key)
  if (!value) return null
  const normalized = value.trim()
  return normalized || null
}

export function getStoredAccessToken(): string | null {
  return readStorageValue(ACCESS_TOKEN_STORAGE_KEY)
}

export function setStoredAccessToken(token: string) {
  localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token)
}

export function clearStoredAccessToken() {
  localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY)
}

export function getStoredPreferredMode(): AppMode | null {
  const value = readStorageValue(MODE_STORAGE_KEY)
  if (value === 'training' || value === 'management' || value === 'monitor') {
    return value
  }
  return null
}

export function setStoredPreferredMode(mode: AppMode) {
  localStorage.setItem(MODE_STORAGE_KEY, mode)
}

export function clearStoredPreferredMode() {
  localStorage.removeItem(MODE_STORAGE_KEY)
}

export function clearStoredAuthState() {
  clearStoredAccessToken()
  clearStoredPreferredMode()
}
