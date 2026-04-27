<script setup lang="ts">
import { computed, onBeforeUnmount, watch } from 'vue'

import {
  getTrainingStatusLabel,
  getTrainingStatusTone,
  MONITORING_STATUS_LABEL_OVERRIDES,
} from '@/constants/trainingStatus'
import {
  getSessionRpeHelp,
  getSessionRpeLabel,
  isExtremeSessionRpe,
  isHighSessionRpe,
} from '@/constants/sessionRpe'
import type {
  MonitoringAlertLevel,
  MonitoringAssignmentDetail,
  MonitoringAthleteCard,
  MonitoringAthleteDetailResponse,
  MonitoringExerciseItem,
  MonitoringSetRecord,
} from '@/types/monitoring'

const props = defineProps<{
  athlete: MonitoringAthleteCard | null
  detail: MonitoringAthleteDetailResponse | null
  loading: boolean
  error: string
  sessionDate: string
  visible: boolean
}>()

const emit = defineEmits<{
  close: []
  openSession: []
  openReport: []
  retryLoad: []
}>()

const shouldShow = computed(() => props.visible && props.athlete !== null)
const displayAthlete = computed(() => props.detail || props.athlete)
const sessionStatus = computed(() => displayAthlete.value?.session_status || 'no_plan')
const syncStatus = computed(() => displayAthlete.value?.sync_status || 'synced')
const alertLevel = computed<MonitoringAlertLevel>(() => props.detail?.alert_level ?? props.athlete?.alert_level ?? 'none')
const statusTone = computed(() => getTrainingStatusTone(sessionStatus.value))
const statusLabel = computed(() => getTrainingStatusLabel(sessionStatus.value, MONITORING_STATUS_LABEL_OVERRIDES))
const syncLabel = computed(() => {
  if (syncStatus.value === 'manual_retry_required') return '同步异常待处理'
  if (syncStatus.value === 'pending') return '待同步'
  return '已同步'
})
const alertLevelLabels: Record<MonitoringAlertLevel, string> = {
  none: '',
  info: '提示',
  warning: '警告',
  critical: '关键',
}
const canOpenSession = computed(() => {
  if (props.detail) {
    return props.detail.assignments.some((assignment) => assignment.session_id !== null)
  }
  return Boolean(props.athlete?.session_id)
})
const totalCompletedItems = computed(() => props.detail?.assignments.reduce((sum, assignment) => sum + assignment.completed_items, 0) ?? props.athlete?.completed_items ?? 0)
const totalItems = computed(() => props.detail?.assignments.reduce((sum, assignment) => sum + assignment.total_items, 0) ?? props.athlete?.total_items ?? 0)
const totalCompletedSets = computed(() => props.detail?.assignments.reduce((sum, assignment) => sum + assignment.completed_sets, 0) ?? props.athlete?.completed_sets ?? 0)
const totalSets = computed(() => props.detail?.assignments.reduce((sum, assignment) => sum + assignment.total_sets, 0) ?? props.athlete?.total_sets ?? 0)
const alertMessages = computed(() => {
  const reasons = props.detail?.alert_reasons?.length ? props.detail.alert_reasons : props.athlete?.alert_reasons ?? []
  if (reasons.length) return reasons

  const messages: string[] = []
  if (syncStatus.value === 'manual_retry_required') messages.push('同步异常待处理。')
  if (syncStatus.value === 'pending') messages.push('本地数据待同步。')
  if (sessionStatus.value === 'partial_complete') messages.push('已结束未完成，需要课后确认。')
  if (sessionStatus.value === 'absent') messages.push('缺席。')
  return messages
})

function statusText(status: string) {
  return getTrainingStatusLabel(status, MONITORING_STATUS_LABEL_OVERRIDES)
}

function targetText(exercise: MonitoringExerciseItem) {
  const repsText = exercise.prescribed_reps == null ? '未设次数' : `${exercise.prescribed_reps}次`
  const loadText = exercise.target_weight == null ? exercise.target_note || '未设重量' : `${exercise.target_weight}kg`
  return `${exercise.prescribed_sets}组 × ${repsText} × ${loadText}`
}

function remainingSetText(exercise: MonitoringExerciseItem) {
  const remaining = Math.max(exercise.prescribed_sets - exercise.completed_sets, 0)
  if (remaining <= 0) return ''
  return `还有 ${remaining} 组未完成`
}

