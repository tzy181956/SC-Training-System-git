import type { MonitoringAthleteCard } from '@/types/monitoring'

const ATHLETE_STATUS_SORT_PRIORITY: Record<string, number> = {
  in_progress: 1,
  not_started: 2,
  partial_complete: 3,
  absent: 4,
  completed: 5,
  no_plan: 6,
}

const ALERT_LEVEL_SORT_PRIORITY: Record<string, number> = {
  critical: 0,
  warning: 1,
  info: 2,
  none: 3,
}

function getAthleteSortPriority(athlete: MonitoringAthleteCard) {
  const alertPriority = ALERT_LEVEL_SORT_PRIORITY[athlete.alert_level] ?? ALERT_LEVEL_SORT_PRIORITY.none
  return alertPriority * 10 + (ATHLETE_STATUS_SORT_PRIORITY[athlete.session_status] ?? 9)
}

export function sortMonitoringAthletes<T extends MonitoringAthleteCard>(athletes: readonly T[]) {
  return [...athletes].sort((left, right) => {
    const priorityDiff = getAthleteSortPriority(left) - getAthleteSortPriority(right)
    if (priorityDiff !== 0) return priorityDiff
    return left.athlete_name.localeCompare(right.athlete_name, 'zh-CN')
  })
}
