export function formatSessionDuration(startAt?: string | null, endAt?: string | null) {
  if (!startAt || !endAt) return ''

  const start = new Date(startAt)
  const end = new Date(endAt)
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return ''

  const diffMs = end.getTime() - start.getTime()
  if (diffMs <= 0) return ''

  const totalMinutes = Math.max(1, Math.round(diffMs / 60000))
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60

  if (hours > 0 && minutes > 0) return `${hours}小时${minutes}分钟`
  if (hours > 0) return `${hours}小时`
  return `${totalMinutes}分钟`
}

export function formatDurationMinutes(totalMinutes?: number | null) {
  if (totalMinutes == null || totalMinutes <= 0) return ''

  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60

  if (hours > 0 && minutes > 0) return `${hours}小时${minutes}分钟`
  if (hours > 0) return `${hours}小时`
  return `${totalMinutes}分钟`
}