function formatWeight(value?: number | null) {
  return value == null ? '-' : `${value}kg`
}

function formatReps(value?: number | null) {
  return value == null ? '-' : `${value}次`
}

function formatRir(value?: number | null) {
  return value == null ? '-' : String(value)
}

function formatDateTime(value?: string | null) {
  if (!value) return '-'

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function assignmentKey(assignment: MonitoringAssignmentDetail) {
  return `${assignment.assignment_id}-${assignment.session_id ?? 'preview'}`
}

function recordKey(record: MonitoringSetRecord) {
  return record.id ?? `pending-${record.set_number}`
}

function shouldShowAssignmentSessionRpe(assignment: MonitoringAssignmentDetail) {
  return assignment.session_status === 'completed' || assignment.session_rpe != null
}

function assignmentSessionRpeText(assignment: MonitoringAssignmentDetail) {
  if (assignment.session_rpe == null) return 'RPE 未填写'
  return `RPE ${assignment.session_rpe}/10｜${getSessionRpeLabel(assignment.session_rpe)}`
}

function assignmentSessionRpeHelp(assignment: MonitoringAssignmentDetail) {
  if (assignment.session_rpe == null) return ''
  return getSessionRpeHelp(assignment.session_rpe)
}

function assignmentSessionRpeHint(assignment: MonitoringAssignmentDetail) {
  if (isExtremeSessionRpe(assignment.session_rpe)) return '接近极限反馈'
  if (isHighSessionRpe(assignment.session_rpe)) return '主观强度偏高'
  return ''
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape' && shouldShow.value) {
    emit('close')
  }
}

