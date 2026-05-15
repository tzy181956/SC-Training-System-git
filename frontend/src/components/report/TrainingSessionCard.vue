<script setup lang="ts">
import { reactive, ref } from 'vue'

import {
  coachAddTrainingReportSet,
  coachDeleteTrainingReportSetRecord,
  coachVoidTrainingReportSession,
  coachUpdateTrainingReportSetRecord,
} from '@/api/trainingReports'
import { normalizeModeAliasForDisplay } from '@/constants/appModeLabels'
import { getSessionRpeHelp, getSessionRpeLabel } from '@/constants/sessionRpe'
import { getTrainingStatusLabel, getTrainingStatusTone } from '@/constants/trainingStatus'
import { confirmDangerousAction } from '@/utils/dangerousAction'
import { formatDurationMinutes } from '@/utils/sessionDuration'

const props = defineProps<{
  session: any
  onlyIncomplete?: boolean
  onlyMainLift?: boolean
  detailLoading?: boolean
  detailError?: string
}>()

const emit = defineEmits<{
  changed: []
  notify: [payload: { message: string; tone: 'success' | 'warning' | 'error' }]
  requestDetails: [sessionId: number]
}>()

const editingRecordId = ref<number | null>(null)
const savingRecordId = ref<number | null>(null)
const deletingRecordId = ref<number | null>(null)
const addingItemId = ref<number | null>(null)
const savingItemId = ref<number | null>(null)
const voidingSession = ref(false)

const editForm = reactive({
  actual_weight: 0,
  actual_reps: 0,
  actual_rir: 0,
  notes: '',
})

const addForm = reactive({
  actual_weight: 0,
  actual_reps: 0,
  actual_rir: 2,
  notes: '',
})

function shouldShowItem(item: any) {
  return (!props.onlyIncomplete || item.status !== 'completed') && (!props.onlyMainLift || item.is_main_lift)
}

function hasLoadedDetails() {
  return props.session.details_loaded || (props.session.items?.length || 0) > 0
}

function handleToggle(event: Event) {
  const target = event.target as HTMLDetailsElement
  if (!target.open) return
  if (hasLoadedDetails() || props.detailLoading) return
  emit('requestDetails', props.session.id)
}

function isVoidedSession() {
  return props.session.status === 'voided'
}

function canVoidSession() {
  return !isVoidedSession() && Number(props.session.completed_sets || 0) === 0
}

function adjustmentClass(record: any) {
  if (record.user_decision === 'accepted') return 'accepted'
  if (record.suggestion_weight != null && record.final_weight === record.suggestion_weight) return 'guided'
  return 'modified'
}

function startEdit(record: any) {
  editingRecordId.value = record.id
  editForm.actual_weight = record.actual_weight
  editForm.actual_reps = record.actual_reps
  editForm.actual_rir = record.actual_rir
  editForm.notes = record.notes ?? ''
}

function cancelEdit() {
  editingRecordId.value = null
}

function startAdd(item: any) {
  if (isVoidedSession()) return
  addingItemId.value = item.id
  const lastRecord = item.records[item.records.length - 1]
  addForm.actual_weight = lastRecord?.final_weight ?? lastRecord?.actual_weight ?? 0
  addForm.actual_reps = item.prescribed_reps
  addForm.actual_rir = 2
  addForm.notes = ''
}

function cancelAdd() {
  addingItemId.value = null
}

async function saveEdit(recordId: number) {
  savingRecordId.value = recordId
  try {
    await coachUpdateTrainingReportSetRecord(recordId, {
      actual_weight: editForm.actual_weight,
      actual_reps: editForm.actual_reps,
      actual_rir: editForm.actual_rir,
      notes: editForm.notes || null,
      actor_name: '管理端',
    })
    cancelEdit()
    emit('notify', { message: '课后修正已保存，训练课状态已重算。', tone: 'success' })
    emit('changed')
  } catch (error: any) {
    emit('notify', {
      message: error?.response?.data?.detail || '课后修正保存失败，请稍后重试。',
      tone: 'error',
    })
  } finally {
    savingRecordId.value = null
  }
}

