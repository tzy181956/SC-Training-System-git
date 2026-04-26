export const TRAINING_STATUS_LABELS = {
  not_started: '未开始',
  in_progress: '进行中',
  completed: '已完成',
  partial_complete: '未完全完成',
  absent: '缺席',
  pending: '待同步',
  no_plan: '无计划',
} as const

export const TRAINING_STATUS_TONES = {
  not_started: 'danger',
  in_progress: 'progress',
  completed: 'success',
  partial_complete: 'partial',
  absent: 'neutral',
  pending: 'warning',
  no_plan: 'neutral',
} as const

export type TrainingStatus = keyof typeof TRAINING_STATUS_LABELS
export type TrainingStatusTone = (typeof TRAINING_STATUS_TONES)[TrainingStatus]

const TRAINING_STATUS_SET = new Set(Object.keys(TRAINING_STATUS_LABELS) as TrainingStatus[])
const FINAL_TRAINING_STATUS_SET = new Set<TrainingStatus>(['completed', 'partial_complete', 'absent'])

export function normalizeTrainingStatus(status?: string | null): TrainingStatus {
  if (status && TRAINING_STATUS_SET.has(status as TrainingStatus)) {
    return status as TrainingStatus
  }
  return 'no_plan'
}

export function getTrainingStatusLabel(
  status?: string | null,
  overrides: Partial<Record<TrainingStatus, string>> = {},
) {
  const normalizedStatus = normalizeTrainingStatus(status)
  return overrides[normalizedStatus] ?? TRAINING_STATUS_LABELS[normalizedStatus]
}

export function getTrainingStatusTone(status?: string | null): TrainingStatusTone {
  return TRAINING_STATUS_TONES[normalizeTrainingStatus(status)]
}

export function isFinalTrainingStatus(status?: string | null) {
  return FINAL_TRAINING_STATUS_SET.has(normalizeTrainingStatus(status))
}
