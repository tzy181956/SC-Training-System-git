<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps<{
  item: any | null
  suggestion?: any | null
  onSubmitCurrentSet?: ((payload: Record<string, unknown>) => Promise<any>) | null
  onUpdateRecord?: ((recordId: number, payload: Record<string, unknown>) => Promise<any>) | null
  onReturnToActionList?: (() => void) | null
}>()

const currentDraft = reactive({
  weight: '',
  reps: '',
  rir: '',
})
const currentDraftDirty = ref(false)
const currentSetSaving = ref(false)
const currentSetError = ref('')
const currentSetFeedback = ref('')
const currentWeightInput = ref<HTMLInputElement | null>(null)
const currentRepsInput = ref<HTMLInputElement | null>(null)
const RIR_OPTIONS = [0, 1, 2, 3, 4] as const

const historyPanelOpen = ref(false)
const savingRecordId = ref<number | null>(null)
const expandedRecordId = ref<number | null>(null)
const recordError = ref('')
const recordDrafts = reactive<Record<number, { weight: string; reps: string; rir: string; dirty: boolean }>>({})

const isCompleted = computed(() => {
  if (!props.item) return false
  return props.item.status === 'completed' || (props.item.records?.length || 0) >= props.item.prescribed_sets
})

const latestRecord = computed(() => {
  const records = props.item?.records || []
  return records.length ? records[records.length - 1] : null
})

const completedSetCount = computed(() => props.item?.records?.length || 0)
const totalSetCount = computed(() => props.item?.prescribed_sets || 0)
const currentSetNumber = computed(() => Math.min((props.item?.records?.length || 0) + 1, props.item?.prescribed_sets || 1))
const hasSelectedCurrentRir = computed(() => toDraftString(currentDraft.rir).trim() !== '')
const canSubmitCurrentSet = computed(() => !currentSetSaving.value && !isCompleted.value && hasSelectedCurrentRir.value && Boolean(props.onSubmitCurrentSet))
const actionTitle = computed(() => props.item?.exercise?.name || '当前动作')
const actionStatusLabel = computed(() => {
  if (isCompleted.value) return '已完成'
  return '录入中'
})
const actionStatusTone = computed(() => {
  if (isCompleted.value) return 'completed'
  return 'active'
})
const currentRirDisplay = computed(() => {
  if (!hasSelectedCurrentRir.value) return '未选择'
  return currentDraft.rir === '4' ? '4+' : currentDraft.rir
})
const currentSetSubmitHint = computed(() => {
  if (currentSetSaving.value) return '正在本地确认当前组'
  if (!hasSelectedCurrentRir.value) return '先选择 RIR，再提交当前组'
  return '确认后立即保存到本机，后台自动同步'
})

const currentSetButtonLabel = computed(() => {
  if (!props.item) return '确认提交当前组'
  const completedSets = props.item.records?.length || 0
  return completedSets + 1 >= props.item.prescribed_sets ? '确认并完成当前动作' : '确认提交当前组'
})

const submitButtonLabel = computed(() => {
  if (currentSetSaving.value) return '正在确认...'
  if (isCompleted.value) return '动作已完成'
  if (!hasSelectedCurrentRir.value) return '请选择 RIR'
  return currentSetButtonLabel.value
})

watch(
  () => ({
    itemId: props.item?.id ?? null,
    recordCount: props.item?.records?.length ?? 0,
    initialLoad: props.item?.initial_load ?? null,
    prescribedReps: props.item?.prescribed_reps ?? null,
    latestRecordId: latestRecord.value?.id ?? null,
    latestWeight: latestRecord.value?.actual_weight ?? latestRecord.value?.final_weight ?? null,
    latestReps: latestRecord.value?.actual_reps ?? null,
    latestRir: latestRecord.value?.actual_rir ?? null,
  }),
  (nextState, previousState) => {
    if (!props.item) return

    const itemChanged = nextState.itemId !== previousState?.itemId
    const recordCountChanged = nextState.recordCount !== previousState?.recordCount

    if (!itemChanged && !recordCountChanged && currentDraftDirty.value) {
      return
    }

    applyCurrentDraftDefaults()
    currentDraftDirty.value = false
    currentSetError.value = ''
    currentSetFeedback.value = ''
  },
  { immediate: true },
)

