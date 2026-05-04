<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

const props = defineProps<{
  item: any | null
  suggestion?: any | null
  onSubmitCurrentSet?: ((payload: Record<string, unknown>) => Promise<any>) | null
  onUpdateRecord?: ((recordId: number, payload: Record<string, unknown>) => Promise<any>) | null
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
const RIR_OPTIONS = [0, 1, 2, 3, 4] as const

const savingRecordId = ref<number | null>(null)
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

const currentSetNumber = computed(() => Math.min((props.item?.records?.length || 0) + 1, props.item?.prescribed_sets || 1))

const currentSetButtonLabel = computed(() => {
  if (!props.item) return '确认提交当前组'
  const completedSets = props.item.records?.length || 0
  return completedSets + 1 >= props.item.prescribed_sets ? '确认并完成当前动作' : '确认提交当前组'
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
    currentDraft.rir = String(latestRecord.value.actual_rir ?? 2)
    return
  }

  currentDraft.weight =
    props.item.initial_load === null || props.item.initial_load === undefined ? '' : formatWeight(props.item.initial_load)
  currentDraft.reps = String(props.item.prescribed_reps || 5)
  currentDraft.rir = '2'
}

function onCurrentInput() {
  currentDraftDirty.value = true
  currentSetFeedback.value = ''
}

function onRecordInput(recordId: number) {
  if (!recordDrafts[recordId]) return
  recordDrafts[recordId].dirty = true
}

function bumpWeight(step: number) {
  const base = Number(currentDraft.weight || 0)
  currentDraft.weight = formatWeight(Math.max(0, base + step))
  currentDraftDirty.value = true
  currentSetFeedback.value = ''
}

function bumpCurrentField(field: 'reps', step: number) {
  if (field === 'reps') {
    const base = Number(currentDraft.reps || 0)
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

function validateCurrentDraft() {
  const weight = Number(currentDraft.weight.trim())
  const reps = Number(currentDraft.reps.trim())
  const rir = Number(currentDraft.rir.trim())

  if (!currentDraft.weight.trim() || Number.isNaN(weight) || weight < 0) {
    return { error: '当前组重量必须是大于等于 0 的数字。' }
  }
  if (!Number.isInteger(reps) || reps <= 0) {
    return { error: '当前组次数必须是正整数。' }
  }
  if (!Number.isInteger(rir) || rir < 0 || rir > 4) {
    return { error: '当前组 RIR 请输入 0 到 4。' }
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
          : `已保存到本机，后台会继续补传，第 ${(response?.item?.records?.length || 0) + 1} 组可继续录入。`
        : response?.item?.status === 'completed'
          ? '已保存，当前动作已完成。'
          : `已保存，第 ${(response?.item?.records?.length || 0) + 1} 组可继续录入。`
  } catch {
    currentSetError.value = '当前组保存失败，请重试。'
    currentSetFeedback.value = ''
  } finally {
    currentSetSaving.value = false
  }
}

function validateRecordDraft(record: any) {
  const draft = recordDrafts[record.id]
  if (!draft) return { error: '未找到当前历史组。' }

  const weight = Number(draft.weight.trim())
  const reps = Number(draft.reps.trim())
  const rir = Number(draft.rir.trim())

  if (!draft.weight.trim() || Number.isNaN(weight) || weight < 0) {
    return { error: `第 ${record.set_number} 组重量必须是大于等于 0 的数字。` }
  }
  if (!Number.isInteger(reps) || reps <= 0) {
    return { error: `第 ${record.set_number} 组次数必须是正整数。` }
  }
  if (!Number.isInteger(rir) || rir < 0 || rir > 4) {
    return { error: `第 ${record.set_number} 组 RIR 请输入 0 到 4。` }
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
  <aside class="panel touch-panel">
    <div v-if="item" class="panel-head">
      <p class="section-title">当前动作录入</p>
      <strong>第 {{ currentSetNumber }} 组 / 共 {{ item.prescribed_sets }} 组</strong>
    </div>
    <div v-else class="empty-state">
      <strong>先从中间选择一个训练动作。</strong>
      <span>右侧会显示该动作的实时录入区和已提交组数据。</span>
    </div>

    <template v-if="item">
      <div class="metric-block">
        <div class="block-header">
          <strong>当前组数据</strong>
          <span>{{ currentSetSaving ? '正在保存当前组...' : '确认后保存到训练记录' }}</span>
        </div>

        <div class="current-stack">
          <label class="field">
            <span>重量 (公斤)</span>
            <input v-model="currentDraft.weight" class="text-input current-input" type="number" step="0.1" min="0" @input="onCurrentInput" />
            <div class="step-row">
              <button v-for="step in [-5, -2.5, 2.5, 5]" :key="`current-weight-${step}`" class="secondary-btn touch-btn step-btn" @click="bumpWeight(step)">
                {{ step > 0 ? `+${step}` : step }}
              </button>
            </div>
          </label>

          <label class="field">
            <span>次数</span>
            <input v-model="currentDraft.reps" class="text-input current-input" type="number" step="1" min="1" @input="onCurrentInput" />
            <div class="step-row step-row-compact">
              <button class="secondary-btn touch-btn step-btn" type="button" @click="bumpCurrentField('reps', -1)">-1</button>
              <button class="secondary-btn touch-btn step-btn" type="button" @click="bumpCurrentField('reps', 1)">+1</button>
            </div>
          </label>

          <label class="field">
            <span>RIR</span>
            <input v-model="currentDraft.rir" class="text-input current-input" type="number" step="1" min="0" max="4" @input="onCurrentInput" />
            <div class="step-row rir-step-row">
              <button
                v-for="rirValue in RIR_OPTIONS"
                :key="`current-rir-${rirValue}`"
                class="secondary-btn touch-btn step-btn rir-btn"
                :class="{ active: currentDraft.rir === String(rirValue) }"
                type="button"
                @click="setCurrentRirValue(rirValue)"
              >
                {{ rirValue === 4 ? '4+' : rirValue }}
              </button>
            </div>
          </label>
        </div>

        <p v-if="currentSetError" class="error-text">{{ currentSetError }}</p>
        <p v-else-if="currentSetFeedback" class="success-text">{{ currentSetFeedback }}</p>
        <button class="primary-btn confirm-btn" :disabled="currentSetSaving || isCompleted" @click="saveCurrentSet">
          {{ currentSetButtonLabel }}
        </button>
      </div>

      <div v-if="suggestion" class="suggestion-card">
        <p class="section-title">下一组建议</p>
        <strong>{{ suggestion.suggestion_weight }} 公斤 / {{ item.prescribed_reps }} 次</strong>
        <span>{{ suggestion.reason_text }}</span>
      </div>

      <div v-if="item.records?.length" class="history-block">
        <div class="history-head">
          <strong>已提交组数据</strong>
          <span>直接修改输入框，离开这一组后自动保存。</span>
        </div>
        <p v-if="recordError" class="error-text">{{ recordError }}</p>

        <div class="history-table">
          <div
            v-for="record in item.records"
            :key="record.id"
            class="history-row"
            :class="{ saving: savingRecordId === record.id }"
            tabindex="-1"
            @focusout="saveRecord(record, $event)"
          >
            <div class="history-row-head">
              <strong class="set-label">第 {{ record.set_number }} 组</strong>
              <span class="row-status">{{ savingRecordId === record.id ? '保存中...' : '已同步' }}</span>
            </div>

            <div class="history-stack">
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
                  <button class="secondary-btn touch-btn history-step-btn" type="button" @click="bumpRecordField(record.id, 'weight', -5)">-5</button>
                  <button class="secondary-btn touch-btn history-step-btn" type="button" @click="bumpRecordField(record.id, 'weight', -2.5)">-2.5</button>
                  <button class="secondary-btn touch-btn history-step-btn" type="button" @click="bumpRecordField(record.id, 'weight', 2.5)">+2.5</button>
                  <button class="secondary-btn touch-btn history-step-btn" type="button" @click="bumpRecordField(record.id, 'weight', 5)">+5</button>
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
                <span>RIR</span>
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
  gap: 10px;
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
  padding: 0 16px;
  font-size: 18px;
}

.touch-btn {
  min-height: 52px;
  border-radius: 14px;
}

.confirm-btn {
  min-height: 56px;
}

.suggestion-card,
.history-block {
  background: #eff6ff;
  padding: 16px;
  border-radius: 16px;
}

.history-row {
  display: grid;
  gap: 14px;
  padding: 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.7);
  min-width: 0;
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

.step-row {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.step-row-compact {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.rir-step-row {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.step-btn,
.history-step-btn {
  min-height: 48px;
}

.rir-btn {
  min-height: 38px;
  padding: 0 6px;
  border-radius: 10px;
  font-size: 13px;
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

@media (min-width: 768px) and (max-width: 1199px) {
  .touch-panel {
    gap: 12px;
  }

  .current-input,
  .history-input {
    min-height: 48px;
    padding: 0 12px;
    font-size: 16px;
  }

  .touch-btn {
    min-height: 44px;
    border-radius: 12px;
  }

  .confirm-btn {
    min-height: 48px;
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

  .rir-btn {
    min-height: 34px;
    border-radius: 9px;
    font-size: 12px;
  }
}

@media (max-width: 767px) {
  .step-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
