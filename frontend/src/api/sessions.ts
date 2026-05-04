import client from './client'

export type TrainingSessionExercise = {
  id: number
  name: string
}

export type TrainingSessionSetRecord = {
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
}

export type TrainingSessionItemSnapshot = {
  id: number | null
  template_item_id: number
  sort_order: number
  prescribed_sets: number
  prescribed_reps: number
  target_note: string | null
  is_main_lift: boolean
  enable_auto_load: boolean
  initial_load: number | null
  status: string
  exercise: TrainingSessionExercise
  records: TrainingSessionSetRecord[]
}

export type TrainingSessionSnapshot = {
  id: number | null
  athlete_id: number
  assignment_id: number
  template_id: number
  session_date: string
  status: string
  updated_at: string | null
  server_signature: string | null
  started_at: string | null
  completed_at: string | null
  session_rpe: number | null
  session_feedback: string | null
  coach_note: string | null
  athlete_note: string | null
  items: TrainingSessionItemSnapshot[]
}

export type TrainingSessionItem = TrainingSessionItemSnapshot & {
  id: number
}

export type TrainingSessionRead = Omit<TrainingSessionSnapshot, 'items' | 'id'> & {
  id: number
  items: TrainingSessionItem[]
}

export type TrainingSuggestion = {
  suggestion_weight: number | null
  decision_hint: string
  reason_code: string
  reason_text: string
  should_deload: boolean
  should_stop_progression: boolean
}

export type TrainingSetMutationResponse = {
  record: TrainingSessionSetRecord | null
  next_suggestion: TrainingSuggestion | null
  item: TrainingSessionItem | null
  session: TrainingSessionRead
  session_status: string
  session_completed_at: string | null
  operation_type?: 'create_set' | 'update_set' | 'complete_session'
  local_record_id?: number | null
  sync_status?: 'synced'
}

export type SessionSyncOperation =
  | {
      operation_type: 'create_set'
      assignment_id: number
      session_date: string
      template_item_id: number
      session_id?: number | null
      session_item_id?: number | null
      local_record_id?: number | null
      actual_weight: number
      actual_reps: number
      actual_rir: number
      final_weight?: number | null
      notes?: string | null
    }
  | {
      operation_type: 'update_set'
      session_id?: number | null
      record_id: number
      actual_weight: number
      actual_reps: number
      actual_rir: number
      final_weight?: number | null
      notes?: string | null
    }
  | {
      operation_type: 'complete_session'
      assignment_id: number
      session_date: string
      session_id?: number | null
    }

export type SessionFinishFeedbackPayload = {
  session_rpe: number
  session_feedback?: string | null
}

export type FullSessionSyncPayload = {
  assignment_id: number
  athlete_id: number
  template_id?: number | null
  session_date: string
  session_id?: number | null
  status: string
  started_at?: string | null
  completed_at?: string | null
  session_rpe?: number | null
  session_feedback?: string | null
  last_server_updated_at?: string | null
  last_server_signature?: string | null
  trigger_reason: 'manual' | 'fallback'
  items: Array<{
    template_item_id: number
    exercise_id: number
    sort_order: number
    prescribed_sets: number
    prescribed_reps: number
    target_note?: string | null
    is_main_lift: boolean
    enable_auto_load: boolean
    status: string
    initial_load?: number | null
    records: Array<{
      set_number: number
      actual_weight: number
      actual_reps: number
      actual_rir: number
      final_weight: number
      notes?: string | null
      completed_at: string
    }>
  }>
}

export type SessionFullSyncResponse = {
  session: TrainingSessionRead
  session_status: string
  session_completed_at: string | null
  sync_status: 'synced'
  sync_mode: 'full'
  conflict_logged: boolean
}

export type TrainingSyncIssue = {
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

export type TrainingSyncIssueReportPayload = {
  session_key: string
  athlete_id: number
  assignment_id?: number | null
  session_id?: number | null
  session_date: string
  failure_count: number
  summary: string
  last_error?: string | null
  sync_payload: FullSessionSyncPayload
}

export type TrainingSyncIssueRetryResponse = {
  issue: TrainingSyncIssue
  session: TrainingSessionRead
  conflict_logged: boolean
}

export async function fetchTrainingAthletes(sessionDate?: string) {
  const { data } = await client.get('/training/athletes', { params: { session_date: sessionDate } })
  return data
}

export async function fetchTrainingPlans(athleteId: number, sessionDate?: string) {
  const { data } = await client.get('/training/plans', { params: { athlete_id: athleteId, session_date: sessionDate } })
  return data
}

export async function startTrainingSession(assignmentId: number, sessionDate?: string) {
  const { data } = await client.post<TrainingSessionSnapshot>(`/training/plans/${assignmentId}/session`, null, {
    params: { session_date: sessionDate },
  })
  return data
}

export async function fetchSession(sessionId: number) {
  const { data } = await client.get<TrainingSessionRead>(`/training/sessions/${sessionId}`)
  return data
}

export async function submitSet(itemId: number, payload: Record<string, unknown>) {
  const { data } = await client.post<TrainingSetMutationResponse>(`/training/session-items/${itemId}/sets`, payload)
  return data
}

export async function updateSetRecord(recordId: number, payload: Record<string, unknown>) {
  const { data } = await client.patch<TrainingSetMutationResponse>(`/training/set-records/${recordId}`, payload)
  return data
}

export async function completeTrainingSession(sessionId: number) {
  const { data } = await client.post<TrainingSessionRead>(`/training/sessions/${sessionId}/complete`)
  return data
}

export async function submitTrainingSessionFinishFeedback(sessionId: number, payload: SessionFinishFeedbackPayload) {
  const { data } = await client.post<TrainingSessionRead>(`/training/sessions/${sessionId}/finish-feedback`, payload)
  return data
}

export async function syncTrainingSetOperation(payload: SessionSyncOperation) {
  const { data } = await client.post<TrainingSetMutationResponse>('/training/session-sync', payload)
  return data
}

export async function syncTrainingSessionSnapshot(payload: FullSessionSyncPayload) {
  const { data } = await client.post<SessionFullSyncResponse>('/training/session-sync/full', payload)
  return data
}

export async function reportTrainingSyncIssue(payload: TrainingSyncIssueReportPayload) {
  const { data } = await client.post('/training/session-sync/issues/report', payload)
  return data as TrainingSyncIssue
}

export async function fetchTrainingSyncIssues(params?: {
  athlete_id?: number
  date_from?: string
  date_to?: string
  issue_status?: 'manual_retry_required' | 'resolved'
}) {
  const { data } = await client.get('/training/session-sync/issues', { params })
  return data as TrainingSyncIssue[]
}

export async function retryTrainingSyncIssue(issueId: number) {
  const { data } = await client.post(`/training/session-sync/issues/${issueId}/retry`)
  return data as TrainingSyncIssueRetryResponse
}

export async function resolveTrainingSyncIssue(issueId: number) {
  const { data } = await client.post(`/training/session-sync/issues/${issueId}/resolve`)
  return data as TrainingSyncIssue
}