watch(
  () => props.item?.records,
  (records) => {
    recordError.value = ''
    historyPanelOpen.value = false
    expandedRecordId.value = null
    for (const key of Object.keys(recordDrafts)) {
      delete recordDrafts[Number(key)]
    }
    for (const record of records || []) {
      recordDrafts[record.id] = {
        weight: formatWeight(record.actual_weight),
        reps: String(record.actual_reps),
        rir: String(record.actual_rir),
        dirty: false,
      }
    }
  },
  { immediate: true, deep: true },
)

function normalizeWeight(value: number) {
  return Math.round(value * 10) / 10
}

function formatWeight(value: number) {
  const normalized = normalizeWeight(value)
  return Number.isInteger(normalized) ? String(normalized) : normalized.toFixed(1)
}

function applyCurrentDraftDefaults() {
  if (!props.item) return

  if (latestRecord.value) {
    const inheritedWeight = latestRecord.value.actual_weight ?? latestRecord.value.final_weight
    currentDraft.weight = inheritedWeight === null || inheritedWeight === undefined ? '' : formatWeight(inheritedWeight)
    currentDraft.reps = String(latestRecord.value.actual_reps ?? props.item.prescribed_reps ?? 5)
    currentDraft.rir = ''
    return
  }

  currentDraft.weight =
    props.item.initial_load === null || props.item.initial_load === undefined ? '' : formatWeight(props.item.initial_load)
  currentDraft.reps = String(props.item.prescribed_reps || 5)
  currentDraft.rir = ''
}

function onCurrentDraftInput(field: 'weight' | 'reps', event: Event) {
  const target = event.target as HTMLInputElement | null
  currentDraft[field] = target?.value ?? ''
  onCurrentInput()
}

function onCurrentInput() {
  currentDraftDirty.value = true
  currentSetFeedback.value = ''
}

function onRecordInput(recordId: number) {
  if (!recordDrafts[recordId]) return
  recordDrafts[recordId].dirty = true
}

function parseDraftNumber(value: string, fallback: number) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : fallback
}

function bumpWeight(step: number) {
  const baseText = currentWeightInput.value?.value ?? currentDraft.weight
  const base = parseDraftNumber(baseText || '0', 0)
  currentDraft.weight = formatWeight(Math.max(0, base + step))
  currentDraftDirty.value = true
  currentSetFeedback.value = ''
}

function bumpCurrentField(field: 'reps', step: number) {
  if (field === 'reps') {
    const baseText = currentRepsInput.value?.value ?? currentDraft.reps
    const base = parseDraftNumber(baseText || '1', 1)
    currentDraft.reps = String(Math.max(1, Math.round(base + step)))
  }

  currentDraftDirty.value = true
  currentSetFeedback.value = ''
}

function setCurrentRirValue(value: number) {
  currentDraft.rir = String(Math.max(0, Math.min(4, Math.round(value))))
  currentDraftDirty.value = true
  currentSetFeedback.value = ''
}

function bumpRecordField(recordId: number, field: 'weight' | 'reps', step: number) {
  const draft = recordDrafts[recordId]
  if (!draft) return

  if (field === 'weight') {
    const base = Number(draft.weight || 0)
    draft.weight = formatWeight(Math.max(0, base + step))
  }

  if (field === 'reps') {
    const base = Number(draft.reps || 0)
    draft.reps = String(Math.max(1, Math.round(base + step)))
  }

  draft.dirty = true
}

function setRecordRirValue(recordId: number, value: number) {
  const draft = recordDrafts[recordId]
  if (!draft) return
  draft.rir = String(Math.max(0, Math.min(4, Math.round(value))))
  draft.dirty = true
}

function toDraftString(value: unknown) {
  return value === null || value === undefined ? '' : String(value)
}

