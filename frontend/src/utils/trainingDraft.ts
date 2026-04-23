const DRAFT_STORAGE_PREFIX = 'training-local-draft:'
const FINAL_SESSION_STATUSES = new Set(['completed', 'absent', 'partial_complete'])

export const TRAINING_DRAFT_SYNC_STATUS = {
  SYNCED: 'synced',
  PENDING: 'pending',
} as const

export type TrainingDraftSyncStatus = (typeof TRAINING_DRAFT_SYNC_STATUS)[keyof typeof TRAINING_DRAFT_SYNC_STATUS]

export type TrainingDraftSetPayload = {
  actual_weight: number
  actual_reps: number
  actual_rir: number
  final_weight: number
  notes: string | null
}

type TrainingDraftCreateSetOperation = {
  operation_key: string
  operation_type: 'create_set'
  assignment_id: number
  session_date: string
  session_id: number | null
  template_item_id: number
  session_item_id: number | null
  local_record_id: number
  payload: TrainingDraftSetPayload
  queued_at: string
}

type TrainingDraftUpdateSetOperation = {
  operation_key: string
  operation_type: 'update_set'
  session_id: number | null
  record_id: number
  payload: TrainingDraftSetPayload
  queued_at: string
}

type TrainingDraftCompleteSessionOperation = {
  operation_key: string
  operation_type: 'complete_session'
  assignment_id: number
  session_date: string
  session_id: number | null
  queued_at: string
}

export type TrainingDraftSyncOperation =
  | TrainingDraftCreateSetOperation
  | TrainingDraftUpdateSetOperation
  | TrainingDraftCompleteSessionOperation

export type TrainingLocalDraft = {
  session_key: string
  athlete_id: number
  athlete_name?: string | null
  assignment_id: number
  session_id: number | null
  template_id: number | null
  template_name?: string | null
  session_date: string
  current_item_id: number | null
  current_exercise_id: number | null
  recorded_sets: number
  sync_status: TrainingDraftSyncStatus
  pending_sync: boolean
  last_server_updated_at: string | null
  incremental_failure_count: number
  last_sync_attempt_at: string | null
  last_modified_at: string
  latest_suggestion: any | null
  pending_operations: TrainingDraftSyncOperation[]
  session_snapshot: any
}

type TrainingDraftKeyParams = {
  athleteId: number
  assignmentId: number
  sessionDate: string
}

export function buildTrainingDraftSessionKey({ athleteId, assignmentId, sessionDate }: TrainingDraftKeyParams) {
  return `athlete:${athleteId}:assignment:${assignmentId}:date:${sessionDate}`
}

export function countSessionRecordedSets(session: any | null | undefined) {
  if (!session?.items?.length) return 0
  return session.items.reduce((total: number, item: any) => total + (item.records?.length || 0), 0)
}

export function hasSessionRecordedSets(session: any | null | undefined) {
  return countSessionRecordedSets(session) > 0
}

export function createTrainingLocalDraft(params: {
  sessionKey: string
  session: any
  athleteName?: string | null
  templateName?: string | null
  currentItemId?: number | null
  latestSuggestion?: any | null
  syncStatus?: TrainingDraftSyncStatus
  pendingSync?: boolean
  lastServerUpdatedAt?: string | null
  incrementalFailureCount?: number
  lastSyncAttemptAt?: string | null
  pendingOperations?: TrainingDraftSyncOperation[]
}): TrainingLocalDraft {
  const {
    session,
    sessionKey,
    athleteName,
    templateName,
    currentItemId = null,
    latestSuggestion = null,
    syncStatus = TRAINING_DRAFT_SYNC_STATUS.SYNCED,
    pendingSync = false,
    lastServerUpdatedAt = null,
    incrementalFailureCount = 0,
    lastSyncAttemptAt = null,
    pendingOperations = [],
  } = params
  const activeItem = session?.items?.find((item: any) => item.id === currentItemId) || null

  return {
    session_key: sessionKey,
    athlete_id: session.athlete_id,
    athlete_name: athleteName || null,
    assignment_id: session.assignment_id,
    session_id: session.id ?? null,
    template_id: session.template_id ?? null,
    template_name: templateName || null,
    session_date: session.session_date,
    current_item_id: currentItemId,
    current_exercise_id: activeItem?.exercise?.id || null,
    recorded_sets: countSessionRecordedSets(session),
    sync_status: syncStatus,
    pending_sync: pendingSync || syncStatus === TRAINING_DRAFT_SYNC_STATUS.PENDING,
    last_server_updated_at: lastServerUpdatedAt,
    incremental_failure_count: incrementalFailureCount,
    last_sync_attempt_at: lastSyncAttemptAt,
    last_modified_at: new Date().toISOString(),
    latest_suggestion: latestSuggestion || null,
    pending_operations: pendingOperations,
    session_snapshot: session,
  }
}

export function saveTrainingLocalDraft(draft: TrainingLocalDraft) {
  localStorage.setItem(`${DRAFT_STORAGE_PREFIX}${draft.session_key}`, JSON.stringify(draft))
}

