import { defineStore } from 'pinia'
import { ref } from 'vue'

import {
  completeTrainingSession,
  fetchSession,
  fetchTrainingAthletes,
  fetchTrainingPlans,
  syncTrainingSessionSnapshot,
  syncTrainingSetOperation,
  type FullSessionSyncPayload,
  type SessionSyncOperation,
  startTrainingSession,
} from '@/api/sessions'
import {
  buildTrainingDraftSessionKey,
  createCompleteSessionSyncOperation,
  createCreateSetSyncOperation,
  createTrainingLocalDraft,
  createUpdateSetSyncOperation,
  deleteTrainingLocalDraft,
  findTrainingLocalDraftBySessionId,
  hasSessionRecordedSets,
  loadTrainingLocalDraft,
  saveTrainingLocalDraft,
  TRAINING_DRAFT_SYNC_STATUS,
  type TrainingDraftSyncOperation,
  type TrainingDraftSyncStatus,
  shouldOfferDraftRestore,
  type TrainingLocalDraft,
} from '@/utils/trainingDraft'

const FINAL_SESSION_STATUSES = new Set(['completed', 'absent', 'partial_complete'])
const NOT_STARTED_SESSION_STATUS = 'not_started'
const IN_PROGRESS_SESSION_STATUS = 'in_progress'
const SYNC_RETRY_DELAY_MS = 4000
const SYNC_RETRY_IDLE_MS = 1200
const FULL_SYNC_FAILURE_THRESHOLD = 3

type DraftUiState = {
  activeItemId?: number | null
  latestSuggestion?: any | null
}

type NormalizedSetPayload = {
  actual_weight: number
  actual_reps: number
  actual_rir: number
  final_weight: number
  notes: string | null
}

type CreateSetOperation = Extract<TrainingDraftSyncOperation, { operation_type: 'create_set' }>
type UpdateSetOperation = Extract<TrainingDraftSyncOperation, { operation_type: 'update_set' }>

