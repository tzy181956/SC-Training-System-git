export const SESSION_RPE_VALUES = Array.from({ length: 11 }, (_, index) => index)

export type SessionRpeMeta = {
  label: string
  help: string
}

export const SESSION_RPE_LABELS: Record<number, SessionRpeMeta> = {
  0: { label: '一点也不费力', help: '几乎没有训练负荷' },
  1: { label: '很轻松', help: '非常轻松，几乎无压力' },
  2: { label: '轻松', help: '轻松完成，仍有大量余力' },
  3: { label: '适中', help: '有训练感，但整体可控' },
  4: { label: '有点困难', help: '开始感觉吃力，但仍较稳定' },
  5: { label: '困难', help: '明显费力，需要集中注意力' },
  6: { label: '比较困难', help: '持续吃力，完成质量需要关注' },
  7: { label: '很困难', help: '强度较高，明显接近高负荷' },
  8: { label: '非常困难', help: '非常吃力，需要较强意志完成' },
  9: { label: '极度困难', help: '接近极限，只能勉强坚持' },
  10: { label: '已尽最大努力', help: '最大努力，无法继续提高输出' },
}

export const SESSION_RPE_COLORS: Record<number, string> = {
  0: '#9fb8aa',
  1: '#86c98b',
  2: '#4fb86a',
  3: '#8bc34a',
  4: '#d6d45a',
  5: '#f4c430',
  6: '#f59e0b',
  7: '#f97316',
  8: '#ea580c',
  9: '#dc2626',
  10: '#991b1b',
}

const SESSION_RPE_NEUTRAL_COLOR = '#94a3b8'

export type SessionRpeColorTheme = {
  accent: string
  softBackground: string
  border: string
  surface: string
  shadow: string
}

function hexToRgba(hex: string, alpha: number) {
  const normalized = hex.replace('#', '')
  const fullHex = normalized.length === 3
    ? normalized.split('').map((char) => char + char).join('')
    : normalized

  const red = Number.parseInt(fullHex.slice(0, 2), 16)
  const green = Number.parseInt(fullHex.slice(2, 4), 16)
  const blue = Number.parseInt(fullHex.slice(4, 6), 16)

  return `rgba(${red}, ${green}, ${blue}, ${alpha})`
}

export function getSessionRpeMeta(value: number | null | undefined) {
  if (value == null || Number.isNaN(value) || !Number.isInteger(value)) return null
  return SESSION_RPE_LABELS[value] ?? null
}

export function getSessionRpeLabel(value: number | null | undefined, fallback = '') {
  return getSessionRpeMeta(value)?.label ?? fallback
}

export function getSessionRpeHelp(value: number | null | undefined, fallback = '') {
  return getSessionRpeMeta(value)?.help ?? fallback
}

export function getSessionRpeColor(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return SESSION_RPE_NEUTRAL_COLOR
  return SESSION_RPE_COLORS[value] ?? SESSION_RPE_NEUTRAL_COLOR
}

export function getSessionRpeColorTheme(value: number | null | undefined): SessionRpeColorTheme {
  const accent = getSessionRpeColor(value)
  return {
    accent,
    softBackground: hexToRgba(accent, 0.14),
    border: hexToRgba(accent, 0.28),
    surface: hexToRgba(accent, value == null || Number.isNaN(value) ? 0.06 : 0.08),
    shadow: hexToRgba(accent, value == null || Number.isNaN(value) ? 0.12 : 0.18),
  }
}

export function getSessionRpeDescription(value: number | null | undefined) {
  return getSessionRpeLabel(value, '请选择本次训练整体 RPE')
}

export function isHighSessionRpe(value: number | null | undefined) {
  return typeof value === 'number' && value >= 8
}

export function isExtremeSessionRpe(value: number | null | undefined) {
  return typeof value === 'number' && value >= 9
}
