import type { MonitoringAthleteCard } from '@/types/monitoring'

const ATHLETE_STATUS_SORT_PRIORITY: Record<string, number> = {
  in_progress: 1,
  not_started: 2,
  partial_complete: 3,
  absent: 4,
  completed: 5,
  no_plan: 6,
}

function getAthleteSortPriority(athlete: MonitoringAthleteCard) {
  if (athlete.sync_status === 'manual_retry_required') return 0
  return ATHLETE_STATUS_SORT_PRIORITY[athlete.session_status] ?? 99
}

export function sortMonitoringAthletes<T extends MonitoringAthleteCard>(athletes: readonly T[]) {
  return [...athletes].sort((left, right) => {
    const priorityDiff = getAthleteSortPriority(left) - getAthleteSortPriority(right)
    if (priorityDiff !== 0) return priorityDiff
    return left.athlete_name.localeCompare(right.athlete_name, 'zh-CN')
  })
}