export const useTrainingStore = defineStore('training', () => {
  const athletes = ref<any[]>([])
  const selectedAthleteId = ref<number>(0)
  const sessionDate = ref<string>('')
  const assignments = ref<any[]>([])
  const previewAssignmentId = ref<number>(0)
  const session = ref<any | null>(null)
  const activeDraftSessionKey = ref<string>('')
  const draftPendingSync = ref(false)
  const syncStatus = ref<TrainingDraftSyncStatus>(TRAINING_DRAFT_SYNC_STATUS.SYNCED)
  const draftUiState = ref<{ activeItemId: number | null; latestSuggestion: any | null }>({
    activeItemId: null,
    latestSuggestion: null,
  })
  let syncRetryTimer: number | null = null
  let syncInFlight = false

  if (typeof window !== 'undefined') {
    window.addEventListener('online', () => {
      _scheduleIncrementalSync(300)
    })
  }

  async function hydrateAthletes(targetDate = sessionDate.value) {
    athletes.value = await fetchTrainingAthletes(targetDate)
    const selectedStillExists = athletes.value.some((athlete) => athlete.id === selectedAthleteId.value)
    if (!selectedStillExists) {
      const preferredAthlete =
        athletes.value.find((athlete) => athlete.training_status !== 'no_plan') || athletes.value[0] || null
      selectedAthleteId.value = preferredAthlete?.id || 0
    }
  }

  async function loadPlans(athleteId: number, targetDate: string) {
    selectedAthleteId.value = athleteId
    sessionDate.value = targetDate
    const response = await fetchTrainingPlans(athleteId, targetDate)
    assignments.value = response.assignments
    previewAssignmentId.value = response.assignments[0]?.id || 0
    return response
  }

  async function openPlanSession(assignmentId: number, targetDate: string) {
    previewAssignmentId.value = assignmentId
    sessionDate.value = targetDate
    session.value = await startTrainingSession(assignmentId, targetDate)
    activeDraftSessionKey.value = _buildSessionKey(session.value)
    _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.SYNCED)
    return session.value
  }

  async function loadSession(sessionId: number) {
    session.value = await fetchSession(sessionId)
    activeDraftSessionKey.value = _buildSessionKey(session.value)
    _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.SYNCED)
    return session.value
  }

  async function recordSet(itemId: number, payload: Record<string, unknown>, uiState: DraftUiState = {}) {
    if (!session.value) throw new Error('No session loaded')

    const normalizedPayload = _normalizeSetPayload(payload)
    if (draftPendingSync.value) {
      return _saveSetLocally(itemId, normalizedPayload, uiState)
    }

    try {
      const response = await syncTrainingSetOperation(
        _toSessionSyncOperationPayload(_buildCreateSetOperation(session.value, itemId, normalizedPayload)),
      )
      _replaceSession(response.session)
      _persistLocalDraft({
        ...uiState,
        latestSuggestion: response.next_suggestion ?? uiState.latestSuggestion ?? null,
        pendingSync: false,
        lastServerUpdatedAt: response.session.updated_at ?? null,
        lastServerSignature: response.session.server_signature ?? null,
        incrementalFailureCount: 0,
        lastSyncAttemptAt: new Date().toISOString(),
      })
      await hydrateAthletes(sessionDate.value)
      return response
    } catch {
      return _saveSetLocally(itemId, normalizedPayload, uiState)
    }
  }

  async function reviseSetRecord(recordId: number, payload: Record<string, unknown>, uiState: DraftUiState = {}) {
    if (!session.value) throw new Error('No session loaded')

    const normalizedPayload = _normalizeSetPayload(payload)
    if (draftPendingSync.value) {
      return _reviseSetLocally(recordId, normalizedPayload, uiState)
    }

    try {
      const response = await syncTrainingSetOperation(
        _toSessionSyncOperationPayload(_buildUpdateSetOperation(session.value, recordId, normalizedPayload)),
      )
      _replaceSession(response.session)
      _persistLocalDraft({
        ...uiState,
        latestSuggestion: response.next_suggestion ?? uiState.latestSuggestion ?? null,
        pendingSync: false,
        lastServerUpdatedAt: response.session.updated_at ?? null,
        lastServerSignature: response.session.server_signature ?? null,
        incrementalFailureCount: 0,
        lastSyncAttemptAt: new Date().toISOString(),
      })
      await hydrateAthletes(sessionDate.value)
      return response
    } catch {
      return _reviseSetLocally(recordId, normalizedPayload, uiState)
    }
  }

  async function endSession(_sessionId: number, uiState: DraftUiState = {}) {
    if (!session.value) throw new Error('No session loaded')

    if (draftPendingSync.value || !session.value.id) {
      return _endSessionLocally(uiState)
    }

    try {
      const nextSession = await completeTrainingSession(session.value.id)
      _replaceSession(nextSession)
      _persistLocalDraft({
        ...uiState,
        latestSuggestion: null,
        pendingSync: false,
        lastServerUpdatedAt: nextSession.updated_at ?? null,
        lastServerSignature: nextSession.server_signature ?? null,
        incrementalFailureCount: 0,
        lastSyncAttemptAt: new Date().toISOString(),
      })
      await hydrateAthletes(sessionDate.value)
      return nextSession
    } catch {
      return _endSessionLocally(uiState)
    }
  }

  function setPreviewAssignment(assignmentId: number) {
    previewAssignmentId.value = assignmentId
  }

  function getDraftForSession(targetSession = session.value) {
    if (!targetSession) return null
    const sessionKey = _buildSessionKey(targetSession)
    const draft = loadTrainingLocalDraft(sessionKey)
    return shouldOfferDraftRestore(draft) ? draft : null
  }

  function getDraftBySessionId(sessionId: number) {
    const draft = findTrainingLocalDraftBySessionId(sessionId)
    return shouldOfferDraftRestore(draft) ? draft : null
  }

  function getDraftByContext(athleteId: number, assignmentId: number, targetDate: string) {
    const sessionKey = buildTrainingDraftSessionKey({
      athleteId,
      assignmentId,
      sessionDate: targetDate,
    })
    const draft = loadTrainingLocalDraft(sessionKey)
    return shouldOfferDraftRestore(draft) ? draft : null
  }

  function restoreDraft(draft: TrainingLocalDraft) {
    session.value = _clone(draft.session_snapshot)
    selectedAthleteId.value = draft.athlete_id
    sessionDate.value = draft.session_date
    previewAssignmentId.value = draft.assignment_id
    activeDraftSessionKey.value = draft.session_key
    draftUiState.value = {
      activeItemId: draft.current_item_id ?? null,
      latestSuggestion: draft.latest_suggestion ?? null,
    }
    _setSyncStatus(draft.sync_status)
    if (draft.sync_status === TRAINING_DRAFT_SYNC_STATUS.PENDING) {
      _scheduleIncrementalSync()
    }
    return session.value
  }

  function discardDraft(sessionKey = activeDraftSessionKey.value) {
    if (!sessionKey) return
    deleteTrainingLocalDraft(sessionKey)
    if (activeDraftSessionKey.value === sessionKey) {
      activeDraftSessionKey.value = ''
      _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.SYNCED)
    }
  }

  function persistLocalDraftState(uiState: DraftUiState = {}) {
    draftUiState.value = {
      activeItemId: uiState.activeItemId ?? draftUiState.value.activeItemId,
      latestSuggestion: uiState.latestSuggestion ?? draftUiState.value.latestSuggestion,
    }
    _persistLocalDraft({ ...draftUiState.value, pendingSync: draftPendingSync.value })
  }

  function _replaceSession(nextSession: any) {
    session.value = _clone(nextSession)
    activeDraftSessionKey.value = _buildSessionKey(session.value)
  }

  function _setSyncStatus(nextStatus: TrainingDraftSyncStatus) {
    syncStatus.value = nextStatus
    draftPendingSync.value = nextStatus === TRAINING_DRAFT_SYNC_STATUS.PENDING
  }

  function _buildSessionKey(targetSession: any) {
    return buildTrainingDraftSessionKey({
      athleteId: targetSession.athlete_id,
      assignmentId: targetSession.assignment_id,
      sessionDate: targetSession.session_date,
    })
  }

  function _persistLocalDraft({
    activeItemId = draftUiState.value.activeItemId,
    latestSuggestion = draftUiState.value.latestSuggestion,
    pendingSync = draftPendingSync.value,
    pendingOperations = _getPendingOperations(),
    lastServerUpdatedAt,
    lastServerSignature,
    incrementalFailureCount,
    lastSyncAttemptAt,
  }: DraftUiState & {
    pendingSync?: boolean
    pendingOperations?: TrainingDraftSyncOperation[]
    lastServerUpdatedAt?: string | null
    lastServerSignature?: string | null
    incrementalFailureCount?: number
    lastSyncAttemptAt?: string | null
  } = {}) {
    if (!session.value) return

    const existingDraft = activeDraftSessionKey.value ? loadTrainingLocalDraft(activeDraftSessionKey.value) : null
    const hasRecords = hasSessionRecordedSets(session.value)
    if (!hasRecords && !pendingSync) {
      discardDraft(_buildSessionKey(session.value))
      return
    }

    const matchingAthlete = athletes.value.find((athlete) => athlete.id === session.value.athlete_id)
    const matchingAssignment = assignments.value.find((assignment) => assignment.id === session.value.assignment_id)
    const draft = createTrainingLocalDraft({
      sessionKey: _buildSessionKey(session.value),
      session: _clone(session.value),
      athleteName: matchingAthlete?.full_name,
      templateName: matchingAssignment?.template?.name || null,
      currentItemId: activeItemId,
      latestSuggestion,
      syncStatus: pendingSync ? TRAINING_DRAFT_SYNC_STATUS.PENDING : TRAINING_DRAFT_SYNC_STATUS.SYNCED,
      pendingSync,
      lastServerUpdatedAt: lastServerUpdatedAt ?? session.value.updated_at ?? existingDraft?.last_server_updated_at ?? null,
      lastServerSignature: lastServerSignature ?? session.value.server_signature ?? existingDraft?.last_server_signature ?? null,
      incrementalFailureCount: incrementalFailureCount ?? existingDraft?.incremental_failure_count ?? 0,
      lastSyncAttemptAt: lastSyncAttemptAt ?? existingDraft?.last_sync_attempt_at ?? null,
      pendingOperations,
    })

    if (!draft.pending_sync && FINAL_SESSION_STATUSES.has(draft.session_snapshot?.status)) {
      discardDraft(draft.session_key)
      return
    }

    saveTrainingLocalDraft(draft)
    activeDraftSessionKey.value = draft.session_key
    draftUiState.value = {
      activeItemId,
      latestSuggestion,
    }
    _setSyncStatus(draft.sync_status)
  }

  function _saveSetLocally(itemId: number, payload: NormalizedSetPayload, uiState: DraftUiState) {
    if (!session.value) throw new Error('No session loaded')

    const nextSession = _clone(session.value)
    const localRecordId = -Date.now()
    const createOperation = _buildCreateSetOperation(nextSession, itemId, payload, localRecordId)
    const { item, record } = _applyCreateSetToSession(
      nextSession,
      { itemId: createOperation.session_item_id, templateItemId: createOperation.template_item_id },
      payload,
      localRecordId,
    )
    const pendingOperations = _appendPendingOperation(createOperation)

    _replaceSession(nextSession)
    _persistLocalDraft({
      ...uiState,
      pendingSync: true,
      latestSuggestion: null,
      pendingOperations,
    })
    _scheduleIncrementalSync()

    return {
      record,
      next_suggestion: null,
      item,
      session: nextSession,
      session_status: nextSession.status,
      session_completed_at: nextSession.completed_at,
      local_only: true,
    }
  }

  function _reviseSetLocally(recordId: number, payload: NormalizedSetPayload, uiState: DraftUiState) {
    if (!session.value) throw new Error('No session loaded')

    const nextSession = _clone(session.value)
    const { item: matchedItem, record: matchedRecord } = _applyUpdateSetToSession(nextSession, recordId, payload)
    const pendingOperations = _queueUpdateOperation(nextSession, matchedRecord.id, payload)

    _replaceSession(nextSession)
    _persistLocalDraft({
      ...uiState,
      pendingSync: true,
      latestSuggestion: null,
      pendingOperations,
    })
    _scheduleIncrementalSync()

    return {
      record: matchedRecord,
      next_suggestion: null,
      item: matchedItem,
      session: nextSession,
      session_status: nextSession.status,
      session_completed_at: nextSession.completed_at,
      local_only: true,
    }
  }

  function _endSessionLocally(uiState: DraftUiState) {
    if (!session.value) throw new Error('No session loaded')

    const nextSession = _clone(session.value)
    _finalizeLocalSession(nextSession)
    const pendingOperations = _queueCompleteSessionOperation(nextSession)

    _replaceSession(nextSession)
    _persistLocalDraft({
      ...uiState,
      latestSuggestion: null,
      pendingSync: true,
      pendingOperations,
    })
    _scheduleIncrementalSync()

    return {
      ...nextSession,
      local_only: true,
    }
  }

  function _normalizeSetPayload(payload: Record<string, unknown>): NormalizedSetPayload {
    return {
      actual_weight: Number(payload.actual_weight),
      actual_reps: Number(payload.actual_reps),
      actual_rir: Number(payload.actual_rir),
      final_weight: Number(payload.final_weight ?? payload.actual_weight),
      notes: (payload.notes as string | null | undefined) ?? null,
    }
  }

  function _resolveSessionItem(targetSession: any, itemId?: number | null, templateItemId?: number | null) {
    const items = targetSession.items || []
    return (
      items.find((entry: any) => entry.id === itemId)
      || items.find((entry: any) => entry.template_item_id === templateItemId)
      || null
    )
  }

  function _buildCreateSetOperation(
    targetSession: any,
    itemId: number,
    payload: NormalizedSetPayload,
    localRecordId: number | null = null,
  ): CreateSetOperation {
    const item = _resolveSessionItem(targetSession, itemId, itemId)
    if (!item) throw new Error('Session item not found')

    return createCreateSetSyncOperation({
      assignmentId: targetSession.assignment_id,
      sessionDate: targetSession.session_date,
      sessionId: targetSession.id ?? null,
      templateItemId: item.template_item_id,
      sessionItemId: targetSession.id ? item.id : null,
      localRecordId: localRecordId ?? 0,
      payload,
    }) as CreateSetOperation
  }

  function _buildUpdateSetOperation(targetSession: any, recordId: number, payload: NormalizedSetPayload): UpdateSetOperation {
    return createUpdateSetSyncOperation({
      sessionId: targetSession.id ?? null,
      recordId,
      payload,
    }) as UpdateSetOperation
  }

  function _applyCreateSetToSession(
    targetSession: any,
    itemLocator: { itemId?: number | null; templateItemId?: number | null },
    payload: NormalizedSetPayload,
    localRecordId: number,
  ) {
    const item = _resolveSessionItem(targetSession, itemLocator.itemId, itemLocator.templateItemId)
    if (!item) throw new Error('Session item not found')

    const previousRecord = item.records?.[item.records.length - 1] || null
    const nextSetNumber = (item.records?.length || 0) + 1
    const completedAt = new Date().toISOString()
    const record = {
      id: localRecordId,
      set_number: nextSetNumber,
      target_weight: previousRecord?.final_weight ?? item.initial_load ?? null,
      target_reps: item.prescribed_reps,
      actual_weight: payload.actual_weight,
      actual_reps: payload.actual_reps,
      actual_rir: payload.actual_rir,
      suggestion_weight: null,
      suggestion_reason: null,
      user_decision: 'accepted',
      final_weight: payload.final_weight,
      completed_at: completedAt,
      notes: payload.notes,
    }

    item.records = [...(item.records || []), record]
    _recomputeLocalSessionState(targetSession, completedAt)
    return { item, record }
  }

  function _applyUpdateSetToSession(targetSession: any, recordId: number, payload: NormalizedSetPayload) {
    let matchedItem: any = null
    let matchedRecord: any = null

    for (const item of targetSession.items || []) {
      const record = item.records?.find((entry: any) => entry.id === recordId)
      if (!record) continue
      matchedItem = item
      matchedRecord = record
      break
    }

    if (!matchedItem || !matchedRecord) throw new Error('Set record not found')

    matchedRecord.actual_weight = payload.actual_weight
    matchedRecord.actual_reps = payload.actual_reps
    matchedRecord.actual_rir = payload.actual_rir
    matchedRecord.final_weight = payload.final_weight
    matchedRecord.notes = payload.notes
    matchedRecord.completed_at = new Date().toISOString()

    _recomputeLocalSessionState(targetSession, matchedRecord.completed_at)
    return { item: matchedItem, record: matchedRecord }
  }

  function _recomputeLocalSessionState(targetSession: any, fallbackTimestamp: string) {
    const items = targetSession.items || []
    let totalRecords = 0

    for (const item of items) {
      const recordCount = item.records?.length || 0
      totalRecords += recordCount
      if (recordCount === 0) {
        item.status = 'pending'
      } else if (recordCount >= item.prescribed_sets) {
        item.status = 'completed'
      } else {
        item.status = IN_PROGRESS_SESSION_STATUS
      }
    }

    if (!items.length || totalRecords === 0) {
      targetSession.status = NOT_STARTED_SESSION_STATUS
      targetSession.started_at = null
      targetSession.completed_at = null
      return
    }

    const sessionCompleted = items.every((entry: any) => (entry.records?.length || 0) >= entry.prescribed_sets)
    targetSession.status = sessionCompleted ? 'completed' : IN_PROGRESS_SESSION_STATUS
    targetSession.started_at = targetSession.started_at || _getFirstRecordedAt(items) || fallbackTimestamp
    targetSession.completed_at = sessionCompleted ? targetSession.completed_at || fallbackTimestamp : null
  }

  function _finalizeLocalSession(targetSession: any) {
    const items = targetSession.items || []
    for (const item of items) {
      const recordCount = item.records?.length || 0
      if (recordCount === 0) {
        item.status = 'pending'
      } else if (recordCount >= item.prescribed_sets) {
        item.status = 'completed'
      } else {
        item.status = IN_PROGRESS_SESSION_STATUS
      }
    }

    const totalRecords = items.reduce((total: number, item: any) => total + (item.records?.length || 0), 0)
    const allCompleted = !!items.length && items.every((item: any) => item.status === 'completed')
    targetSession.status = allCompleted ? 'completed' : 'partial_complete'
    targetSession.started_at = totalRecords > 0 ? targetSession.started_at || _getFirstRecordedAt(items) : null
    targetSession.completed_at = new Date().toISOString()
  }

  function _getFirstRecordedAt(items: any[]) {
    const completedAts = items
      .flatMap((item: any) => item.records || [])
      .map((record: any) => record.completed_at)
      .filter(Boolean)
      .sort()
    return completedAts[0] || null
  }

  function _appendPendingOperation(operation: TrainingDraftSyncOperation) {
    const existingOperations = _getPendingOperations()
    return [...existingOperations, operation]
  }

  function _queueUpdateOperation(targetSession: any, recordId: number, payload: NormalizedSetPayload) {
    const existingOperations = _getPendingOperations()
    const nextOperations = [...existingOperations]
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
    const updateOperation = _buildUpdateSetOperation(targetSession, recordId, payload)
    if (pendingUpdateIndex >= 0) {
      nextOperations[pendingUpdateIndex] = updateOperation
      return nextOperations
    }
    return [...nextOperations, updateOperation]
  }

  function _queueCompleteSessionOperation(targetSession: any) {
    const filteredOperations = _getPendingOperations().filter((operation) => operation.operation_type !== 'complete_session')
    return [
      ...filteredOperations,
      createCompleteSessionSyncOperation({
        assignmentId: targetSession.assignment_id,
        sessionDate: targetSession.session_date,
        sessionId: targetSession.id ?? null,
      }),
    ]
  }

  function _getPendingOperations() {
    if (!activeDraftSessionKey.value) return [] as TrainingDraftSyncOperation[]
    const draft = loadTrainingLocalDraft(activeDraftSessionKey.value)
    return draft?.pending_operations || []
  }

  function _scheduleIncrementalSync(delayMs = SYNC_RETRY_IDLE_MS) {
    if (typeof window === 'undefined') return
    if (!activeDraftSessionKey.value) return
    if (syncRetryTimer !== null) {
      window.clearTimeout(syncRetryTimer)
    }
    syncRetryTimer = window.setTimeout(() => {
      syncRetryTimer = null
      void syncPendingOperations()
    }, delayMs)
  }

  async function syncSessionSnapshot(triggerReason: 'manual' | 'fallback' = 'manual') {
    if (syncInFlight || !activeDraftSessionKey.value) return null

    const draft = loadTrainingLocalDraft(activeDraftSessionKey.value)
    if (!draft?.pending_operations?.length || !draft.session_snapshot) return null

    syncInFlight = true
    try {
      const response = await syncTrainingSessionSnapshot(_buildFullSessionSyncPayload(draft, triggerReason))
      _replaceSession(response.session)
      _persistLocalDraft({
        ...draftUiState.value,
        latestSuggestion: null,
        pendingSync: false,
        pendingOperations: [],
        lastServerUpdatedAt: response.session.updated_at ?? null,
        lastServerSignature: response.session.server_signature ?? null,
        incrementalFailureCount: 0,
        lastSyncAttemptAt: new Date().toISOString(),
      })
      _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.SYNCED)
      await hydrateAthletes(sessionDate.value)
      return response
    } catch {
      _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.PENDING)
      _persistLocalDraft({
        ...draftUiState.value,
        pendingSync: true,
        incrementalFailureCount: Math.max(draft.incremental_failure_count, FULL_SYNC_FAILURE_THRESHOLD),
        lastSyncAttemptAt: new Date().toISOString(),
      })
      _scheduleIncrementalSync(SYNC_RETRY_DELAY_MS)
      return null
    } finally {
      syncInFlight = false
    }
  }

  function requestFullSessionSync() {
    return syncSessionSnapshot('manual')
  }

  async function syncPendingOperations() {
    if (syncInFlight || !activeDraftSessionKey.value) return

    const draft = loadTrainingLocalDraft(activeDraftSessionKey.value)
    if (!draft?.pending_operations?.length) {
      _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.SYNCED)
      return
    }

    if (draft.incremental_failure_count >= FULL_SYNC_FAILURE_THRESHOLD) {
      await syncSessionSnapshot('fallback')
      return
    }

    syncInFlight = true
    let syncedAnyOperation = false
    try {
      let pendingOperations = [...draft.pending_operations]
      while (pendingOperations.length) {
        const operation = pendingOperations[0]
        const response = await syncTrainingSetOperation(_toSessionSyncOperationPayload(operation))
        syncedAnyOperation = true
        pendingOperations = pendingOperations.slice(1)
        pendingOperations = _bindPendingOperationsToSession(response.session, pendingOperations)

        if (operation.operation_type === 'create_set' && operation.local_record_id && response.record) {
          const pendingLocalRecord = _findRecordInSession(session.value, operation.local_record_id)
          if (pendingLocalRecord && _recordNeedsFollowUpUpdate(pendingLocalRecord, response.record)) {
            pendingOperations = _queueFollowUpUpdateOperation(
              pendingOperations,
              response.session.id,
              response.record.id,
              pendingLocalRecord,
            )
          }
        }

        const rebuiltSession = _replayPendingOperations(response.session, pendingOperations)
        _replaceSession(rebuiltSession)
        _persistLocalDraft({
          ...draftUiState.value,
          pendingSync: pendingOperations.length > 0,
          pendingOperations,
          lastServerUpdatedAt: response.session.updated_at ?? null,
          lastServerSignature: response.session.server_signature ?? null,
          incrementalFailureCount: 0,
          lastSyncAttemptAt: new Date().toISOString(),
        })
      }

      _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.SYNCED)
      await hydrateAthletes(sessionDate.value)
    } catch {
      const nextFailureCount = (draft.incremental_failure_count || 0) + 1
      _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.PENDING)
      _persistLocalDraft({
        ...draftUiState.value,
        pendingSync: true,
        incrementalFailureCount: nextFailureCount,
        lastSyncAttemptAt: new Date().toISOString(),
      })
      _scheduleIncrementalSync(SYNC_RETRY_DELAY_MS)
    } finally {
      syncInFlight = false
      if (syncedAnyOperation) {
        _persistLocalDraft({
          ...draftUiState.value,
          pendingSync: draftPendingSync.value,
          incrementalFailureCount: 0,
        })
      }
    }
  }

  function _bindPendingOperationsToSession(nextSession: any, pendingOperations: TrainingDraftSyncOperation[]) {
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

  function _toSessionSyncOperationPayload(operation: TrainingDraftSyncOperation): SessionSyncOperation {
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

  function _buildFullSessionSyncPayload(draft: TrainingLocalDraft, triggerReason: 'manual' | 'fallback'): FullSessionSyncPayload {
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

  function _replayPendingOperations(baseSession: any, pendingOperations: TrainingDraftSyncOperation[]) {
    const nextSession = _clone(baseSession)
    for (const operation of pendingOperations) {
      if (operation.operation_type === 'create_set') {
        _applyCreateSetToSession(
          nextSession,
          { itemId: operation.session_item_id, templateItemId: operation.template_item_id },
          operation.payload,
          operation.local_record_id,
        )
        continue
      }

      if (operation.operation_type === 'update_set') {
        _applyUpdateSetToSession(nextSession, operation.record_id, operation.payload)
        continue
      }

      _finalizeLocalSession(nextSession)
    }
    return nextSession
  }

  function _findRecordInSession(targetSession: any, recordId: number) {
    if (!targetSession?.items?.length) return null
    for (const item of targetSession.items) {
      const record = item.records?.find((entry: any) => entry.id === recordId)
      if (record) return record
    }
    return null
  }

  function _recordNeedsFollowUpUpdate(localRecord: any, syncedRecord: any) {
    return (
      Number(localRecord.actual_weight) !== Number(syncedRecord.actual_weight)
      || Number(localRecord.actual_reps) !== Number(syncedRecord.actual_reps)
      || Number(localRecord.actual_rir) !== Number(syncedRecord.actual_rir)
      || Number(localRecord.final_weight) !== Number(syncedRecord.final_weight)
      || (localRecord.notes || null) !== (syncedRecord.notes || null)
    )
  }

  function _queueFollowUpUpdateOperation(
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

  function _clone<T>(value: T): T {
    return JSON.parse(JSON.stringify(value))
  }

  return {
    athletes,
    selectedAthleteId,
    sessionDate,
    assignments,
    previewAssignmentId,
    session,
    activeDraftSessionKey,
    draftPendingSync,
    syncStatus,
    hydrateAthletes,
    loadPlans,
    openPlanSession,
    loadSession,
    recordSet,
    reviseSetRecord,
    endSession,
    setPreviewAssignment,
    getDraftForSession,
    getDraftBySessionId,
    getDraftByContext,
    restoreDraft,
    discardDraft,
    persistLocalDraftState,
    syncPendingOperations,
    requestFullSessionSync,
  }
})
