<script setup lang="ts">
import {
  getTrainingStatusLabel,
  getTrainingStatusTone,
  MONITORING_STATUS_LABEL_OVERRIDES,
} from '@/constants/trainingStatus'
import type { MonitoringAlertLevel, MonitoringAthleteCard } from '@/types/monitoring'

const props = defineProps<{
  athlete: MonitoringAthleteCard
}>()

const emit = defineEmits<{
  select: []
}>()

function progressText(completed: number, total: number, unit: string) {
  return total ? `${completed}/${total} ${unit}` : `无${unit}计划`
}

function latestSetText() {
  const latestSet = props.athlete.latest_set
  if (!latestSet) return '暂无组记录'
  return `${latestSet.actual_weight ?? '-'}kg · ${latestSet.actual_reps ?? '-'}次 · RIR ${latestSet.actual_rir ?? '-'}`
}

function syncLabel() {
  if (props.athlete.sync_status === 'manual_retry_required') return '同步异常'
  if (props.athlete.sync_status === 'pending') return '待同步'
  return '已同步'
}

const alertLevelLabels: Record<MonitoringAlertLevel, string> = {
  none: '',
  info: '提示',
  warning: '警告',
  critical: '关键',
}

function statusLabel() {
  return getTrainingStatusLabel(props.athlete.session_status, MONITORING_STATUS_LABEL_OVERRIDES)
}

function statusTone() {
  return getTrainingStatusTone(props.athlete.session_status)
}
</script>

<template>
  <button class="athlete-card" :class="[statusTone(), athlete.alert_level, { alert: athlete.has_alert }]" type="button" @click="emit('select')">
    <div class="card-head">
      <div class="athlete-copy adaptive-card">
        <strong class="adaptive-card-title">{{ athlete.athlete_name }}</strong>
        <span class="adaptive-card-subtitle">{{ athlete.team_name || '未分队' }}</span>
      </div>
      <span class="status-pill" :class="statusTone()">{{ statusLabel() }}</span>
    </div>

    <div class="exercise-line">
      <span>当前动作</span>
      <strong>{{ athlete.current_exercise_name || '暂无动作' }}</strong>
    </div>

    <div class="progress-grid">
      <span>{{ progressText(athlete.completed_items, athlete.total_items, '动作') }}</span>
      <span>{{ progressText(athlete.completed_sets, athlete.total_sets, '组') }}</span>
    </div>

    <div class="card-foot">
      <span class="latest-set">{{ latestSetText() }}</span>
      <div class="pill-row">
        <span v-if="athlete.alert_level !== 'none'" class="alert-pill" :class="athlete.alert_level">
          {{ alertLevelLabels[athlete.alert_level] }}
        </span>
        <span class="sync-pill" :class="athlete.sync_status">{{ syncLabel() }}</span>
      </div>
    </div>
  </button>
</template>

<style scoped>
.athlete-card {
  display: grid;
  gap: 12px;
  width: 100%;
  min-height: 190px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: white;
  color: var(--text);
  text-align: left;
  cursor: pointer;
}

.athlete-card:focus-visible {
  outline: 3px solid rgba(15, 118, 110, 0.22);
  outline-offset: 2px;
}

.athlete-card:hover {
  border-color: rgba(15, 118, 110, 0.3);
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.08);
}

.athlete-card.alert {
  border-color: rgba(185, 28, 28, 0.32);
}

.athlete-card.alert.info {
  border-color: rgba(37, 99, 235, 0.28);
}

.athlete-card.alert.warning {
  border-color: rgba(217, 119, 6, 0.34);
}

.athlete-card.alert.critical {
  border-color: rgba(185, 28, 28, 0.42);
}

.card-head,
.card-foot,
.exercise-line {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  min-width: 0;
}

.athlete-copy {
  display: grid;
  gap: 3px;
  min-width: 0;
}

.status-pill,
.sync-pill,
.alert-pill {
  flex-shrink: 0;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.status-pill.success {
  background: #dcfce7;
  color: #166534;
}

.status-pill.progress {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-pill.partial {
  background: #ffedd5;
  color: #c2410c;
}

.status-pill.neutral {
  background: #e5e7eb;
  color: #374151;
}

.status-pill.danger {
  background: #fee2e2;
  color: #b91c1c;
}

.exercise-line {
  align-items: center;
  padding: 10px 12px;
  border-radius: 12px;
  background: var(--panel-soft);
}

.exercise-line span,
.latest-set {
  color: var(--text-soft);
  font-size: 13px;
}

.exercise-line strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.progress-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px;
}

.progress-grid span {
  min-height: 34px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(15, 118, 110, 0.08);
  color: #115e59;
  font-weight: 700;
}

.sync-pill.synced {
  background: #dcfce7;
  color: #166534;
}

.sync-pill.pending {
  background: #fef3c7;
  color: #92400e;
}

.sync-pill.manual_retry_required {
  background: #fee2e2;
  color: #b91c1c;
}

.pill-row {
  display: flex;
  justify-content: flex-end;
  gap: 6px;
  flex-wrap: wrap;
}

.alert-pill.info {
  background: #dbeafe;
  color: #1d4ed8;
}

.alert-pill.warning {
  background: #fef3c7;
  color: #92400e;
}

.alert-pill.critical {
  background: #fee2e2;
  color: #b91c1c;
}

@media (max-width: 720px) {
  .card-foot {
    flex-direction: column;
  }
}
</style>
