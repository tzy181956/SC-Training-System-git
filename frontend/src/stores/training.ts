import { defineStore } from 'pinia'
import { ref } from 'vue'

import {
  completeTrainingSession,
  fetchSession,
  fetchTrainingAthletes,
  fetchTrainingPlans,
  fetchTrainingSyncIssues,
  reportTrainingSyncIssue,
  resolveTrainingSyncIssue,
  submitTrainingSessionFinishFeedback,
  syncTrainingSessionSnapshot,
  syncTrainingSetOperation,
  startTrainingSession,
  type SessionFinishFeedbackPayload,
} from '@/api/sessions'
import {
  classifyTrainingDraftAgainstRemote,
  deleteTrainingLocalDraft,
  type DraftRemoteRelation,
  findTrainingLocalDraftBySessionId,
  isRecoverableTrainingDraft,
  listTrainingLocalDrafts,
  loadTrainingLocalDraft,
  TRAINING_DRAFT_SYNC_STATUS,
  type TrainingManualRetryReason,
  type TrainingDraftSetPayload,
  type TrainingDraftSyncOperation,
  type TrainingDraftSyncStatus,
  type TrainingLocalDraft,
} from '@/utils/trainingDraft'
import { TRAINING_SYNC_CONFLICT_SUMMARY } from '@/constants/trainingSync'
import {
  appendPendingTrainingOperation,
  bindPendingOperationsToSession,
  buildCreateSetOperation,
  buildTrainingFullSessionSyncPayload,
  buildTrainingManualRetrySummary,
  buildTrainingSessionKey,
  buildUpdateSetOperation,
  extractTrainingSyncErrorMessage,
  findPendingTrainingRecord,
  getPendingTrainingOperations,
  getPendingTrainingSyncStatus,
  persistTrainingLocalDraftState,
  queueFollowUpTrainingUpdateOperation,
  queuePendingTrainingCompletionOperation,
  queuePendingTrainingUpdateOperation,
  recordNeedsFollowUpUpdate,
  replayPendingTrainingOperations,
  toSessionSyncOperationPayload,
  type DraftUiState,
} from '@/services/trainingDraftSync'
import {
  applyCreateSetToLocalSession,
  applyUpdateSetToLocalSession,
  cloneTrainingSession,
  finalizeLocalSession,
} from '@/utils/trainingSessionState'

const SYNC_RETRY_DELAY_MS = 4000
const SYNC_RETRY_IDLE_MS = 1200
const FULL_SYNC_FAILURE_THRESHOLD = 3
const ATHLETE_NAME_COLLATOR = new Intl.Collator(['zh-Hans-CN-u-co-pinyin', 'en'], {
  numeric: true,
  sensitivity: 'base',
})

type NormalizedSetPayload = TrainingDraftSetPayload

