import {
  getTrainingStatusLabel,
  MONITORING_STATUS_LABEL_OVERRIDES,
} from '@/constants/trainingStatus'
import type { MonitoringAlertLevel, MonitoringAthleteCard } from '@/types/monitoring'

export function resolveMonitoringAlertLevel(athlete: MonitoringAthleteCard): MonitoringAlertLevel {
  if (athlete.alert_level && athlete.alert_level !== 'none') return athlete.alert_level
  if (!athlete.has_alert && athlete.sync_status === 'synced') return 'none'
  if (athlete.sync_status === 'manual_retry_required') return 'critical'
  return 'warning'
}

export function resolveMonitoringAlertReasons(athlete: MonitoringAthleteCard) {
  if (athlete.alert_reasons?.length) return athlete.alert_reasons
  if (athlete.sync_status === 'manual_retry_required') return ['同步异常待处理']
  if (athlete.sync_status === 'pending') return ['本地数据待同步']
  if (athlete.session_status === 'partial_complete') return ['已结束未完成']
  if (athlete.session_status === 'absent') return ['缺席']
  return [getTrainingStatusLabel(athlete.session_status, MONITORING_STATUS_LABEL_OVERRIDES)]
}

export function buildMonitoringAlertStorageKey(sessionDate: string, bucket: 'dismissed' | 'deleted' = 'dismissed') {
  return `monitoring-alert-${bucket}:${sessionDate}`
}

export function buildMonitoringAlertKey(sessionDate: string, athlete: MonitoringAthleteCard) {
  const level = resolveMonitoringAlertLevel(athlete)
  const reasons = resolveMonitoringAlertReasons(athlete)
  return JSON.stringify([
    sessionDate,
    athlete.athlete_id,
    athlete.sync_status,
    athlete.session_status,
    level,
    athlete.alert_generated_at || '',
    ...reasons,
  ])
}