function toggleRecordExpanded(recordId: number) {
  expandedRecordId.value = expandedRecordId.value === recordId ? null : recordId
}

function isRecordExpanded(recordId: number) {
  return expandedRecordId.value === recordId
}

function toggleHistoryPanel() {
  historyPanelOpen.value = !historyPanelOpen.value
  if (!historyPanelOpen.value) {
    expandedRecordId.value = null
  }
}

function formatRecordSummary(recordId: number) {
  const draft = recordDrafts[recordId]
  if (!draft) return ''
  return `${draft.weight || '-'} 千克 · ${draft.reps || '-'} 次 · RIR（还能做几个） ${draft.rir || '-'}`
}

function validateCurrentDraft() {
  const weightText = toDraftString(currentDraft.weight).trim()
  const repsText = toDraftString(currentDraft.reps).trim()
  const rirText = toDraftString(currentDraft.rir).trim()
  const weight = Number(weightText)
  const reps = Number(repsText)
  const rir = Number(rirText)

  if (!weightText || Number.isNaN(weight) || weight < 0) {
    return { error: '当前组重量必须是大于等于 0 的数字。' }
  }
  if (!Number.isInteger(reps) || reps <= 0) {
    return { error: '当前组次数必须是正整数。' }
  }
  if (!rirText) {
    return { error: '请先手动选择当前组 RIR（还能做几个）。' }
  }
  if (!Number.isInteger(rir) || rir < 0 || rir > 4) {
    return { error: '当前组 RIR（还能做几个）请输入 0 到 4。' }
  }

  return {
    payload: {
      actual_weight: normalizeWeight(weight),
      actual_reps: reps,
      actual_rir: rir,
      final_weight: normalizeWeight(weight),
    },
  }
}

async function saveCurrentSet() {
  if (!props.item || currentSetSaving.value || isCompleted.value) return

  const result = validateCurrentDraft()
  if (!('payload' in result) || !result.payload || !props.onSubmitCurrentSet) {
    currentSetError.value = result.error || '当前组数据无效，请检查后重试。'
    currentSetFeedback.value = ''
    return
  }

  currentSetError.value = ''
  currentSetSaving.value = true
  try {
    const response = await props.onSubmitCurrentSet(result.payload)
    currentDraftDirty.value = false
    currentSetFeedback.value =
      response?.local_only
        ? response?.item?.status === 'completed'
          ? '已保存到本机，后台会继续补传，当前动作已完成。'
          : `已保存到本机，后台同步中，第 ${(response?.item?.records?.length || 0) + 1} 组可继续录入。`
        : response?.item?.status === 'completed'
          ? '已保存，当前动作已完成。'
          : `已保存，第 ${(response?.item?.records?.length || 0) + 1} 组可继续录入。`
  } catch {
    currentSetError.value = '当前组本地保存失败，请重试。'
    currentSetFeedback.value = ''
  } finally {
    currentSetSaving.value = false
  }
}

function validateRecordDraft(record: any) {
  const draft = recordDrafts[record.id]
  if (!draft) return { error: '未找到当前历史组。' }

  const weightText = toDraftString(draft.weight).trim()
  const repsText = toDraftString(draft.reps).trim()
  const rirText = toDraftString(draft.rir).trim()
  const weight = Number(weightText)
  const reps = Number(repsText)
  const rir = Number(rirText)

  if (!weightText || Number.isNaN(weight) || weight < 0) {
    return { error: `第 ${record.set_number} 组重量必须是大于等于 0 的数字。` }
  }
  if (!Number.isInteger(reps) || reps <= 0) {
    return { error: `第 ${record.set_number} 组次数必须是正整数。` }
  }
  if (!Number.isInteger(rir) || rir < 0 || rir > 4) {
    return { error: `第 ${record.set_number} 组 RIR（还能做几个）请输入 0 到 4。` }
  }

  return {
    payload: {
      actual_weight: normalizeWeight(weight),
      actual_reps: reps,
      actual_rir: rir,
      final_weight: normalizeWeight(weight),
      notes: record.notes,
    },
  }
}