async function saveAdd(itemId: number) {
  savingItemId.value = itemId
  try {
    await coachAddTrainingReportSet(itemId, {
      actual_weight: addForm.actual_weight,
      actual_reps: addForm.actual_reps,
      actual_rir: addForm.actual_rir,
      notes: addForm.notes || null,
      actor_name: '管理端',
    })
    cancelAdd()
    emit('notify', { message: '漏录组已补录，训练课状态已重算。', tone: 'success' })
    emit('changed')
  } catch (error: any) {
    emit('notify', {
      message: error?.response?.data?.detail || '补录失败，请检查该动作是否已经达到计划组数。',
      tone: 'error',
    })
  } finally {
    savingItemId.value = null
  }
}

async function deleteRecord(record: any, item: any) {
  const confirmed = confirmDangerousAction({
    title: '删除训练记录',
    impactLines: [
      `动作：${item.exercise_name}`,
      `组次：第 ${record.set_number} 组`,
      `删除后本堂课完成状态会自动重算`,
    ],
  })
  if (!confirmed) return

  deletingRecordId.value = record.id
  try {
    await coachDeleteTrainingReportSetRecord(record.id, {
      confirmed: true,
      actor_name: '管理端',
    })
    if (editingRecordId.value === record.id) {
      cancelEdit()
    }
    emit('notify', { message: '训练记录已删除，训练课状态已重算。', tone: 'success' })
    emit('changed')
  } catch (error: any) {
    emit('notify', {
      message: error?.response?.data?.detail || '删除训练记录失败，请稍后再试。',
      tone: 'error',
    })
  } finally {
    deletingRecordId.value = null
  }
}

async function voidSession() {
  if (!canVoidSession()) return
  const confirmed = confirmDangerousAction({
    title: '作废训练课',
    impactLines: [
      `日期：${props.session.session_date}`,
      `模板：${props.session.template_name}`,
      '仅无组记录训练课可以作废；作废后默认不计入训练统计和完成率。',
      '该操作不会删除数据库记录，会保留日志用于追溯。',
    ],
    recommendation: '如果运动员只是缺席但该课本应参加，请保留“缺席”状态，不要作废。',
  })
  if (!confirmed) return

  voidingSession.value = true
  try {
    await coachVoidTrainingReportSession(props.session.id, {
      confirmed: true,
      actor_name: '管理端',
    })
    emit('notify', { message: '训练课已作废，默认不再计入训练统计。', tone: 'success' })
    emit('changed')
  } catch (error: any) {
    emit('notify', {
      message: error?.response?.data?.detail || '作废训练课失败，请稍后再试。',
      tone: 'error',
    })
  } finally {
    voidingSession.value = false
  }
}

function formatDateTime(value?: string | null) {
  if (!value) return '--'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}

function sessionStatusLabel(status?: string) {
  return getTrainingStatusLabel(status)
}

function sessionStatusTone(status?: string) {
  return getTrainingStatusTone(status)
}

function sessionRpeText() {
  if (props.session.session_rpe == null) return '未填写'
  return `${props.session.session_rpe} / 10`
}

function sessionRpeDescription() {
  if (props.session.session_rpe == null) return ''
  return getSessionRpeLabel(props.session.session_rpe)
}

function sessionRpeHelpText() {
  if (props.session.session_rpe == null) return ''
  return getSessionRpeHelp(props.session.session_rpe)
}

function sessionFeedbackText() {
  return props.session.session_feedback ? `队员备注：${props.session.session_feedback}` : '队员备注：未填写备注'
}

function formatActorName(value?: string | null) {
  return normalizeModeAliasForDisplay(value)
}

function sessionDurationText() {
  if (props.session.session_duration_minutes == null) return ''
  return formatDurationMinutes(props.session.session_duration_minutes)
}

function sessionSrpeLoadText() {
  if (props.session.session_srpe_load == null) return ''
  return String(props.session.session_srpe_load)
}
</script>

