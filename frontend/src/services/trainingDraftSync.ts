import type { FullSessionSyncPayload, SessionSyncOperation } from '@/api/sessions'
import {
  buildTrainingDraftSessionKey,
  createCompleteSessionSyncOperation,
  createCreateSetSyncOperation,
  createTrainingLocalDraft,
  createUpdateSetSyncOperation,
  deleteTrainingLocalDraft,
  hasSessionRecordedSets,
  loadTrainingLocalDraft,
  saveTrainingLocalDraft,
  TRAINING_DRAFT_SYNC_STATUS,
  type TrainingManualRetryReason,
  type TrainingDraftSetPayload,
  type TrainingDraftSyncOperation,
  type TrainingDraftSyncStatus,
  type TrainingLocalDraft,
} from '@/utils/trainingDraft'
import {
  applyCreateSetToLocalSession,
  applyUpdateSetToLocalSession,
  cloneTrainingSession,
  finalizeLocalSession,
  findTrainingSessionRecord,
  resolveTrainingSessionItem,
} from '@/utils/trainingSessionState'

const FINAL_SESSION_STATUSES = new Set(['completed', 'absent', 'partial_complete'])

type CreateSetOperation = Extract<TrainingDraftSyncOperation, { operation_type: 'create_set' }>
type UpdateSetOperation = Extract<TrainingDraftSyncOperation, { operation_type: 'update_set' }>

export type DraftUiState = {
  activeItemId?: number | null
  latestSuggestion?: any | null
}

export type PersistTrainingDraftOptions = DraftUiState & {
  pendingSync?: boolean
  pendingOperations?: TrainingDraftSyncOperation[]
  lastServerUpdatedAt?: string | null
  lastServerSignature?: string | null
  incrementalFailureCount?: number
  lastSyncAttemptAt?: string | null
  syncStatus?: TrainingDraftSyncStatus
  syncIssueId?: number | null
  manualRetryReason?: TrainingManualRetryReason | null
}

export type PersistTrainingDraftResult = {
  action: 'saved' | 'discarded' | 'skipped'
  draft: TrainingLocalDraft | null
  sessionKey: string | null
  draftUiState: {
    activeItemId: number | null
    latestSuggestion: any | null
  }
}

export function buildTrainingSessionKey(targetSession: any) {
  return buildTrainingDraftSessionKey({
    athleteId: targetSession.athlete_id,
    assignmentId: targetSession.assignment_id,
    sessionDate: targetSession.session_date,
  })
}