async function saveRecord(record: any, event: FocusEvent) {
  const currentTarget = event.currentTarget as HTMLElement | null
  const nextTarget = event.relatedTarget as Node | null
  if (currentTarget && nextTarget && currentTarget.contains(nextTarget)) return
  if (!recordDrafts[record.id]?.dirty || savingRecordId.value === record.id || !props.onUpdateRecord) return

  const result = validateRecordDraft(record)
  if (!('payload' in result) || !result.payload) {
    recordError.value = result.error || '历史组数据无效，请检查后重试。'
    resetRecordDraft(record)
    return
  }

  recordError.value = ''
  savingRecordId.value = record.id
  try {
    await props.onUpdateRecord(record.id, result.payload)
    recordDrafts[record.id].dirty = false
  } catch {
    recordError.value = '修改失败，请重试。'
    resetRecordDraft(record)
  } finally {
    savingRecordId.value = null
  }
}

function resetRecordDraft(record: any) {
  recordDrafts[record.id] = {
    weight: formatWeight(record.actual_weight),
    reps: String(record.actual_reps),
    rir: String(record.actual_rir),
    dirty: false,
  }
}
</script>

<template>
  <aside
    class="panel touch-panel"
    data-testid="training-set-panel"
    :data-current-exercise="item?.exercise?.name || ''"
    :data-record-count="item?.records?.length || 0"
    :data-item-status="item?.status || ''"
  >
    <div v-if="item" class="panel-head">
      <div class="panel-title-block">
        <p class="section-title">当前动作录入</p>
        <strong class="action-title">{{ actionTitle }}</strong>
        <span class="set-progress-title">
          {{ isCompleted ? `已完成 ${completedSetCount}/${totalSetCount} 组` : `第 ${currentSetNumber} 组 / 共 ${item.prescribed_sets} 组` }}
        </span>
      </div>
      <span class="action-status-pill" :class="`action-status-pill--${actionStatusTone}`">{{ actionStatusLabel }}</span>
    </div>
    <div v-else class="empty-state">
      <strong>请选择一个训练动作。</strong>
      <span>选择后可录入当前组并查看已提交组数据。</span>
    </div>

    <template v-if="item">
      <div class="metric-block">
        <div class="block-header">
          <strong>当前组数据</strong>
          <span>{{ isCompleted ? '当前动作已收口' : currentSetSubmitHint }}</span>
        </div>

        <div v-if="isCompleted" class="completion-card">
          <strong>当前动作已完成</strong>
          <span>{{ currentSetFeedback || `已完成 ${completedSetCount}/${item.prescribed_sets} 组，可返回动作列表选择下一项。` }}</span>
          <button class="secondary-btn completion-return-btn" type="button" @click="onReturnToActionList && onReturnToActionList()">
            返回动作列表
          </button>
        </div>

        <div v-else class="current-stack">
          <div class="field">
            <span>重量 (千克)</span>
            <div class="inline-stepper">
              <button
                class="secondary-btn touch-btn step-btn inline-stepper-btn step-btn--minus"
                data-testid="current-set-weight-decrement"
                type="button"
                @click="bumpWeight(-2.5)"
              >
                -2.5
              </button>
              <input
                ref="currentWeightInput"
                :value="currentDraft.weight"
                class="text-input current-input inline-stepper-input"
                data-testid="current-set-weight"
                type="number"
                step="0.1"
                min="0"
                @input="onCurrentDraftInput('weight', $event)"
              />
              <button
                class="secondary-btn touch-btn step-btn inline-stepper-btn step-btn--plus"
                data-testid="current-set-weight-increment"
                type="button"
                @click="bumpWeight(2.5)"
              >
                +2.5
              </button>
            </div>
          </div>

          <div class="field">
            <span>次数</span>
            <div class="inline-stepper">
              <button
                class="secondary-btn touch-btn step-btn inline-stepper-btn"
                data-testid="current-set-reps-decrement"
                type="button"
                @click="bumpCurrentField('reps', -1)"
              >
                -1
              </button>
              <input
                ref="currentRepsInput"
                :value="currentDraft.reps"
                class="text-input current-input inline-stepper-input"
                data-testid="current-set-reps"
                type="number"
                step="1"
                min="1"
                @input="onCurrentDraftInput('reps', $event)"
              />
              <button
                class="secondary-btn touch-btn step-btn inline-stepper-btn"
                data-testid="current-set-reps-increment"
                type="button"
                @click="bumpCurrentField('reps', 1)"
              >
                +1
              </button>
            </div>
          </div>

          <label class="field">
            <div class="rir-label-row">
              <span>RIR（还能做几个）</span>
              <strong :class="{ selected: hasSelectedCurrentRir }">{{ currentRirDisplay }}</strong>
            </div>
            <div class="step-row rir-step-row">
              <button
                v-for="rirValue in RIR_OPTIONS"
                :key="`current-rir-${rirValue}`"
                class="secondary-btn touch-btn step-btn rir-btn"
                :class="{ active: currentDraft.rir === String(rirValue) }"
                data-testid="current-set-rir"
                :data-rir-value="rirValue"
                type="button"
                @click="setCurrentRirValue(rirValue)"
              >
                {{ rirValue === 4 ? '4+' : rirValue }}
              </button>
            </div>
          </label>
        </div>

        <div v-if="!isCompleted" class="submit-bar">
          <p v-if="currentSetError" class="error-text">{{ currentSetError }}</p>
          <p v-else-if="currentSetFeedback" class="success-text">{{ currentSetFeedback }}</p>
          <button class="primary-btn confirm-btn" data-testid="submit-current-set" :disabled="!canSubmitCurrentSet" @click="saveCurrentSet">
            {{ submitButtonLabel }}
          </button>
        </div>
      </div>

      <div v-if="suggestion" class="suggestion-card">
        <p class="section-title">下一组建议</p>
        <strong>{{ suggestion.suggestion_weight }} 千克 / {{ item.prescribed_reps }} 次</strong>
        <span>{{ suggestion.reason_text }}</span>
      </div>

      <div v-if="item.records?.length" class="history-block">
        <button class="history-panel-toggle" type="button" @click="toggleHistoryPanel">
          <div class="history-head">
            <strong>已提交组数据</strong>
            <span>{{ historyPanelOpen ? '收起历史组编辑' : '展开后选择具体组进行修改' }}</span>
          </div>
          <span class="history-row-caret history-panel-caret" :class="{ expanded: historyPanelOpen }">▾</span>
        </button>

        <div v-if="historyPanelOpen" class="history-panel-body">
          <div class="history-selector">
            <button
              v-for="record in item.records"
              :key="`record-select-${record.id}`"
              class="secondary-btn touch-btn history-selector-btn"
              :class="{ active: isRecordExpanded(record.id) }"
              data-testid="history-record-selector"
              :data-set-number="record.set_number"
              type="button"
              @click="toggleRecordExpanded(record.id)"
            >
              <strong>第 {{ record.set_number }} 组</strong>
              <span>{{ formatRecordSummary(record.id) }}</span>
            </button>
          </div>

          <p v-if="recordError" class="error-text">{{ recordError }}</p>

          <div
            v-for="record in item.records"
            v-show="isRecordExpanded(record.id)"
            :key="record.id"
            class="history-row"
            :class="{ saving: savingRecordId === record.id, expanded: isRecordExpanded(record.id) }"
          >
            <div class="history-row-head">
              <strong class="set-label">第 {{ record.set_number }} 组</strong>
              <span class="row-status">{{ savingRecordId === record.id ? '保存中...' : '离开当前区域后自动保存' }}</span>
            </div>
            <div class="history-row-summary static">
              <span>{{ formatRecordSummary(record.id) }}</span>
            </div>

            <div class="history-stack" tabindex="-1" @focusout="saveRecord(record, $event)">
              <label class="history-field">
                <span>重量</span>
                <input
                  v-model="recordDrafts[record.id].weight"
                  class="text-input history-input"
                  type="text"
                  inputmode="decimal"
                  @input="onRecordInput(record.id)"
                />
                <div class="step-row">
                  <button class="secondary-btn touch-btn history-step-btn step-btn--minus" type="button" @click="bumpRecordField(record.id, 'weight', -5)">-5</button>
                  <button class="secondary-btn touch-btn history-step-btn step-btn--minus" type="button" @click="bumpRecordField(record.id, 'weight', -2.5)">-2.5</button>
                  <button class="secondary-btn touch-btn history-step-btn step-btn--plus" type="button" @click="bumpRecordField(record.id, 'weight', 2.5)">+2.5</button>
                  <button class="secondary-btn touch-btn history-step-btn step-btn--plus" type="button" @click="bumpRecordField(record.id, 'weight', 5)">+5</button>
                </div>
              </label>

              <label class="history-field">
                <span>组数</span>
                <input class="text-input history-input readonly-input" type="text" :value="record.set_number" readonly />
              </label>

              <label class="history-field">
                <span>次数</span>
                <input
                  v-model="recordDrafts[record.id].reps"
                  class="text-input history-input"
                  type="text"
                  inputmode="numeric"
                  @input="onRecordInput(record.id)"
                />
                <div class="step-row step-row-compact">
                  <button class="secondary-btn touch-btn history-step-btn" type="button" @click="bumpRecordField(record.id, 'reps', -1)">-1</button>
                  <button class="secondary-btn touch-btn history-step-btn" type="button" @click="bumpRecordField(record.id, 'reps', 1)">+1</button>
                </div>
              </label>

              <label class="history-field">
                <span>RIR（还能做几个）</span>
                <input
                  v-model="recordDrafts[record.id].rir"
                  class="text-input history-input"
                  type="text"
                  inputmode="numeric"
                  @input="onRecordInput(record.id)"
                />
                <div class="step-row rir-step-row">
                  <button
                    v-for="rirValue in RIR_OPTIONS"
                    :key="`history-rir-${record.id}-${rirValue}`"
                    class="secondary-btn touch-btn history-step-btn rir-btn"
                    :class="{ active: recordDrafts[record.id].rir === String(rirValue) }"
                    type="button"
                    @click="setRecordRirValue(record.id, rirValue)"
                  >
                    {{ rirValue === 4 ? '4+' : rirValue }}
                  </button>
                </div>
              </label>
            </div>
          </div>
        </div>
      </div>
    </template>
  </aside>