<template>
  <details class="session-card" @toggle="handleToggle">
    <summary class="session-head">
      <div class="session-copy adaptive-card">
        <p class="session-date">{{ session.session_date }}</p>
        <h4 class="adaptive-card-title">{{ session.template_name }}</h4>
      </div>
      <div class="session-meta">
        <span class="status-chip" :class="sessionStatusTone(session.status)">{{ sessionStatusLabel(session.status) }}</span>
        <span>{{ session.completed_items }}/{{ session.total_items }} 个动作</span>
        <span>{{ session.completed_sets }}/{{ session.total_sets }} 组</span>
        <button
          v-if="canVoidSession()"
          class="link-btn danger-link session-action"
          type="button"
          :disabled="voidingSession"
          @click.stop.prevent="voidSession"
        >
          {{ voidingSession ? '作废中...' : '作废训练课' }}
        </button>
      </div>
    </summary>

    <div class="session-body">
      <section class="feedback-panel">
        <div class="feedback-head">
          <strong>本次训练反馈</strong>
          <span v-if="sessionDurationText()">训练用时：{{ sessionDurationText() }}</span>
          <span v-if="session.completed_at">完成时间：{{ formatDateTime(session.completed_at) }}</span>
        </div>
        <div class="feedback-grid">
          <div class="feedback-metric">
            <span>整体 RPE</span>
            <strong>{{ sessionRpeText() }}</strong>
          </div>
          <div v-if="sessionSrpeLoadText()" class="feedback-metric">
            <span>sRPE</span>
            <strong>{{ sessionSrpeLoadText() }}</strong>
          </div>
          <div v-if="session.session_rpe != null" class="feedback-metric">
            <span>主观用力程度</span>
            <strong>{{ sessionRpeDescription() }}</strong>
          </div>
        </div>
        <p v-if="session.session_rpe != null" class="feedback-note">解释：{{ sessionRpeHelpText() }}</p>
        <p class="feedback-note">{{ sessionFeedbackText() }}</p>
        <p v-if="isVoidedSession()" class="feedback-note danger-note">该训练课已作废，默认不计入训练统计和完成率。</p>
      </section>

      <div v-if="detailLoading" class="detail-state">正在加载训练明细...</div>
      <div v-else-if="detailError" class="detail-state danger-note">
        <span>{{ detailError }}</span>
        <button class="link-btn" type="button" @click="emit('requestDetails', session.id)">重试</button>
      </div>
      <div v-else-if="!hasLoadedDetails()" class="detail-state">
        展开后加载动作和组记录明细，避免一次性拉取过多训练数据。
      </div>

      <article
        v-for="item in session.items"
        :key="item.id"
        v-show="shouldShowItem(item)"
        class="item-card"
      >
        <div class="item-head">
          <div class="item-copy adaptive-card">
            <h5 class="adaptive-card-title">{{ item.exercise_name }}</h5>
            <p class="adaptive-card-subtitle adaptive-card-clamp-2">
              {{ item.completed_sets }}/{{ item.prescribed_sets }} 组，目标 {{ item.prescribed_reps }} 次
            </p>
          </div>

          <div class="item-actions">
            <span class="item-badge" :class="{ main: item.is_main_lift }">
              {{ item.is_main_lift ? '主项动作' : '常规动作' }}
            </span>
            <button
              v-if="!isVoidedSession() && item.completed_sets < item.prescribed_sets"
              class="secondary-btn small-btn"
              type="button"
              @click="addingItemId === item.id ? cancelAdd() : startAdd(item)"
            >
              {{ addingItemId === item.id ? '取消补录' : '补录一组' }}
            </button>
          </div>
        </div>

        <p v-if="item.target_note" class="item-note adaptive-card-subtitle adaptive-card-clamp-2">{{ item.target_note }}</p>

        <div class="record-table-wrap">
          <table class="record-table">
            <thead>
              <tr>
                <th>组次</th>
                <th>目标重量</th>
                <th>实际重量</th>
                <th>次数</th>
                <th>RIR</th>
                <th>建议重量</th>
                <th>最终采用</th>
                <th>调整说明</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="record in item.records" :key="record.id">
                <tr>
                  <td>第 {{ record.set_number }} 组</td>
                  <td>{{ record.target_weight ?? '-' }}</td>
                  <td>{{ record.actual_weight }}</td>
                  <td>{{ record.actual_reps }}</td>
                  <td>{{ record.actual_rir }}</td>
                  <td>{{ record.suggestion_weight ?? '-' }}</td>
                  <td>{{ record.final_weight }}</td>
                  <td>
                    <span class="decision-pill" :class="adjustmentClass(record)">{{ record.adjustment_type }}</span>
                  </td>
                  <td>
                    <button class="link-btn" type="button" @click="startEdit(record)">修改</button>
                    <button
                      class="link-btn danger-link"
                      type="button"
                      :disabled="deletingRecordId === record.id"
                      @click="deleteRecord(record, item)"
                    >
                      {{ deletingRecordId === record.id ? '删除中...' : '删除' }}
                    </button>
                  </td>
                </tr>
                <tr v-if="editingRecordId === record.id" class="editor-row">
                  <td colspan="9">
                    <div class="editor-grid">
                      <label class="field">
                        <span>重量</span>
                        <input v-model.number="editForm.actual_weight" type="number" step="0.5" class="text-input" />
                      </label>
                      <label class="field">
                        <span>次数</span>
                        <input v-model.number="editForm.actual_reps" type="number" min="0" class="text-input" />
                      </label>
                      <label class="field">
                        <span>RIR</span>
                        <input v-model.number="editForm.actual_rir" type="number" min="0" class="text-input" />
                      </label>
                      <label class="field notes-field">
                        <span>备注</span>
                        <input v-model="editForm.notes" type="text" class="text-input" />
                      </label>
                    </div>
                    <div class="editor-actions">
                      <button class="secondary-btn small-btn" type="button" @click="cancelEdit">取消</button>
                      <button
                        class="primary-btn small-btn"
                        type="button"
                        :disabled="savingRecordId === record.id"
                        @click="saveEdit(record.id)"
                      >
                        {{ savingRecordId === record.id ? '保存中...' : '保存修正' }}
                      </button>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>

        <div v-if="addingItemId === item.id" class="inline-panel">
          <div class="editor-grid">
            <label class="field">
              <span>重量</span>
              <input v-model.number="addForm.actual_weight" type="number" step="0.5" class="text-input" />
            </label>
            <label class="field">
              <span>次数</span>
              <input v-model.number="addForm.actual_reps" type="number" min="0" class="text-input" />
            </label>
            <label class="field">
              <span>RIR</span>
              <input v-model.number="addForm.actual_rir" type="number" min="0" class="text-input" />
            </label>
            <label class="field notes-field">
              <span>备注</span>
              <input v-model="addForm.notes" type="text" class="text-input" />
            </label>
          </div>
          <div class="editor-actions">
            <button class="secondary-btn small-btn" type="button" @click="cancelAdd">取消</button>
            <button
              class="primary-btn small-btn"
              type="button"
              :disabled="savingItemId === item.id"
              @click="saveAdd(item.id)"
            >
              {{ savingItemId === item.id ? '补录中...' : '确认补录' }}
            </button>
          </div>
        </div>
      </article>

      <section v-if="session.edit_logs?.length" class="log-panel">
        <div class="log-head">
          <strong>课后修改日志</strong>
          <span>{{ session.edit_logs.length }} 条</span>
        </div>
        <div class="log-list">
          <article v-for="log in session.edit_logs" :key="log.id" class="log-item">
            <strong>{{ log.summary }}</strong>
            <p>{{ formatActorName(log.actor_name) }} · {{ formatDateTime(log.edited_at || log.created_at) }}</p>
          </article>
        </div>
      </section>
    </div>
  </details>
