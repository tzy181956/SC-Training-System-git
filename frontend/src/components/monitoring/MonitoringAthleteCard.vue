<script setup lang="ts">
import { computed } from 'vue'

import {
  getTrainingStatusLabel,
  getTrainingStatusTone,
  MONITORING_STATUS_LABEL_OVERRIDES,
} from '@/constants/trainingStatus'
import { getSessionRpeLabel, isExtremeSessionRpe, isHighSessionRpe } from '@/constants/sessionRpe'
import type { MonitoringAlertLevel, MonitoringAthleteCard } from '@/types/monitoring'
import { buildMonitoringAlertKey, resolveMonitoringAlertLevel } from '@/utils/monitoringAlerts'

const props = defineProps<{
  athlete: MonitoringAthleteCard
  sessionDate: string
  dismissedAlertKeys: string[]
}>()

const emit = defineEmits<{
  select: []
}>()

function progressText(completed: number, total: number, unit: string) {
  return total ? `${completed}/${total} ${unit}` : `无${unit}计划`
}

function clampProgressRatio(value: number) {
  if (Number.isNaN(value)) return 0
  return Math.min(Math.max(value, 0), 1)
}

function setProgressRatio() {
  if (props.athlete.total_sets > 0) {
    return clampProgressRatio(props.athlete.completed_sets / props.athlete.total_sets)
  }
  if (props.athlete.total_items > 0) {
    return clampProgressRatio(props.athlete.completed_items / props.athlete.total_items)
  }
  return props.athlete.session_status === 'completed' ? 1 : 0
}

function progressStyle() {
  return {
    '--progress-ratio': String(setProgressRatio()),
  }
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

function shouldShowSessionRpe() {
  return props.athlete.session_status === 'completed' || props.athlete.session_rpe != null
}

function sessionRpeText() {
  if (props.athlete.session_rpe == null) return 'RPE 未填写'
  return `RPE ${props.athlete.session_rpe}/10｜${getSessionRpeLabel(props.athlete.session_rpe)}`
}

function sessionRpeHint() {
  if (isExtremeSessionRpe(props.athlete.session_rpe)) return '接近极限反馈'
  if (isHighSessionRpe(props.athlete.session_rpe)) return '主观强度偏高'
  if (props.athlete.session_rpe == null) return ''
  return ''
}

const alertLevelLabels: Record<MonitoringAlertLevel, string> = {
  none: '',
  info: '提示',
  warning: '警告',
  critical: '关键',
}

const alertHidden = computed(() => props.dismissedAlertKeys.includes(buildMonitoringAlertKey(props.sessionDate, props.athlete)))
const visibleAlertLevel = computed<MonitoringAlertLevel>(() => (alertHidden.value ? 'none' : resolveMonitoringAlertLevel(props.athlete)))
const showAlert = computed(() => visibleAlertLevel.value !== 'none')

function statusLabel() {
  return getTrainingStatusLabel(props.athlete.session_status, MONITORING_STATUS_LABEL_OVERRIDES)
}

function statusTone() {
  return getTrainingStatusTone(props.athlete.session_status)
}
</script>

<template>
  <button
    class="athlete-card"
    :class="[statusTone(), visibleAlertLevel, { alert: showAlert }]"
    :style="progressStyle()"
    data-testid="monitoring-athlete-card"
    :data-athlete-name="athlete.athlete_name"
    :data-session-status="athlete.session_status"
    :data-sync-status="athlete.sync_status"
    type="button"
    @click="emit('select')"
  >
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
      <div class="progress-metric">
        <strong>{{ progressText(athlete.completed_items, athlete.total_items, '动作') }}</strong>
        <small>动作完成</small>
      </div>
      <div class="progress-metric">
        <strong>{{ progressText(athlete.completed_sets, athlete.total_sets, '组') }}</strong>
        <small>组完成</small>
      </div>
    </div>

    <div v-if="shouldShowSessionRpe()" class="session-rpe-line">
      <strong>{{ sessionRpeText() }}</strong>
      <span v-if="sessionRpeHint()">{{ sessionRpeHint() }}</span>
    </div>

    <div class="card-foot">
      <span class="latest-set">{{ latestSetText() }}</span>
      <div class="pill-row">
        <span v-if="showAlert" class="alert-pill" :class="visibleAlertLevel">
          {{ alertLevelLabels[visibleAlertLevel] }}
        </span>
        <span class="sync-pill" :class="athlete.sync_status">{{ syncLabel() }}</span>
      </div>
    </div>
  </button>
</template>

<style scoped>
.athlete-card {
  --progress-ratio: 0;
  --progress-soft: rgba(15, 118, 110, 0.1);
  --progress-soft-strong: rgba(15, 118, 110, 0.16);
  position: relative;
  isolation: isolate;
  overflow: hidden;
  display: grid;
  gap: 12px;
  width: 100%;
  min-height: 194px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: white;
  color: var(--text);
  text-align: left;
  cursor: pointer;
}

.athlete-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, var(--progress-soft) 0%, var(--progress-soft-strong) 100%);
  transform: scaleX(var(--progress-ratio));
  transform-origin: left center;
  pointer-events: none;
  z-index: 0;
}

.athlete-card > * {
  position: relative;
  z-index: 1;
}

.athlete-card.success {
  --progress-soft: rgba(22, 163, 74, 0.11);
  --progress-soft-strong: rgba(22, 163, 74, 0.18);
}

.athlete-card.progress {
  --progress-soft: rgba(37, 99, 235, 0.1);
  --progress-soft-strong: rgba(37, 99, 235, 0.17);
}

.athlete-card.partial {
  --progress-soft: rgba(217, 119, 6, 0.1);
  --progress-soft-strong: rgba(217, 119, 6, 0.17);
}

.athlete-card.neutral,
.athlete-card.danger {
  --progress-soft: rgba(100, 116, 139, 0.08);
  --progress-soft-strong: rgba(100, 116, 139, 0.13);
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

.progress-metric {
  display: grid;
  gap: 2px;
  min-height: 46px;
  padding: 8px 10px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(15, 23, 42, 0.06);
}

.progress-metric strong {
  color: var(--text);
  font-size: 14px;
}

.progress-metric small {
  color: var(--text-soft);
  font-size: 12px;
}

.session-rpe-line {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.04);
}

.session-rpe-line strong {
  font-size: 14px;
}

.session-rpe-line span {
  color: var(--text-soft);
  font-size: 13px;
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