export function persistTrainingLocalDraftState(params: {
  session: any | null
  athletes: any[]
  assignments: any[]
  activeDraftSessionKey: string
  draftPendingSync: boolean
  draftUiState: {
    activeItemId: number | null
    latestSuggestion: any | null
  }
  syncIssueId: number | null
  options?: PersistTrainingDraftOptions
}): PersistTrainingDraftResult {
  const { session, athletes, assignments, activeDraftSessionKey, draftPendingSync, draftUiState, syncIssueId, options = {} } = params
  const activeItemId = options.activeItemId ?? draftUiState.activeItemId
  const latestSuggestion = options.latestSuggestion ?? draftUiState.latestSuggestion

  if (!session) {
    return {
      action: 'skipped',
      draft: null,
      sessionKey: null,
      draftUiState: {
        activeItemId,
        latestSuggestion,
      },
    }
  }

  const existingDraft = activeDraftSessionKey ? loadTrainingLocalDraft(activeDraftSessionKey) : null
  const pendingSync = options.pendingSync ?? draftPendingSync
  const sessionKey = buildTrainingSessionKey(session)
  const hasRecords = hasSessionRecordedSets(session)
  if (!hasRecords && !pendingSync) {
    deleteTrainingLocalDraft(sessionKey)
    return {
      action: 'discarded',
      draft: null,
      sessionKey,
      draftUiState: {
        activeItemId,
        latestSuggestion,
      },
    }
  }

  const matchingAthlete = athletes.find((athlete) => athlete.id === session.athlete_id)
  const matchingAssignment = assignments.find((assignment) => assignment.id === session.assignment_id)
  const draft = createTrainingLocalDraft({
    sessionKey,
    session: cloneTrainingSession(session),
    athleteName: matchingAthlete?.full_name,
    templateName: matchingAssignment?.template?.name || null,
    currentItemId: activeItemId,
    latestSuggestion,
    syncStatus:
      options.syncStatus ?? (pendingSync ? TRAINING_DRAFT_SYNC_STATUS.PENDING : TRAINING_DRAFT_SYNC_STATUS.SYNCED),
    pendingSync,
    lastServerUpdatedAt: options.lastServerUpdatedAt ?? session.updated_at ?? existingDraft?.last_server_updated_at ?? null,
    lastServerSignature: options.lastServerSignature ?? session.server_signature ?? existingDraft?.last_server_signature ?? null,
    incrementalFailureCount: options.incrementalFailureCount ?? existingDraft?.incremental_failure_count ?? 0,
    lastSyncAttemptAt: options.lastSyncAttemptAt ?? existingDraft?.last_sync_attempt_at ?? null,
    syncIssueId: options.syncIssueId ?? existingDraft?.sync_issue_id ?? syncIssueId ?? null,
    manualRetryReason: options.manualRetryReason ?? existingDraft?.manual_retry_reason ?? null,
    pendingOperations: options.pendingOperations ?? getPendingTrainingOperations(sessionKey),
  })

  if (!draft.pending_sync && FINAL_SESSION_STATUSES.has(draft.session_snapshot?.status)) {
    deleteTrainingLocalDraft(draft.session_key)
    return {
      action: 'discarded',
      draft: null,
      sessionKey: draft.session_key,
      draftUiState: {
        activeItemId,
        latestSuggestion,
      },
    }
  }

  saveTrainingLocalDraft(draft)
  return {
    action: 'saved',
    draft,
    sessionKey: draft.session_key,
    draftUiState: {
      activeItemId,
      latestSuggestion,
    },
  }
}

export function getPendingTrainingSyncStatus(syncStatus: TrainingDraftSyncStatus) {
  return syncStatus === TRAINING_DRAFT_SYNC_STATUS.MANUAL_REQUIRED
    ? TRAINING_DRAFT_SYNC_STATUS.MANUAL_REQUIRED
    : TRAINING_DRAFT_SYNC_STATUS.PENDING
}

export function getPendingTrainingOperations(sessionKey: string) {
  if (!sessionKey) return [] as TrainingDraftSyncOperation[]
  const draft = loadTrainingLocalDraft(sessionKey)
  return draft?.pending_operations || []
}

export function appendPendingTrainingOperation(sessionKey: string, operation: TrainingDraftSyncOperation) {
  return [...getPendingTrainingOperations(sessionKey), ensurePendingCreateOperationHasLocalId(operation)]
}

export function buildCreateSetOperation(
  targetSession: any,
  itemId: number,
  payload: TrainingDraftSetPayload,
  localRecordId: number | null = null,
): CreateSetOperation {
  const item = resolveTrainingSessionItem(targetSession, itemId, itemId)
  if (!item) throw new Error('Session item not found')

  return createCreateSetSyncOperation({
    assignmentId: targetSession.assignment_id,
    sessionDate: targetSession.session_date,
    sessionId: targetSession.id ?? null,
    templateItemId: item.template_item_id,
    sessionItemId: targetSession.id ? item.id : null,
    localRecordId,
    payload,
  }) as CreateSetOperation
}

export function buildUpdateSetOperation(targetSession: any, recordId: number, payload: TrainingDraftSetPayload): UpdateSetOperation {
  return createUpdateSetSyncOperation({
    sessionId: targetSession.id ?? null,
    recordId,
    payload,
  }) as UpdateSetOperation
}