</template>

<style scoped>
.touch-panel {
  position: relative;
  display: grid;
  gap: 18px;
  align-content: start;
  height: 100%;
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.panel-head,
.metric-block,
.suggestion-card,
.empty-state,
.field,
.history-head {
  display: grid;
  gap: 10px;
}

.panel-head {
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 14px;
}

.panel-title-block {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.action-title {
  color: var(--text);
  font-size: 1.15rem;
  line-height: 1.2;
  font-weight: 900;
  overflow-wrap: anywhere;
}

.set-progress-title {
  color: var(--text-soft);
  font-size: 1.35rem;
  line-height: 1.18;
  font-weight: 900;
}

.action-status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 13px;
  line-height: 1;
  font-weight: 900;
  white-space: nowrap;
}

.action-status-pill--active {
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
}

.action-status-pill--saving {
  background: rgba(245, 158, 11, 0.14);
  color: #92400e;
}

.action-status-pill--completed {
  background: rgba(22, 163, 74, 0.12);
  color: #166534;
}

.section-title,
p,
span {
  margin: 0;
  color: var(--muted);
}

.block-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: baseline;
}

.current-stack,
.history-table {
  display: grid;
  gap: 14px;
}

.field span,
.history-field span,
.row-status {
  font-size: 12px;
  color: var(--muted);
}