</template>

<style scoped>
.session-card{border:1px solid var(--line);border-radius:20px;background:white;overflow:hidden}
.session-head{list-style:none;display:flex;justify-content:space-between;align-items:flex-start;gap:16px;padding:18px 20px;cursor:pointer}
.session-head::-webkit-details-marker{display:none}
.session-copy,.item-copy{min-width:0;flex:1}
.session-date,.item-head p,.item-note,.log-item p{margin:0;color:var(--text-soft)}
.session-head h4,.item-head h5{margin:4px 0 0}
.session-meta{display:flex;flex-wrap:wrap;gap:8px;justify-content:flex-end;color:var(--text-soft);font-size:14px}
.session-action{align-self:center}
.status-chip,.item-badge,.decision-pill{padding:6px 10px;border-radius:999px;font-size:13px}
.status-chip.success{background:#dcfce7;color:#166534}
.status-chip.progress{background:#dbeafe;color:#1d4ed8}
.status-chip.partial{background:#ffedd5;color:#c2410c}
.status-chip.neutral{background:#e5e7eb;color:#374151}
.status-chip.danger{background:#fee2e2;color:#b91c1c}
.status-chip.warning{background:#fef3c7;color:#92400e}
.item-badge{background:var(--panel-soft);color:var(--text);flex-shrink:0}
.item-badge.main{background:rgba(251,191,36,.18);color:#92400e}
.decision-pill.accepted{background:rgba(34,197,94,.16);color:#166534}
.decision-pill.guided{background:rgba(59,130,246,.14);color:#1d4ed8}
.decision-pill.modified{background:rgba(239,68,68,.12);color:#b91c1c}
.session-body{padding:0 20px 20px;display:grid;gap:14px}
.feedback-panel{display:grid;gap:10px;padding:16px;border-radius:16px;background:rgba(15,118,110,.06);border:1px solid rgba(15,118,110,.12)}
.feedback-head{display:flex;justify-content:space-between;gap:12px;align-items:center;flex-wrap:wrap}
.feedback-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.feedback-metric{display:grid;gap:6px;padding:12px;border-radius:14px;background:white}
.feedback-metric span,.feedback-note{margin:0;color:var(--text-soft)}
.feedback-note{font-size:14px}
.danger-note{color:#b91c1c;font-weight:700}
.detail-state{padding:12px 14px;border-radius:14px;background:rgba(15,23,42,.04);color:var(--text-soft);display:flex;align-items:center;gap:12px;justify-content:space-between}
.item-card{border-radius:18px;background:var(--panel-soft);padding:16px;display:grid;gap:12px}
.item-head{display:flex;align-items:flex-start;justify-content:space-between;gap:16px}
.item-actions{display:flex;flex-wrap:wrap;justify-content:flex-end;align-items:center;gap:8px}
.record-table-wrap{overflow:auto}
.record-table{width:100%;border-collapse:collapse}
.record-table th,.record-table td{padding:10px 8px;text-align:left;border-bottom:1px solid var(--line);white-space:nowrap}
.link-btn{border:none;background:transparent;color:#0f766e;font-weight:600;cursor:pointer;padding:0}
.danger-link{margin-left:10px;color:#b91c1c}
.editor-row td{background:rgba(15,118,110,.05)}
.editor-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}
.field{display:grid;gap:6px;min-width:0}
.field span{font-size:13px;color:var(--text-soft)}
.notes-field{grid-column:span 1}
.editor-actions{display:flex;justify-content:flex-end;gap:10px;margin-top:12px}
.inline-panel{border:1px dashed rgba(15,118,110,.28);border-radius:16px;padding:14px;background:rgba(255,255,255,.7)}
.log-panel{border-top:1px solid var(--line);padding-top:12px;display:grid;gap:10px}
.log-head{display:flex;justify-content:space-between;gap:12px;align-items:center}
.log-list{display:grid;gap:8px}
.log-item{padding:12px 14px;border-radius:14px;background:rgba(15,23,42,.04)}

@media (max-width: 960px) {
  .editor-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .feedback-grid{grid-template-columns:1fr}
}
</style>
