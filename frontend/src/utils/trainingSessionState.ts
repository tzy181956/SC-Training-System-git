import type { TrainingDraftSetPayload } from '@/utils/trainingDraft'

const NOT_STARTED_SESSION_STATUS = 'not_started'
const IN_PROGRESS_SESSION_STATUS = 'in_progress'

type SessionItemLocator = {
  itemId?: number | null
  templateItemId?: number | null
}

export function cloneTrainingSession<T>(value: T): T {
  return JSON.parse(JSON.stringify(value))
}

export function resolveTrainingSessionItem(targetSession: any, itemId?: number | null, templateItemId?: number | null) {
  const items = targetSession.items || []
  return items.find((entry: any) => entry.id === itemId) || items.find((entry: any) => entry.template_item_id === templateItemId) || null
}

export function applyCreateSetToLocalSession(
  targetSession: any,
  itemLocator: SessionItemLocator,
  payload: TrainingDraftSetPayload,
  localRecordId: number,
  completedAt: string,
) {
  const item = resolveTrainingSessionItem(targetSession, itemLocator.itemId, itemLocator.templateItemId)
  if (!item) throw new Error('Session item not found')

  const previousRecord = item.records?.[item.records.length - 1] || null
  const nextSetNumber = (item.records?.length || 0) + 1
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
  recomputeLocalSessionState(targetSession, completedAt)
  return { item, record }
}

export function applyUpdateSetToLocalSession(
  targetSession: any,
  recordId: number,
  payload: TrainingDraftSetPayload,
  completedAt: string,
) {
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
  matchedRecord.completed_at = completedAt

  recomputeLocalSessionState(targetSession, completedAt)
  return { item: matchedItem, record: matchedRecord }
}

export function recomputeLocalSessionState(targetSession: any, fallbackTimestamp: string) {
  const items = targetSession.items || []
  let totalRecords = 0

  for (const item of items) {
    const recordCount = item.records?.length || 0
    totalRecords += recordCount
    item.status = resolveLocalSessionItemStatus(recordCount, item.prescribed_sets)
  }

  if (!items.length || totalRecords === 0) {
    targetSession.status = NOT_STARTED_SESSION_STATUS
    targetSession.started_at = null
    targetSession.completed_at = null
    return
  }

  const sessionCompleted = items.every((entry: any) => (entry.records?.length || 0) >= entry.prescribed_sets)
  targetSession.status = sessionCompleted ? 'completed' : IN_PROGRESS_SESSION_STATUS
  targetSession.started_at = targetSession.started_at || findFirstRecordedAt(items) || fallbackTimestamp
  targetSession.completed_at = sessionCompleted ? targetSession.completed_at || fallbackTimestamp : null
}

export function finalizeLocalSession(targetSession: any, completedAt: string) {
  const items = targetSession.items || []
  for (const item of items) {
    const recordCount = item.records?.length || 0
    item.status = resolveLocalSessionItemStatus(recordCount, item.prescribed_sets)
  }

  const totalRecords = items.reduce((total: number, item: any) => total + (item.records?.length || 0), 0)
  const allCompleted = !!items.length && items.every((item: any) => item.status === 'completed')
  targetSession.status = allCompleted ? 'completed' : 'partial_complete'
  targetSession.started_at = totalRecords > 0 ? targetSession.started_at || findFirstRecordedAt(items) : null
  targetSession.completed_at = completedAt
}

export function findTrainingSessionRecord(targetSession: any, recordId: number) {
  if (!targetSession?.items?.length) return null
  for (const item of targetSession.items) {
    const record = item.records?.find((entry: any) => entry.id === recordId)
    if (record) return record
  }
  return null
}

export function resolveLocalSessionItemStatus(recordCount: number, prescribedSets: number) {
  if (recordCount === 0) return 'pending'
  if (recordCount >= prescribedSets) return 'completed'
  return IN_PROGRESS_SESSION_STATUS
}

function findFirstRecordedAt(items: any[]) {
  const completedAts = items
    .flatMap((item: any) => item.records || [])
    .map((record: any) => record.completed_at)
    .filter(Boolean)
    .sort()
  return completedAts[0] || null
}
