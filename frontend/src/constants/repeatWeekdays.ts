export const DEFAULT_REPEAT_WEEKDAYS = [1, 2, 3, 4, 5, 6, 7] as const

export const REPEAT_WEEKDAY_OPTIONS = [
  { value: 1, label: '周一' },
  { value: 2, label: '周二' },
  { value: 3, label: '周三' },
  { value: 4, label: '周四' },
  { value: 5, label: '周五' },
  { value: 6, label: '周六' },
  { value: 7, label: '周日' },
] as const

export function normalizeRepeatWeekdays(weekdays: readonly number[] | null | undefined) {
  if (!weekdays?.length) {
    return []
  }
  return Array.from(new Set(weekdays.filter((weekday) => weekday >= 1 && weekday <= 7))).sort((left, right) => left - right)
}

export function formatRepeatWeekdays(weekdays: readonly number[] | null | undefined) {
  const normalized = normalizeRepeatWeekdays(weekdays)
  if (!normalized.length) {
    return '未选择循环星期'
  }
  if (normalized.length === DEFAULT_REPEAT_WEEKDAYS.length) {
    return '周一至周日'
  }
  const labels = REPEAT_WEEKDAY_OPTIONS
    .filter((option) => normalized.includes(option.value))
    .map((option) => option.label)
  return labels.join('、')
}