.field input {
  min-height: 52px;
}

.current-input {
  min-height: 56px;
  padding: 0 12px;
  font-size: 22px;
  font-weight: 700;
}

.touch-btn {
  min-height: 56px;
  border-radius: 14px;
}

.confirm-btn {
  width: 100%;
  min-height: 64px;
  border-radius: 28px;
  font-size: 20px;
}

.confirm-btn:disabled {
  opacity: 1;
  filter: none;
  background: linear-gradient(180deg, #d8e9e6 0%, #bddbd6 100%);
  border-color: rgba(15, 118, 110, 0.18);
  color: #55736f;
}

.submit-bar {
  position: sticky;
  bottom: -18px;
  z-index: 2;
  display: grid;
  gap: 10px;
  padding: 14px 0 0;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0) 0%, var(--panel) 22%, var(--panel) 100%);
}

.completion-card {
  display: grid;
  gap: 12px;
  padding: 16px;
  border: 1px solid rgba(22, 163, 74, 0.18);
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(240, 253, 244, 0.96), rgba(236, 253, 245, 0.96));
}

.completion-card strong {
  color: #166534;
  font-size: 18px;
}

.completion-card span {
  color: #315c45;
  font-size: 14px;
  line-height: 1.45;
}

.completion-return-btn {
  min-height: 56px;
  border-radius: 18px;
}