export function loadTrainingLocalDraft(sessionKey: string) {
  const raw = localStorage.getItem(`${DRAFT_STORAGE_PREFIX}${sessionKey}`)
  if (!raw) return null

  try {
    return normalizeTrainingLocalDraft(JSON.parse(raw))
  } catch {
    return null
  }
}

export function deleteTrainingLocalDraft(sessionKey: string) {
  localStorage.removeItem(`${DRAFT_STORAGE_PREFIX}${sessionKey}`)
}

export function findTrainingLocalDraftBySessionId(sessionId: number) {
  const drafts = listTrainingLocalDrafts()
  return drafts.find((draft) => draft.session_id === sessionId) || null
}

export function listTrainingLocalDrafts() {
  const drafts: TrainingLocalDraft[] = []

  for (let index = 0; index < localStorage.length; index += 1) {
    const key = localStorage.key(index)
    if (!key?.startsWith(DRAFT_STORAGE_PREFIX)) continue

    const raw = localStorage.getItem(key)
    if (!raw) continue

    try {
      const normalized = normalizeTrainingLocalDraft(JSON.parse(raw))
      if (normalized) {
        drafts.push(normalized)
      }
    } catch {
      continue
    }
  }

  return drafts.sort((left, right) => right.last_modified_at.localeCompare(left.last_modified_at))
}

export function shouldOfferDraftRestore(draft: TrainingLocalDraft | null) {
  if (!draft) return false
  if (!draft.recorded_sets) return false
  return draft.sync_status === TRAINING_DRAFT_SYNC_STATUS.PENDING || !FINAL_SESSION_STATUSES.has(draft.session_snapshot?.status)
}

export function createCreateSetSyncOperation(params: {
  assignmentId: number
  sessionDate: string
  sessionId: number | null
  templateItemId: number
  sessionItemId: number | null
  localRecordId: number
  payload: TrainingDraftSetPayload
}): TrainingDraftSyncOperation {
  return {
    operation_key: `create:${params.localRecordId}`,
    operation_type: 'create_set',
    assignment_id: params.assignmentId,
    session_date: params.sessionDate,
    session_id: params.sessionId,
    template_item_id: params.templateItemId,
    session_item_id: params.sessionItemId,
    local_record_id: params.localRecordId,
    payload: params.payload,
    queued_at: new Date().toISOString(),
  }
}

export function createUpdateSetSyncOperation(params: {
  sessionId: number | null
  recordId: number
  payload: TrainingDraftSetPayload
}): TrainingDraftSyncOperation {
  return {
    operation_key: `update:${params.recordId}`,
    operation_type: 'update_set',
    session_id: params.sessionId,
    record_id: params.recordId,
    payload: params.payload,
    queued_at: new Date().toISOString(),
  }
}

export function createCompleteSessionSyncOperation(params: {
  assignmentId: number
  sessionDate: string
  sessionId: number | null
}): TrainingDraftSyncOperation {
  return {
    operation_key: `complete:${params.assignmentId}:${params.sessionDate}`,
    operation_type: 'complete_session',
    assignment_id: params.assignmentId,
    session_date: params.sessionDate,
    session_id: params.sessionId,
    queued_at: new Date().toISOString(),
  }
}

function normalizeTrainingLocalDraft(raw: any): TrainingLocalDraft | null {
  if (!raw || typeof raw !== 'object') return null
  const syncStatus =
    raw.sync_status === TRAINING_DRAFT_SYNC_STATUS.PENDING
      ? TRAINING_DRAFT_SYNC_STATUS.PENDING
      : TRAINING_DRAFT_SYNC_STATUS.SYNCED
  const pendingOperations = Array.isArray(raw.pending_operations) ? raw.pending_operations : []

  return {
    session_key: raw.session_key,
    athlete_id: raw.athlete_id,
    athlete_name: raw.athlete_name ?? null,
    assignment_id: raw.assignment_id,
    session_id: raw.session_id ?? null,
    template_id: raw.template_id ?? null,
    template_name: raw.template_name ?? null,
    session_date: raw.session_date,
    current_item_id: raw.current_item_id ?? null,
    current_exercise_id: raw.current_exercise_id ?? null,
    recorded_sets: raw.recorded_sets ?? countSessionRecordedSets(raw.session_snapshot),
    sync_status: raw.pending_sync ? TRAINING_DRAFT_SYNC_STATUS.PENDING : syncStatus,
    pending_sync: raw.pending_sync ?? syncStatus === TRAINING_DRAFT_SYNC_STATUS.PENDING,
    last_server_updated_at: raw.last_server_updated_at ?? null,
    incremental_failure_count: Number(raw.incremental_failure_count ?? 0),
    last_sync_attempt_at: raw.last_sync_attempt_at ?? null,
    last_modified_at: raw.last_modified_at ?? new Date().toISOString(),
    latest_suggestion: raw.latest_suggestion ?? null,
    pending_operations: pendingOperations,
    session_snapshot: raw.session_snapshot ?? null,
  }
}