watch(
  shouldShow,
  (visible) => {
    if (visible) {
      window.addEventListener('keydown', handleKeydown)
      return
    }
    window.removeEventListener('keydown', handleKeydown)
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div
    v-if="shouldShow && athlete"
    class="detail-overlay"
    role="presentation"
    @click="emit('close')"
  >
    <article
      class="detail-card"
      role="dialog"
      aria-modal="true"
      :aria-label="`${athlete.athlete_name} 今日训练详情`"
      @click.stop
    >
      <header class="detail-head">
        <div class="athlete-title">
          <p class="section-label">{{ sessionDate }}</p>
          <h2>{{ displayAthlete?.athlete_name || athlete.athlete_name }}</h2>
          <span>{{ displayAthlete?.team_name || '未分队' }}</span>
        </div>
        <div class="status-stack">
          <span v-if="alertLevel !== 'none'" class="alert-pill" :class="alertLevel">
            {{ alertLevelLabels[alertLevel] }}
          </span>
          <span class="status-pill" :class="statusTone">{{ statusLabel }}</span>
          <span class="sync-pill" :class="syncStatus">{{ syncLabel }}</span>
        </div>
      </header>

      <div class="metric-grid">
        <div class="metric-card">
          <span>动作进度</span>
          <strong>{{ totalCompletedItems }} / {{ totalItems }}</strong>
        </div>
        <div class="metric-card">
          <span>组数进度</span>
          <strong>{{ totalCompletedSets }} / {{ totalSets }}</strong>
        </div>
      </div>

      <div v-if="alertMessages.length" class="alert-list">
        <span v-for="message in alertMessages" :key="message">{{ message }}</span>
      </div>

      <div v-if="loading" class="detail-state">正在加载本次训练明细...</div>
      <div v-else-if="error" class="detail-state error-state">
        <span>{{ error }}</span>
        <button class="secondary-btn detail-btn" type="button" @click.stop="emit('retryLoad')">重试加载</button>
      </div>
      <div v-else-if="detail && !detail.assignments.length" class="detail-state">该队员当天无有效训练计划。</div>

      <section v-else-if="detail" class="assignment-list">
        <article
          v-for="assignment in detail.assignments"
          :key="assignmentKey(assignment)"
          class="assignment-card"
        >
          <header class="assignment-head">
            <div>
              <span class="section-label">训练计划</span>
              <h3>{{ assignment.template_name }}</h3>
            </div>
            <div class="assignment-meta">
              <span class="status-pill" :class="getTrainingStatusTone(assignment.session_status)">
                {{ statusText(assignment.session_status) }}
              </span>
              <span>{{ assignment.completed_items }}/{{ assignment.total_items }} 动作</span>
              <span>{{ assignment.completed_sets }}/{{ assignment.total_sets }} 组</span>
            </div>
          </header>

          <div v-if="shouldShowAssignmentSessionRpe(assignment)" class="assignment-feedback">
            <strong>{{ assignmentSessionRpeText(assignment) }}</strong>
            <span v-if="assignmentSessionRpeHelp(assignment)">{{ assignmentSessionRpeHelp(assignment) }}</span>
            <span v-if="assignmentSessionRpeHint(assignment)">{{ assignmentSessionRpeHint(assignment) }}</span>
            <span v-if="assignment.session_completed_at">完成时间：{{ formatDateTime(assignment.session_completed_at) }}</span>
            <p v-if="assignment.session_feedback" class="assignment-feedback-note">{{ assignment.session_feedback }}</p>
          </div>

          <div class="exercise-list">
            <article
              v-for="exercise in assignment.exercises"
              :key="`${assignment.assignment_id}-${exercise.sort_order}-${exercise.exercise_id ?? exercise.exercise_name}`"
              class="exercise-card"
            >
              <header class="exercise-head">
                <div>
                  <div class="exercise-title-row">
                    <h4>{{ exercise.exercise_name }}</h4>
                    <span v-if="exercise.is_main_lift" class="main-lift-pill">主项</span>
                  </div>
                  <p>{{ targetText(exercise) }}</p>
                </div>
                <div class="exercise-meta">
                  <span>{{ statusText(exercise.status) }}</span>
                  <strong>{{ exercise.completed_sets }} / {{ exercise.prescribed_sets }} 组</strong>
                </div>
              </header>

              <div v-if="exercise.records.length" class="record-table-wrap">
                <table class="record-table">
                  <thead>
                    <tr>
                      <th>组</th>
                      <th>目标重量</th>
                      <th>目标次数</th>
                      <th>实际重量</th>
                      <th>实际次数</th>
                      <th>RIR</th>
                      <th>时间</th>
                      <th>备注</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="record in exercise.records" :key="recordKey(record)">
                      <td data-label="组">第 {{ record.set_number }} 组</td>
                      <td data-label="目标重量">{{ formatWeight(record.target_weight) }}</td>
                      <td data-label="目标次数">{{ formatReps(record.target_reps) }}</td>
                      <td data-label="实际重量">{{ formatWeight(record.actual_weight) }}</td>
                      <td data-label="实际次数">{{ formatReps(record.actual_reps) }}</td>
                      <td data-label="RIR">{{ formatRir(record.actual_rir) }}</td>
                      <td data-label="时间">{{ formatDateTime(record.completed_at) }}</td>
                      <td data-label="备注">{{ record.notes || '-' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div v-else class="empty-records">暂无完成组记录。</div>
              <div v-if="remainingSetText(exercise)" class="remaining-sets">{{ remainingSetText(exercise) }}</div>
            </article>
          </div>
        </article>
      </section>

      <footer class="detail-actions">
        <button class="secondary-btn detail-btn" type="button" @click.stop="emit('close')">关闭</button>
        <button class="secondary-btn detail-btn" type="button" @click.stop="emit('openReport')">查看训练报告</button>
        <button
          v-if="canOpenSession"
          class="primary-btn detail-btn"
          type="button"
          @click.stop="emit('openSession')"
        >
          进入训练记录页
        </button>
      </footer>
    </article>
  </div>
</template>

<style scoped>
.detail-overlay {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 40px;
  background: rgba(15, 23, 42, 0.38);
  backdrop-filter: blur(2px);
}

.detail-card {
  width: min(960px, calc(100vw - 80px));
  max-height: calc(100dvh - 80px);
  margin: auto;
  overflow-y: auto;
  display: grid;
  gap: 18px;
  padding: 24px;
  border-radius: 24px;
  background: white;
  box-shadow: 0 24px 80px rgba(15, 23, 42, 0.28);
  color: var(--text);
}

.detail-head,
.assignment-head,
.exercise-head,
.detail-actions {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.athlete-title,
.assignment-head > div:first-child,
.exercise-head > div:first-child {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.athlete-title h2,
.athlete-title p,
.assignment-head h3,
.exercise-head h4,
.exercise-head p {
  margin: 0;
}

.athlete-title h2 {
  font-size: clamp(1.8rem, 3vw, 2.6rem);
  line-height: 1.05;
}

.assignment-head h3 {
  font-size: 1.25rem;
}

.exercise-head h4 {
  font-size: 1.05rem;
}

.athlete-title span,
.section-label,
.metric-card span,
.exercise-head p,
.assignment-meta,
.exercise-meta {
  color: var(--text-soft);
}

.status-stack,
.assignment-meta {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.status-pill,
.sync-pill,
.alert-pill,
.alert-list span,
.main-lift-pill {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 11px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 800;
  white-space: nowrap;
}

.status-pill.success,
.sync-pill.synced {
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

.status-pill.danger,
.sync-pill.manual_retry_required {
  background: #fee2e2;
  color: #b91c1c;
}

.sync-pill.pending {
  background: #fef3c7;
  color: #92400e;
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

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.metric-card,
.assignment-card,
.exercise-card,
.detail-state {
  border: 1px solid var(--line);
  border-radius: 18px;
  background: var(--panel-soft);
}

.metric-card {
  display: grid;
  gap: 8px;
  padding: 16px;
}

.metric-card strong {
  font-size: 2rem;
  line-height: 1;
  color: #115e59;
}

.alert-list {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.alert-list span {
  background: #fff7ed;
  color: #c2410c;
}

.detail-state {
  min-height: 120px;
  display: grid;
  place-items: center;
  gap: 12px;
  padding: 18px;
  color: var(--text-soft);
}

.error-state {
  color: #b91c1c;
}

.assignment-list,
.exercise-list {
  display: grid;
  gap: 14px;
}

.assignment-feedback {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.04);
}

.assignment-feedback span,
.assignment-feedback-note {
  color: var(--text-soft);
}

.assignment-feedback-note {
  margin: 0;
}

.assignment-card,
.exercise-card {
  display: grid;
  gap: 14px;
  padding: 16px;
  background: white;
}

.exercise-card {
  background: #f8fafc;
}

.exercise-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.main-lift-pill {
  min-height: 26px;
  padding: 0 9px;
  background: #ccfbf1;
  color: #0f766e;
}

.exercise-meta {
  display: grid;
  gap: 4px;
  justify-items: end;
  text-align: right;
}

.record-table-wrap {
  overflow-x: auto;
}

.record-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 760px;
  font-size: 14px;
}

.record-table th,
.record-table td {
  padding: 10px 9px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.32);
  text-align: left;
  vertical-align: top;
}

.record-table th {
  color: var(--text-soft);
  font-size: 12px;
  font-weight: 800;
}

.empty-records,
.remaining-sets {
  min-height: 38px;
  display: flex;
  align-items: center;
  padding: 0 12px;
  border-radius: 12px;
  background: rgba(15, 118, 110, 0.08);
  color: #115e59;
  font-weight: 700;
}

.empty-records {
  background: #f1f5f9;
  color: var(--text-soft);
}

.detail-actions {
  justify-content: flex-end;
  flex-wrap: wrap;
  padding-top: 4px;
}

.detail-btn {
  min-height: 42px;
}

@media (max-width: 1180px) {
  .detail-overlay {
    padding: 28px;
  }

  .detail-card {
    width: min(860px, calc(100vw - 56px));
    max-height: calc(100dvh - 56px);
  }
}

@media (max-width: 640px) {
  .detail-overlay {
    padding: 14px;
  }

  .detail-card {
    width: calc(100vw - 28px);
    max-height: calc(100dvh - 28px);
    gap: 14px;
    padding: 18px;
    border-radius: 18px;
  }

  .detail-head,
  .assignment-head,
  .exercise-head,
  .detail-actions {
    flex-direction: column;
  }

  .status-stack,
  .assignment-meta,
  .detail-actions {
    justify-content: flex-start;
  }

  .exercise-meta {
    justify-items: start;
    text-align: left;
  }

  .metric-grid {
    grid-template-columns: 1fr;
  }

  .record-table-wrap {
    overflow-x: visible;
  }

  .record-table,
  .record-table thead,
  .record-table tbody,
  .record-table tr,
  .record-table td {
    display: block;
    width: 100%;
    min-width: 0;
  }

  .record-table thead {
    display: none;
  }

  .record-table tr {
    padding: 10px;
    border: 1px solid rgba(148, 163, 184, 0.32);
    border-radius: 12px;
    background: white;
  }

  .record-table tr + tr {
    margin-top: 10px;
  }

  .record-table td {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    padding: 7px 0;
    border-bottom: 0;
  }

  .record-table td::before {
    content: attr(data-label);
    color: var(--text-soft);
    font-weight: 800;
  }
}
</style>