.suggestion-card,
.history-block {
  background: #eff6ff;
  padding: 16px;
  border-radius: 16px;
}

.history-row {
  display: grid;
  gap: 12px;
  padding: 12px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.7);
  min-width: 0;
}

.history-row.expanded {
  background: rgba(255, 255, 255, 0.96);
  box-shadow: inset 0 0 0 1px rgba(15, 118, 110, 0.14);
}

.history-panel-toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 0;
  border: 0;
  background: transparent;
  text-align: left;
  cursor: pointer;
}

.history-panel-body {
  display: grid;
  gap: 12px;
}

.history-selector {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 8px;
}

.history-selector-btn {
  display: grid;
  gap: 4px;
  min-height: 68px;
  padding: 10px 12px;
  text-align: left;
}

.history-selector-btn strong,
.history-selector-btn span {
  margin: 0;
}

.history-selector-btn strong {
  font-size: 15px;
  font-weight: 800;
}

.history-selector-btn span {
  color: var(--muted);
  font-size: 12px;
  line-height: 1.3;
}

.history-selector-btn.active {
  background: var(--primary);
  color: white;
  border-color: transparent;
}

.history-selector-btn.active span {
  color: rgba(255, 255, 255, 0.88);
}

.history-row.saving {
  opacity: 0.7;
}

.history-row-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.history-row-summary {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
}

.history-row-summary.static {
  justify-content: flex-start;
}

.history-row-summary span:first-child {
  min-width: 0;
}

.history-row-caret {
  flex-shrink: 0;
  color: var(--muted);
  transition: transform 0.18s ease;
}

.history-row-caret.expanded {
  transform: rotate(180deg);
}

.history-panel-caret {
  align-self: flex-start;
  margin-top: 2px;
}

.history-stack {
  display: grid;
  gap: 14px;
}

.history-field {
  display: grid;
  gap: 8px;
}

.history-input {
  min-height: 56px;
  padding: 0 16px;
  font-size: 18px;
}

.readonly-input {
  background: #f8fafc;
  color: var(--text);
}

.rir-label-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.rir-label-row strong {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  min-height: 32px;
  padding: 0 10px;
  border-radius: 999px;
  background: #f1f5f9;
  color: var(--text-soft);
  font-size: 14px;
  font-weight: 900;
}

.rir-label-row strong.selected {
  background: var(--primary);
  color: white;
}

.step-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.inline-stepper {
  display: grid;
  grid-template-columns: minmax(72px, 0.45fr) minmax(86px, 1fr) minmax(72px, 0.45fr);
  align-items: center;
  gap: 8px;
}

.inline-stepper-input {
  min-width: 0;
  text-align: center;
}

.inline-stepper-btn {
  min-width: 0;
  padding-inline: 10px;
}

