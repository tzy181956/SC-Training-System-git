export const TRAINING_SYNC_CONFLICT_SUMMARY = '服务器已在本地最后确认同步后发生变化，当前设备继续本地记录，待教练处理'

export const TRAINING_SYNC_NOTICE_TEXT = {
  offlineRecoverable: '当前离线，正在使用本地草稿记录。',
  localAhead: '正在同步本地训练数据。',
  conflictHandoff: '该训练课已在其他位置更新，当前设备继续本地记录，课后请教练处理同步差异。',
} as const

export function isTrainingSyncConflictSummary(summary?: string | null) {
  if (!summary) return false
  return summary.includes('服务器已在本地最后确认同步后发生变化')
}

export function getTrainingSyncIssueLabel(summary?: string | null) {
  return isTrainingSyncConflictSummary(summary) ? '训练中冲突待处理' : '同步异常待处理'
}
