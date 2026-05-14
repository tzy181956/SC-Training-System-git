import client from './client'

type DangerousActionPayload = {
  confirmed: true
  actor_name?: string | null
  confirmation_text?: string | null
}

export type TrainingReportSetRecord = {
  id: number
  set_number: number
  target_weight: number | null
  target_reps: number
  actual_weight: number
  actual_reps: number
  actual_rir: number
  suggestion_weight: number | null
  suggestion_reason: string | null
  user_decision: string
  final_weight: number
  completed_at: string
  notes: string | null
  adjustment_type: string
}

export type TrainingReportEditLog = {
  id: number
  action_type: string
  actor_name: string
  object_type: string
  object_id: number | null
  summary: string
  created_at: string
  edited_at: string
}

export type TrainingReportItem = {
  id: number
  exercise_name: string
  sort_order: number
  prescribed_sets: number
  prescribed_reps: number
  completed_sets: number
  target_note: string | null
  is_main_lift: boolean
  status: string
  records: TrainingReportSetRecord[]
}

export type TrainingReportSession = {
  id: number
  session_date: string
  template_name: string
  status: string
  started_at: string | null
  session_duration_minutes: number | null
  session_rpe: number | null
  session_srpe_load: number | null
  session_feedback: string | null
  completed_at: string | null
  completed_items: number
  total_items: number
  completed_sets: number
  total_sets: number
  items: TrainingReportItem[]
  edit_logs: TrainingReportEditLog[]
}

export type TrainingReportSyncIssue = {
  id: number
  athlete_id: number
  athlete_name?: string | null
  assignment_id?: number | null
  session_id?: number | null
  session_date: string
  session_key: string
  issue_status: 'manual_retry_required' | 'resolved'
  summary: string
  failure_count: number
  last_error?: string | null
  updated_at: string
  resolved_at?: string | null
}

export type TrainingReportResponse = {
  athlete: {
    id: number
    full_name: string
  }
  date_range: {
    date_from: string
    date_to: string
  }
  summary: {
    total_sessions: number
    completed_sessions: number
    completion_rate: number
    completed_items: number
    total_items: number
    completed_sets: number
    total_sets: number
    latest_session_date: string | null
    voided_sessions: number
  }
  sessions: TrainingReportSession[]
  trend: {
    main_lift_series: Array<{
      exercise_name: string
      points: Array<{ session_date: string; value: number }>
    }>
    completion_series: Array<{
      session_date: string
      template_name: string
      completion_rate: number
    }>
  }
  flags: Array<{
    level: string
    title: string
    description: string
  }>
  sync_issues: TrainingReportSyncIssue[]
}

export async function fetchTrainingReport(params: {
  athlete_id: number
  date_from?: string
  date_to?: string
}) {
  const { data } = await client.get<TrainingReportResponse>('/training-reports', { params })
  return data
}

export async function coachUpdateTrainingReportSetRecord(
  recordId: number,
  payload: {
    actual_weight: number
    actual_reps: number
    actual_rir: number
    notes?: string | null
    actor_name?: string | null
  },
) {
  const { data } = await client.patch(`/training-reports/set-records/${recordId}`, payload)
  return data
}

export async function coachAddTrainingReportSet(
  itemId: number,
  payload: {
    actual_weight: number
    actual_reps: number
    actual_rir: number
    notes?: string | null
    actor_name?: string | null
  },
) {
  const { data } = await client.post(`/training-reports/session-items/${itemId}/sets`, payload)
  return data
}

export async function coachDeleteTrainingReportSetRecord(recordId: number, payload: DangerousActionPayload) {
  const { data } = await client.delete(`/training-reports/set-records/${recordId}`, { data: payload })
  return data
}

export async function coachVoidTrainingReportSession(sessionId: number, payload: DangerousActionPayload) {
  const { data } = await client.post(`/training-reports/sessions/${sessionId}/void`, payload)
  return data
}