.step-row-compact {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.rir-step-row {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.step-btn,
.history-step-btn {
  min-height: 56px;
  font-size: 18px;
}

.step-btn--minus {
  background: linear-gradient(180deg, #fff7f7 0%, #fef2f2 100%);
  border-color: rgba(185, 28, 28, 0.22);
  color: #b91c1c;
  box-shadow: 0 10px 20px rgba(185, 28, 28, 0.07);
}

.step-btn--plus {
  background: linear-gradient(180deg, #f0fdf4 0%, #dcfce7 100%);
  border-color: rgba(22, 101, 52, 0.2);
  color: #166534;
  box-shadow: 0 10px 20px rgba(22, 101, 52, 0.08);
}

.rir-btn {
  min-height: 56px;
  padding: 0 6px;
  border-radius: 14px;
  font-size: 18px;
  line-height: 1;
}

.rir-btn.active {
  background: var(--primary);
  color: white;
  border-color: transparent;
}

.set-label {
  font-size: 18px;
}

.error-text {
  color: #b91c1c;
  font-size: 13px;
}

.success-text {
  color: #166534;
  font-size: 13px;
}

@media (min-width: 900px) and (max-width: 1199px) and (orientation: landscape) {
  .touch-panel {
    gap: 12px;
  }

  .panel-head,
  .metric-block,
  .suggestion-card,
  .empty-state,
  .field,
  .history-head {
    gap: 8px;
  }

  .panel-head {
    gap: 10px;
  }

  .action-title {
    font-size: 1.08rem;
  }

  .set-progress-title {
    font-size: 1.2rem;
  }

  .action-status-pill {
    min-height: 30px;
    padding-inline: 10px;
    font-size: 12px;
  }

  .block-header {
    display: grid;
    gap: 4px;
  }

  .current-stack,
  .history-table {
    gap: 10px;
  }

  .current-input,
  .history-input {
    min-height: 56px;
    padding: 0 12px;
    font-size: 20px;
  }

  .touch-btn {
    min-height: 50px;
    border-radius: 12px;
  }

  .confirm-btn {
    min-height: 58px;
    font-size: 18px;
  }

  .suggestion-card,
  .history-block {
    padding: 12px;
    border-radius: 14px;
  }

  .history-row {
    gap: 10px;
    padding: 12px;
  }

  .history-stack {
    gap: 10px;
  }

  .step-row {
    gap: 6px;
  }

  .inline-stepper {
    grid-template-columns: minmax(62px, 0.44fr) minmax(78px, 1fr) minmax(62px, 0.44fr);
    gap: 6px;
  }

  .rir-btn {
    min-height: 48px;
    border-radius: 12px;
    font-size: 16px;
  }
}

@media (min-width: 900px) and (max-width: 1050px) and (orientation: landscape) {
  .touch-panel {
    gap: 10px;
  }

  .current-input,
  .history-input {
    min-height: 54px;
    font-size: 20px;
  }

  .touch-btn {
    min-height: 48px;
  }

  .confirm-btn {
    min-height: 56px;
    font-size: 17px;
  }

  .submit-bar {
    bottom: -12px;
    gap: 8px;
    padding-top: 10px;
  }

  .suggestion-card,
  .history-block {
    padding: 10px;
  }

  .step-row {
    gap: 5px;
  }

  .inline-stepper {
    grid-template-columns: minmax(58px, 0.44fr) minmax(72px, 1fr) minmax(58px, 0.44fr);
    gap: 5px;
  }

  .step-btn,
  .history-step-btn {
    min-height: 48px;
    font-size: 16px;
  }

  .rir-btn {
    min-height: 46px;
    font-size: 15px;
  }
}

@media (max-width: 767px) {
  .inline-stepper {
    grid-template-columns: minmax(64px, 0.45fr) minmax(82px, 1fr) minmax(64px, 0.45fr);
  }

  .step-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .rir-step-row {
    grid-template-columns: repeat(5, minmax(0, 1fr));
  }
}
</style>
