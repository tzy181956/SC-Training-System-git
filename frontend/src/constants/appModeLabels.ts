import type { AppMode } from '@/stores/auth'

export const APP_MODE_DISPLAY_LABELS: Record<AppMode, string> = {
  training: '训练模式',
  management: '管理模式',
  monitor: '实时模式',
}

const LEGACY_MODE_NAME_ALIASES: Record<string, string> = {
  训练端: '训练模式',
  训练模式: '训练模式',
  管理端: '管理模式',
  管理模式: '管理模式',
  监控端: '实时模式',
  实时模式: '实时模式',
}

const ACTOR_FILTER_INPUT_ALIASES: Record<string, string> = {
  训练模式: '训练端',
  管理模式: '管理端',
  实时模式: '监控端',
}

export function getAppModeDisplayLabel(mode: AppMode) {
  return APP_MODE_DISPLAY_LABELS[mode]
}

export function normalizeModeAliasForDisplay(value?: string | null) {
  if (!value) return value || ''
  const trimmed = value.trim()
  return LEGACY_MODE_NAME_ALIASES[trimmed] || trimmed
}

export function normalizeActorNameFilter(value?: string | null) {
  if (!value) return ''
  const trimmed = value.trim()
  return ACTOR_FILTER_INPUT_ALIASES[trimmed] || trimmed
}