export function queuePendingTrainingUpdateOperation(params: {
  sessionKey: string
  targetSession: any
  recordId: number
  payload: TrainingDraftSetPayload
}) {
  const { sessionKey, targetSession, recordId, payload } = params
  const nextOperations = [...getPendingTrainingOperations(sessionKey)]
  const pendingCreateIndex = nextOperations.findIndex(
    (operation) => operation.operation_type === 'create_set' && operation.local_record_id === recordId,
  )
  if (pendingCreateIndex >= 0) {
    const pendingCreate = nextOperations[pendingCreateIndex] as CreateSetOperation
    nextOperations[pendingCreateIndex] = {
      ...pendingCreate,
      payload,
    }
    return nextOperations
  }

  const pendingUpdateIndex = nextOperations.findIndex(
    (operation) => operation.operation_type === 'update_set' && operation.record_id === recordId,
  )
  const updateOperation = buildUpdateSetOperation(targetSession, recordId, payload)
  if (pendingUpdateIndex >= 0) {
    nextOperations[pendingUpdateIndex] = updateOperation
    return nextOperations
  }
  return [...nextOperations, updateOperation]
}

export function queuePendingTrainingCompletionOperation(sessionKey: string, targetSession: any) {
  const filteredOperations = getPendingTrainingOperations(sessionKey).filter((operation) => operation.operation_type !== 'complete_session')
  return [
    ...filteredOperations,
    createCompleteSessionSyncOperation({
      assignmentId: targetSession.assignment_id,
      sessionDate: targetSession.session_date,
      sessionId: targetSession.id ?? null,
    }),
  ]
}

export function bindPendingOperationsToSession(nextSession: any, pendingOperations: TrainingDraftSyncOperation[]) {
  return pendingOperations.map((operation) => {
    if (operation.operation_type === 'create_set') {
      const matchedItem = nextSession.items?.find((item: any) => item.template_item_id === operation.template_item_id) || null
      return {
        ...operation,
        session_id: nextSession.id ?? operation.session_id,
        session_item_id: matchedItem?.id ?? operation.session_item_id,
      }
    }

    if (operation.operation_type === 'complete_session') {
      return {
        ...operation,
        session_id: nextSession.id ?? operation.session_id,
      }
    }

    return {
      ...operation,
      session_id: nextSession.id ?? operation.session_id,
    }
  })
}

export function toSessionSyncOperationPayload(operation: TrainingDraftSyncOperation): SessionSyncOperation {
  if (operation.operation_type === 'create_set') {
    return {
      operation_type: 'create_set',
      assignment_id: operation.assignment_id,
      session_date: operation.session_date,
      session_id: operation.session_id,
      template_item_id: operation.template_item_id,
      session_item_id: operation.session_item_id,
      local_record_id: operation.local_record_id,
      ...operation.payload,
    }
  }

  if (operation.operation_type === 'complete_session') {
    return {
      operation_type: 'complete_session',
      assignment_id: operation.assignment_id,
      session_date: operation.session_date,
      session_id: operation.session_id,
    }
  }

  return {
    operation_type: 'update_set',
    session_id: operation.session_id,
    record_id: operation.record_id,
    ...operation.payload,
  }
}