export const useTrainingStore = defineStore('training', () => {
  const athletes = ref<any[]>([])
  const selectedAthleteId = ref<number>(0)
  const sessionDate = ref<string>('')
  const assignments = ref<any[]>([])
  const previewAssignmentId = ref<number>(0)
  const session = ref<any | null>(null)
  const activeDraftSessionKey = ref<string>('')
  const draftPendingSync = ref(false)
  const syncIssueId = ref<number | null>(null)
  const syncStatus = ref<TrainingDraftSyncStatus>(TRAINING_DRAFT_SYNC_STATUS.SYNCED)
  const manualRetryReason = ref<TrainingManualRetryReason | null>(null)
  const draftUiState = ref<{ activeItemId: number | null; latestSuggestion: any | null }>({
    activeItemId: null,
    latestSuggestion: null,
  })
  let syncRetryTimer: number | null = null
  let syncInFlight = false

  if (typeof window !== 'undefined') {
    window.addEventListener('online', () => {
      if (syncStatus.value === TRAINING_DRAFT_SYNC_STATUS.MANUAL_REQUIRED) {
        void _reconcileManualSyncState()
        return
      }
      _scheduleIncrementalSync(300)
    })
  }

  async function hydrateAthletes(targetDate = sessionDate.value) {
    athletes.value = _sortTrainingAthletes(await fetchTrainingAthletes(targetDate))
    const selectedStillExists = athletes.value.some((athlete) => athlete.id === selectedAthleteId.value)
    if (!selectedStillExists) {
      selectedAthleteId.value = athletes.value[0]?.id || 0
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
    activeDraftSessionKey.value = buildTrainingSessionKey(session.value)
    syncIssueId.value = null
    manualRetryReason.value = null
    _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.SYNCED)
    return session.value
  }

  async function loadSession(sessionId: number) {
    session.value = await fetchSession(sessionId)
    activeDraftSessionKey.value = buildTrainingSessionKey(session.value)
    syncIssueId.value = null
    manualRetryReason.value = null
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
        toSessionSyncOperationPayload(buildCreateSetOperation(session.value, itemId, normalizedPayload)),
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
        toSessionSyncOperationPayload(buildUpdateSetOperation(session.value, recordId, normalizedPayload)),
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

  async function submitSessionFinishFeedback(payload: SessionFinishFeedbackPayload) {
    if (!session.value?.id) throw new Error('No persisted session loaded')

    const nextSession = await submitTrainingSessionFinishFeedback(session.value.id, payload)
    _replaceSession(nextSession)
    _persistLocalDraft({
      ...draftUiState.value,
      pendingSync: draftPendingSync.value,
      syncStatus: syncStatus.value,
      syncIssueId: syncIssueId.value,
      lastServerUpdatedAt: nextSession.updated_at ?? null,
      lastServerSignature: nextSession.server_signature ?? null,
      incrementalFailureCount: 0,
      lastSyncAttemptAt: new Date().toISOString(),
    })
    await hydrateAthletes(sessionDate.value)
    return nextSession
  }

  function setPreviewAssignment(assignmentId: number) {
    previewAssignmentId.value = assignmentId
  }

  function getDraftForSession(targetSession = session.value) {
    if (!targetSession) return null
    const sessionKey = buildTrainingSessionKey(targetSession)
    return loadTrainingLocalDraft(sessionKey)
  }

  function getDraftBySessionId(sessionId: number) {
    const draft = findTrainingLocalDraftBySessionId(sessionId)
    return isRecoverableTrainingDraft(draft) ? draft : null
  }

  function getDraftByContext(athleteId: number, assignmentId: number, targetDate: string) {
    const sessionKey = buildTrainingSessionKey({
      athlete_id: athleteId,
      assignment_id: assignmentId,
      session_date: targetDate,
    })
    const draft = loadTrainingLocalDraft(sessionKey)
    return isRecoverableTrainingDraft(draft) ? draft : null
  }

  function getDraftBySessionKey(sessionKey: string) {
    if (!sessionKey) return null
    const draft = loadTrainingLocalDraft(sessionKey)
    return isRecoverableTrainingDraft(draft) ? draft : null
  }

  function getLatestRecoverableDraft() {
    return listTrainingLocalDrafts().find((draft) => isRecoverableTrainingDraft(draft)) || null
  }

  function restoreDraft(draft: TrainingLocalDraft) {
    session.value = cloneTrainingSession(draft.session_snapshot)
    selectedAthleteId.value = draft.athlete_id
    sessionDate.value = draft.session_date
    previewAssignmentId.value = draft.assignment_id
    activeDraftSessionKey.value = draft.session_key
    syncIssueId.value = draft.sync_issue_id ?? null
    manualRetryReason.value = draft.manual_retry_reason ?? null
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
      _clearScheduledSyncRetry()
      activeDraftSessionKey.value = ''
      syncIssueId.value = null
      manualRetryReason.value = null
      _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.SYNCED)
    }
  }

  function persistLocalDraftState(uiState: DraftUiState = {}) {
    draftUiState.value = {
      activeItemId: uiState.activeItemId ?? draftUiState.value.activeItemId,
      latestSuggestion: uiState.latestSuggestion ?? draftUiState.value.latestSuggestion,
    }
    _persistLocalDraft({
      ...draftUiState.value,
      pendingSync: draftPendingSync.value,
      syncStatus: syncStatus.value,
      syncIssueId: syncIssueId.value,
    })
  }

  function _replaceSession(nextSession: any) {
    session.value = cloneTrainingSession(nextSession)
    activeDraftSessionKey.value = buildTrainingSessionKey(session.value)
  }

  function replaceSessionFromRemote(nextSession: any, uiState: DraftUiState = {}) {
    _replaceSession(nextSession)
    selectedAthleteId.value = nextSession.athlete_id
    sessionDate.value = nextSession.session_date
    previewAssignmentId.value = nextSession.assignment_id
    syncIssueId.value = null
    manualRetryReason.value = null
    _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.SYNCED)
    _persistLocalDraft({
      ...uiState,
      pendingSync: false,
      pendingOperations: [],
      syncStatus: TRAINING_DRAFT_SYNC_STATUS.SYNCED,
      syncIssueId: null,
      manualRetryReason: null,
      lastServerUpdatedAt: nextSession.updated_at ?? null,
      lastServerSignature: nextSession.server_signature ?? null,
      incrementalFailureCount: 0,
      lastSyncAttemptAt: new Date().toISOString(),
    })
    return session.value
  }

  function classifyDraftRelation(targetSession: any): DraftRemoteRelation | null {
    return classifyTrainingDraftAgainstRemote(getDraftForSession(targetSession), targetSession)
  }

  function _setSyncStatus(nextStatus: TrainingDraftSyncStatus) {
    syncStatus.value = nextStatus
    draftPendingSync.value = nextStatus !== TRAINING_DRAFT_SYNC_STATUS.SYNCED
  }

  function _sortTrainingAthletes(nextAthletes: any[]) {
    return [...nextAthletes].sort((left, right) => {
      const leftHasPlan = Array.isArray(left.assignments) && left.assignments.length > 0
      const rightHasPlan = Array.isArray(right.assignments) && right.assignments.length > 0

      if (leftHasPlan !== rightHasPlan) {
        return leftHasPlan ? -1 : 1
      }

      const leftName = String(left.full_name || '').trim()
      const rightName = String(right.full_name || '').trim()
      const nameCompare = ATHLETE_NAME_COLLATOR.compare(leftName, rightName)
      if (nameCompare !== 0) {
        return nameCompare
      }

      return Number(left.id || 0) - Number(right.id || 0)
    })
  }

  function _persistLocalDraft({
    activeItemId = draftUiState.value.activeItemId,
    latestSuggestion = draftUiState.value.latestSuggestion,
    pendingSync = draftPendingSync.value,
    pendingOperations = getPendingTrainingOperations(activeDraftSessionKey.value),
    lastServerUpdatedAt,
    lastServerSignature,
    incrementalFailureCount,
    lastSyncAttemptAt,
    syncStatus: nextSyncStatus,
    syncIssueId: nextSyncIssueId,
    manualRetryReason: nextManualRetryReason,
  }: DraftUiState & {
    pendingSync?: boolean
    pendingOperations?: TrainingDraftSyncOperation[]
    lastServerUpdatedAt?: string | null
    lastServerSignature?: string | null
    incrementalFailureCount?: number
    lastSyncAttemptAt?: string | null
    syncStatus?: TrainingDraftSyncStatus
    syncIssueId?: number | null
    manualRetryReason?: TrainingManualRetryReason | null
  } = {}) {
    const result = persistTrainingLocalDraftState({
      session: session.value,
      athletes: athletes.value,
      assignments: assignments.value,
      activeDraftSessionKey: activeDraftSessionKey.value,
      draftPendingSync: draftPendingSync.value,
      draftUiState: draftUiState.value,
      syncIssueId: syncIssueId.value,
      options: {
        activeItemId,
        latestSuggestion,
        pendingSync,
        pendingOperations,
        lastServerUpdatedAt,
        lastServerSignature,
        incrementalFailureCount,
        lastSyncAttemptAt,
        syncStatus: nextSyncStatus,
        syncIssueId: nextSyncIssueId,
        manualRetryReason: nextManualRetryReason,
      },
    })
    draftUiState.value = result.draftUiState
    if (result.action === 'discarded' && result.sessionKey && activeDraftSessionKey.value === result.sessionKey) {
      _clearScheduledSyncRetry()
      activeDraftSessionKey.value = ''
      syncIssueId.value = null
      _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.SYNCED)
      return
    }
    if (result.action !== 'saved' || !result.draft) {
      return
    }
    activeDraftSessionKey.value = result.draft.session_key
    syncIssueId.value = result.draft.sync_issue_id
    manualRetryReason.value = result.draft.manual_retry_reason ?? null
    _setSyncStatus(result.draft.sync_status)
  }

  function _saveSetLocally(itemId: number, payload: NormalizedSetPayload, uiState: DraftUiState) {
    if (!session.value) throw new Error('No session loaded')

    const nextSession = cloneTrainingSession(session.value)
    const localRecordId = -Date.now()
    const createOperation = buildCreateSetOperation(nextSession, itemId, payload, localRecordId)
    const { item, record } = applyCreateSetToLocalSession(
      nextSession,
      { itemId: createOperation.session_item_id, templateItemId: createOperation.template_item_id },
      payload,
      localRecordId,
      new Date().toISOString(),
    )
    const pendingOperations = appendPendingTrainingOperation(activeDraftSessionKey.value, createOperation)

    _replaceSession(nextSession)
    _persistLocalDraft({
      ...uiState,
      pendingSync: true,
      syncStatus: getPendingTrainingSyncStatus(syncStatus.value),
      syncIssueId: syncIssueId.value,
      latestSuggestion: null,
      pendingOperations,
    })
    if (syncStatus.value === TRAINING_DRAFT_SYNC_STATUS.MANUAL_REQUIRED) {
      void _refreshManualSyncIssue()
    } else {
      _scheduleIncrementalSync()
    }

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

    const nextSession = cloneTrainingSession(session.value)
    const { item: matchedItem, record: matchedRecord } = applyUpdateSetToLocalSession(
      nextSession,
      recordId,
      payload,
      new Date().toISOString(),
    )
    const pendingOperations = queuePendingTrainingUpdateOperation({
      sessionKey: activeDraftSessionKey.value,
      targetSession: nextSession,
      recordId: matchedRecord.id,
      payload,
    })

    _replaceSession(nextSession)
    _persistLocalDraft({
      ...uiState,
      pendingSync: true,
      syncStatus: getPendingTrainingSyncStatus(syncStatus.value),
      syncIssueId: syncIssueId.value,
      latestSuggestion: null,
      pendingOperations,
    })
    if (syncStatus.value === TRAINING_DRAFT_SYNC_STATUS.MANUAL_REQUIRED) {
      void _refreshManualSyncIssue()
    } else {
      _scheduleIncrementalSync()
    }

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

    const nextSession = cloneTrainingSession(session.value)
    finalizeLocalSession(nextSession, new Date().toISOString())
    const pendingOperations = queuePendingTrainingCompletionOperation(activeDraftSessionKey.value, nextSession)

    _replaceSession(nextSession)
    _persistLocalDraft({
      ...uiState,
      latestSuggestion: null,
      pendingSync: true,
      syncStatus: getPendingTrainingSyncStatus(syncStatus.value),
      syncIssueId: syncIssueId.value,
      pendingOperations,
    })
    if (syncStatus.value === TRAINING_DRAFT_SYNC_STATUS.MANUAL_REQUIRED) {
      void _refreshManualSyncIssue()
    } else {
      _scheduleIncrementalSync()
    }

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
  function _scheduleIncrementalSync(delayMs = SYNC_RETRY_IDLE_MS) {
    if (typeof window === 'undefined') return
    if (!activeDraftSessionKey.value) return
    if (syncStatus.value === TRAINING_DRAFT_SYNC_STATUS.MANUAL_REQUIRED) return
    if (syncRetryTimer !== null) {
      window.clearTimeout(syncRetryTimer)
    }
    syncRetryTimer = window.setTimeout(() => {
      syncRetryTimer = null
      void syncPendingOperations()
    }, delayMs)
  }

  function _clearScheduledSyncRetry() {
    if (typeof window === 'undefined') return
    if (syncRetryTimer !== null) {
      window.clearTimeout(syncRetryTimer)
      syncRetryTimer = null
    }
  }

  async function _resolveSyncIssueIfNeeded(issueId = syncIssueId.value) {
    if (!issueId) return
    try {
      await resolveTrainingSyncIssue(issueId)
      syncIssueId.value = null
    } catch {
      // Keep local training flow uninterrupted even if clearing the issue flag fails.
    }
  }

  async function _refreshManualSyncIssue() {
    if (!activeDraftSessionKey.value) return null
    const draft = loadTrainingLocalDraft(activeDraftSessionKey.value)
    if (!draft?.session_snapshot || syncStatus.value !== TRAINING_DRAFT_SYNC_STATUS.MANUAL_REQUIRED) {
      return null
    }

    try {
      const issue = await reportTrainingSyncIssue({
        session_key: draft.session_key,
        athlete_id: draft.athlete_id,
        assignment_id: draft.assignment_id,
        session_id: session.value?.id ?? draft.session_id ?? null,
        session_date: draft.session_date,
        failure_count: Math.max(draft.incremental_failure_count, FULL_SYNC_FAILURE_THRESHOLD),
        summary:
          draft.manual_retry_reason === 'conflict'
            ? TRAINING_SYNC_CONFLICT_SUMMARY
            : draft.sync_issue_id
            ? '人工处理中的同步异常仍未关闭，最新本地草稿快照已刷新。'
            : '自动重试已停止，最新本地草稿快照正等待教练或管理员手动补传。',
        last_error: null,
        sync_payload: buildTrainingFullSessionSyncPayload(
          {
            ...draft,
            session_id: session.value?.id ?? draft.session_id ?? null,
            session_snapshot: cloneTrainingSession(session.value ?? draft.session_snapshot),
          },
          'manual',
        ),
      })
      syncIssueId.value = issue.id
      _persistLocalDraft({
        ...draftUiState.value,
        pendingSync: true,
        syncStatus: TRAINING_DRAFT_SYNC_STATUS.MANUAL_REQUIRED,
        syncIssueId: issue.id,
        manualRetryReason: draft.manual_retry_reason ?? manualRetryReason.value,
        incrementalFailureCount: Math.max(draft.incremental_failure_count, FULL_SYNC_FAILURE_THRESHOLD),
      })
      return issue
    } catch {
      return null
    }
  }

  async function _reconcileManualSyncState() {
    if (!session.value || syncStatus.value !== TRAINING_DRAFT_SYNC_STATUS.MANUAL_REQUIRED) return

    if (!syncIssueId.value) {
      await _refreshManualSyncIssue()
      return
    }

    try {
      const openIssues = await fetchTrainingSyncIssues({
        athlete_id: session.value.athlete_id,
        date_from: session.value.session_date,
        date_to: session.value.session_date,
        issue_status: 'manual_retry_required',
      })
      const stillOpen = openIssues.some((issue) => issue.id === syncIssueId.value)
      if (stillOpen) {
        await _refreshManualSyncIssue()
        return
      }

      const nextSession = session.value.id
        ? await fetchSession(session.value.id)
        : await startTrainingSession(session.value.assignment_id, session.value.session_date)
      _replaceSession(nextSession)
      _persistLocalDraft({
        ...draftUiState.value,
        latestSuggestion: null,
        pendingSync: false,
        pendingOperations: [],
        syncStatus: TRAINING_DRAFT_SYNC_STATUS.SYNCED,
        syncIssueId: null,
        manualRetryReason: null,
        lastServerUpdatedAt: nextSession.updated_at ?? null,
        lastServerSignature: nextSession.server_signature ?? null,
        incrementalFailureCount: 0,
        lastSyncAttemptAt: new Date().toISOString(),
      })
      _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.SYNCED)
      manualRetryReason.value = null
      await hydrateAthletes(sessionDate.value)
    } catch {
      // Device-side reconciliation stays best-effort and must not block training.
    }
  }

  async function _markManualRetryRequired(
    draft: TrainingLocalDraft,
    triggerReason: 'manual' | 'fallback',
    error: unknown,
  ) {
    _clearScheduledSyncRetry()

    let nextIssueId = draft.sync_issue_id ?? syncIssueId.value ?? null
    try {
      const issue = await reportTrainingSyncIssue({
        session_key: draft.session_key,
        athlete_id: draft.athlete_id,
        assignment_id: draft.assignment_id,
        session_id: session.value?.id ?? draft.session_id ?? null,
        session_date: draft.session_date,
        failure_count: Math.max(draft.incremental_failure_count, FULL_SYNC_FAILURE_THRESHOLD),
        summary: buildTrainingManualRetrySummary(triggerReason),
        last_error: extractTrainingSyncErrorMessage(error),
        sync_payload: buildTrainingFullSessionSyncPayload(
          {
            ...draft,
            session_id: session.value?.id ?? draft.session_id ?? null,
            session_snapshot: cloneTrainingSession(session.value ?? draft.session_snapshot),
          },
          triggerReason,
        ),
      })
      nextIssueId = issue.id
    } catch {
      // Reporting the issue is best-effort. Local draft remains the source of truth either way.
    }

    _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.MANUAL_REQUIRED)
    manualRetryReason.value = 'retry_failed'
    _persistLocalDraft({
      ...draftUiState.value,
      pendingSync: true,
      syncStatus: TRAINING_DRAFT_SYNC_STATUS.MANUAL_REQUIRED,
      syncIssueId: nextIssueId,
      manualRetryReason: 'retry_failed',
      incrementalFailureCount: Math.max(draft.incremental_failure_count, FULL_SYNC_FAILURE_THRESHOLD),
      lastSyncAttemptAt: new Date().toISOString(),
    })
  }

  async function handoffConflictToCoach(draft: TrainingLocalDraft) {
    _clearScheduledSyncRetry()

    let nextIssueId = draft.sync_issue_id ?? syncIssueId.value ?? null
    try {
      const issue = await reportTrainingSyncIssue({
        session_key: draft.session_key,
        athlete_id: draft.athlete_id,
        assignment_id: draft.assignment_id,
        session_id: session.value?.id ?? draft.session_id ?? null,
        session_date: draft.session_date,
        failure_count: Math.max(draft.incremental_failure_count, FULL_SYNC_FAILURE_THRESHOLD),
        summary: TRAINING_SYNC_CONFLICT_SUMMARY,
        last_error: '检测到服务器端在本地最后确认同步后已更新，当前设备已暂停自动覆盖。',
        sync_payload: buildTrainingFullSessionSyncPayload(
          {
            ...draft,
            session_id: session.value?.id ?? draft.session_id ?? null,
            session_snapshot: cloneTrainingSession(session.value ?? draft.session_snapshot),
            manual_retry_reason: 'conflict',
          },
          'manual',
        ),
      })
      nextIssueId = issue.id
    } catch {
      // Handoff is best-effort. Device-side recording remains local-first.
    }

    _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.MANUAL_REQUIRED)
    manualRetryReason.value = 'conflict'
    _persistLocalDraft({
      ...draftUiState.value,
      pendingSync: true,
      syncStatus: TRAINING_DRAFT_SYNC_STATUS.MANUAL_REQUIRED,
      syncIssueId: nextIssueId,
      manualRetryReason: 'conflict',
      incrementalFailureCount: Math.max(draft.incremental_failure_count, FULL_SYNC_FAILURE_THRESHOLD),
      lastSyncAttemptAt: new Date().toISOString(),
    })
  }

  async function syncSessionSnapshot(triggerReason: 'manual' | 'fallback' = 'manual') {
    if (syncInFlight || !activeDraftSessionKey.value) return null

    const draft = loadTrainingLocalDraft(activeDraftSessionKey.value)
    if (!draft?.pending_operations?.length || !draft.session_snapshot) return null

    syncInFlight = true
    try {
      const response = await syncTrainingSessionSnapshot(buildTrainingFullSessionSyncPayload(draft, triggerReason))
      _replaceSession(response.session)
      _persistLocalDraft({
        ...draftUiState.value,
        latestSuggestion: null,
        pendingSync: false,
        pendingOperations: [],
        syncStatus: TRAINING_DRAFT_SYNC_STATUS.SYNCED,
        syncIssueId: null,
        manualRetryReason: null,
        lastServerUpdatedAt: response.session.updated_at ?? null,
        lastServerSignature: response.session.server_signature ?? null,
        incrementalFailureCount: 0,
        lastSyncAttemptAt: new Date().toISOString(),
      })
      _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.SYNCED)
      manualRetryReason.value = null
      await _resolveSyncIssueIfNeeded(draft.sync_issue_id ?? syncIssueId.value)
      await hydrateAthletes(sessionDate.value)
      return response
    } catch (error) {
      await _markManualRetryRequired(draft, triggerReason, error)
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

    if (draft.sync_status === TRAINING_DRAFT_SYNC_STATUS.MANUAL_REQUIRED) {
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
        const response = await syncTrainingSetOperation(toSessionSyncOperationPayload(operation))
        syncedAnyOperation = true
        pendingOperations = pendingOperations.slice(1)
        pendingOperations = bindPendingOperationsToSession(response.session, pendingOperations)

        if (operation.operation_type === 'create_set' && operation.local_record_id && response.record) {
          const pendingLocalRecord = findPendingTrainingRecord(session.value, operation.local_record_id)
          if (pendingLocalRecord && recordNeedsFollowUpUpdate(pendingLocalRecord, response.record)) {
            pendingOperations = queueFollowUpTrainingUpdateOperation(
              pendingOperations,
              response.session.id,
              response.record.id,
              pendingLocalRecord,
            )
          }
        }

        const rebuiltSession = replayPendingTrainingOperations(response.session, pendingOperations)
        _replaceSession(rebuiltSession)
        _persistLocalDraft({
          ...draftUiState.value,
          pendingSync: pendingOperations.length > 0,
          syncStatus: pendingOperations.length > 0 ? TRAINING_DRAFT_SYNC_STATUS.PENDING : TRAINING_DRAFT_SYNC_STATUS.SYNCED,
          syncIssueId: null,
          pendingOperations,
          lastServerUpdatedAt: response.session.updated_at ?? null,
          lastServerSignature: response.session.server_signature ?? null,
          incrementalFailureCount: 0,
          lastSyncAttemptAt: new Date().toISOString(),
        })
      }

      _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.SYNCED)
      await _resolveSyncIssueIfNeeded(draft.sync_issue_id ?? syncIssueId.value)
      await hydrateAthletes(sessionDate.value)
    } catch {
      const nextFailureCount = (draft.incremental_failure_count || 0) + 1
      _setSyncStatus(TRAINING_DRAFT_SYNC_STATUS.PENDING)
      _persistLocalDraft({
        ...draftUiState.value,
        pendingSync: true,
        syncStatus: TRAINING_DRAFT_SYNC_STATUS.PENDING,
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
          syncStatus: syncStatus.value,
          syncIssueId: syncIssueId.value,
          incrementalFailureCount: 0,
        })
      }
    }
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
    manualRetryReason,
    hydrateAthletes,
    loadPlans,
    openPlanSession,
    loadSession,
    recordSet,
    reviseSetRecord,
    endSession,
    submitSessionFinishFeedback,
    setPreviewAssignment,
    getDraftForSession,
    getDraftBySessionId,
    getDraftByContext,
    getDraftBySessionKey,
    getLatestRecoverableDraft,
    restoreDraft,
    replaceSessionFromRemote,
    classifyDraftRelation,
    handoffConflictToCoach,
    discardDraft,
    persistLocalDraftState,
    syncPendingOperations,
    requestFullSessionSync,
  }
})
