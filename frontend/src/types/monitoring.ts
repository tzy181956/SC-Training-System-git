import type { TrainingStatus } from '@/constants/trainingStatus'

export type MonitoringSyncStatus = 'synced' | 'pending' | 'manual_retry_required'

export type MonitoringBoardSectionId = 'team-summary' | 'athlete-board' | 'sync-alerts'

export type MonitoringBoardSection = {
  id: MonitoringBoardSectionId
  title: string
  description: string
}

export type MonitoringLatestSetSnapshot = {
  actual_weight: number | null
  actual_reps: number | null
  actual_rir: number | null
  completed_at: string | null
}

export type MonitoringAthleteCard = {
  athlete_id: number
  athlete_name: string
  team_id: number | null
  team_name: string | null
  session_id: number | null
  session_status: TrainingStatus
  sync_status: MonitoringSyncStatus
  current_exercise_name: string | null
  completed_items: number
  total_items: number
  completed_sets: number
  total_sets: number
  latest_set: MonitoringLatestSetSnapshot | null
  has_alert: boolean
}

export type MonitoringTeamSummaryItem = {
  team_id: number | null
  team_name: string
  total_athletes: number
  not_started_count: number
  in_progress_count: number
  completed_count: number
  partial_complete_count: number
  absent_count: number
  pending_sync_count: number
  manual_retry_required_count: number
}

export type MonitoringTeamOption = {
  team_id: number | null
  team_name: string
  athlete_count: number
}

export type MonitoringTodayResponse = {
  session_date: string
  updated_at: string | null
  teams: MonitoringTeamOption[]
  athletes: MonitoringAthleteCard[]
}

export type MonitoringTeamSummaryResponse = {
  session_date: string
  updated_at: string | null
  teams: MonitoringTeamSummaryItem[]
}