export function buildTrainingFullSessionSyncPayload(
  draft: TrainingLocalDraft,
  triggerReason: 'manual' | 'fallback',
): FullSessionSyncPayload {
  const snapshot = draft.session_snapshot
  return {
    assignment_id: snapshot.assignment_id,
    athlete_id: snapshot.athlete_id,
    template_id: snapshot.template_id ?? null,
    session_date: snapshot.session_date,
    session_id: snapshot.id ?? null,
    status: snapshot.status,
    started_at: snapshot.started_at ?? null,
    completed_at: snapshot.completed_at ?? null,
    session_rpe: snapshot.session_rpe ?? null,
    session_feedback: snapshot.session_feedback ?? null,
    last_server_updated_at: draft.last_server_updated_at,
    last_server_signature: draft.last_server_signature,
    trigger_reason: triggerReason,
    items: (snapshot.items || []).map((item: any) => ({
      template_item_id: item.template_item_id,
      exercise_id: item.exercise?.id,
      sort_order: item.sort_order,
      prescribed_sets: item.prescribed_sets,
      prescribed_reps: item.prescribed_reps,
      target_note: item.target_note ?? null,
      is_main_lift: !!item.is_main_lift,
      enable_auto_load: !!item.enable_auto_load,
      status: item.status,
      initial_load: item.initial_load ?? null,
      records: (item.records || []).map((record: any) => ({
        set_number: record.set_number,
        actual_weight: Number(record.actual_weight),
        actual_reps: Number(record.actual_reps),
        actual_rir: Number(record.actual_rir),
        final_weight: Number(record.final_weight),
        notes: (record.notes as string | null | undefined) ?? null,
        completed_at: record.completed_at,
      })),
    })),
  }
}

export function replayPendingTrainingOperations(baseSession: any, pendingOperations: TrainingDraftSyncOperation[]) {
  const nextSession = cloneTrainingSession(baseSession)
  for (const operation of pendingOperations) {
    if (operation.operation_type === 'create_set') {
      if (operation.local_record_id === null) {
        throw new Error('Pending create_set operation missing local_record_id')
      }
      applyCreateSetToLocalSession(
        nextSession,
        { itemId: operation.session_item_id, templateItemId: operation.template_item_id },
        operation.payload,
        operation.local_record_id,
        new Date().toISOString(),
      )
      continue
    }

    if (operation.operation_type === 'update_set') {
      applyUpdateSetToLocalSession(nextSession, operation.record_id, operation.payload, new Date().toISOString())
      continue
    }

    finalizeLocalSession(nextSession, new Date().toISOString())
  }
  return nextSession
}

function ensurePendingCreateOperationHasLocalId(operation: TrainingDraftSyncOperation) {
  if (operation.operation_type === 'create_set' && operation.local_record_id === null) {
    throw new Error('Pending create_set operation missing local_record_id')
  }
  return operation
}

export function recordNeedsFollowUpUpdate(localRecord: any, syncedRecord: any) {
  return (
    Number(localRecord.actual_weight) !== Number(syncedRecord.actual_weight)
    || Number(localRecord.actual_reps) !== Number(syncedRecord.actual_reps)
    || Number(localRecord.actual_rir) !== Number(syncedRecord.actual_rir)
    || Number(localRecord.final_weight) !== Number(syncedRecord.final_weight)
    || (localRecord.notes || null) !== (syncedRecord.notes || null)
  )
}

export function queueFollowUpTrainingUpdateOperation(
  pendingOperations: TrainingDraftSyncOperation[],
  sessionId: number | null,
  recordId: number,
  record: any,
) {
  const payload = {
    actual_weight: Number(record.actual_weight),
    actual_reps: Number(record.actual_reps),
    actual_rir: Number(record.actual_rir),
    final_weight: Number(record.final_weight),
    notes: (record.notes as string | null | undefined) ?? null,
  }
  const filteredOperations = pendingOperations.filter(
    (operation) => !(operation.operation_type === 'update_set' && operation.record_id === recordId),
  )
  return [
    createUpdateSetSyncOperation({
      sessionId,
      recordId,
      payload,
    }),
    ...filteredOperations,
  ]
}

export function findPendingTrainingRecord(targetSession: any, recordId: number) {
  return findTrainingSessionRecord(targetSession, recordId)
}

export function extractTrainingSyncErrorMessage(error: unknown) {
  const maybeError = error as { response?: { data?: { detail?: string } }; message?: string }
  return maybeError?.response?.data?.detail || maybeError?.message || '同步失败'
}

export function buildTrainingManualRetrySummary(triggerReason: 'manual' | 'fallback') {
  return triggerReason === 'manual'
    ? '手动整课补传失败，需教练或管理员继续人工处理。'
    : '自动重试与整课兜底补传都已失败，需教练或管理员继续人工处理。'
}
