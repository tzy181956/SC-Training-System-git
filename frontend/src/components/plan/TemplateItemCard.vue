<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

const props = defineProps<{
  item: any
  exercises: any[]
}>()

const emit = defineEmits<{
  change: [itemId: number, payload: Record<string, unknown>]
  remove: [itemId: number]
  move: [itemId: number, direction: 'up' | 'down']
}>()

const draft = reactive(buildDraft(props.item))
const level1Category = ref('')
const level2Category = ref('')
const comboOpen = ref(false)
const searchKeyword = ref('')
const comboRoot = ref<HTMLElement | null>(null)
const searchInput = ref<HTMLInputElement | null>(null)
let syncingFromProps = false

watch(
  () => props.item,
  (item) => {
    syncingFromProps = true
    Object.assign(draft, buildDraft(item))
    syncExercisePicker(item.exercise_id, item.exercise)
    queueMicrotask(() => {
      syncingFromProps = false
    })
  },
  { deep: true, immediate: true },
)

watch(
  () => props.exercises,
  () => {
    if (!draft.exercise_id) return
    syncExercisePicker(draft.exercise_id)
  },
  { deep: true },
)

watch(
  draft,
  () => {
    if (syncingFromProps) return
    emit('change', props.item.id, serializeDraft())
  },
  { deep: true },
)

const selectedExercise = computed(() => props.exercises.find((exercise) => exercise.id === draft.exercise_id))
const loadModeLabel = computed(() => (draft.initial_load_mode === 'percent_1rm' ? '按最近测试百分比' : '固定重量'))

const level1Options = computed(() =>
  Array.from(new Set(props.exercises.map((exercise) => normalizeString(exercise.level1_category)).filter(Boolean))).sort((left, right) =>
    left.localeCompare(right, 'zh-CN'),
  ),
)

const level2Options = computed(() =>
  Array.from(
    new Set(
      props.exercises
        .filter((exercise) => !level1Category.value || normalizeString(exercise.level1_category) === level1Category.value)
        .map((exercise) => normalizeString(exercise.level2_category))
        .filter(Boolean),
    ),
  ).sort((left, right) => left.localeCompare(right, 'zh-CN')),
)

const scopedExercises = computed(() =>
  props.exercises.filter((exercise) => {
    if (level1Category.value && normalizeString(exercise.level1_category) !== level1Category.value) return false
    if (level2Category.value && normalizeString(exercise.level2_category) !== level2Category.value) return false
    return true
  }),
)

const selectedExerciseLabel = computed(() =>
  selectedExercise.value ? formatExerciseOption(selectedExercise.value) : '',
)

const searchableExercises = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase()
  const source = scopedExercises.value
  const matched = keyword
    ? source.filter((exercise) =>
        [
          normalizeString(exercise.name),
          normalizeString(exercise.name_en),
          normalizeString(exercise.base_movement),
          normalizeString(exercise.level2_category),
        ]
          .join(' ')
          .toLowerCase()
          .includes(keyword),
      )
    : source

  return matched.slice(0, 200).map((exercise) => ({
    ...exercise,
    optionLabel: formatExerciseOption(exercise),
  }))
})

function buildDraft(item: any) {
  const rules = item.progression_rules || {}
  return {
    exercise_id: item.exercise_id,
    sort_order: item.sort_order,
    prescribed_sets: item.prescribed_sets,
    prescribed_reps: item.prescribed_reps,
    target_note: item.target_note || '',
    is_main_lift: item.is_main_lift,
    enable_auto_load: item.enable_auto_load,
    initial_load_mode: item.initial_load_mode || 'fixed_weight',
    initial_load_value: item.initial_load_value ?? 0,
    progression_goal: item.progression_goal || '',
    progression_rules: {
      target_rir: rules.target_rir ?? 2,
      up_step: rules.up_step ?? 2.5,
      down_step: rules.down_step ?? 2.5,
      miss_strategy: rules.miss_strategy || '降低重量后完成',
      fatigue_strategy: rules.fatigue_strategy || '连续吃力时停止加重',
    },
    ai_adjust_enabled: item.ai_adjust_enabled || false,
  }
}

function serializeDraft() {
  return {
    exercise_id: draft.exercise_id,
    sort_order: draft.sort_order,
    prescribed_sets: draft.prescribed_sets,
    prescribed_reps: draft.prescribed_reps,
    target_note: draft.target_note,
    is_main_lift: draft.is_main_lift,
    enable_auto_load: draft.enable_auto_load,
    initial_load_mode: draft.initial_load_mode,
    initial_load_value: draft.initial_load_value,
    progression_goal: draft.progression_goal,
    progression_rules: { ...draft.progression_rules },
    ai_adjust_enabled: draft.ai_adjust_enabled,
  }
}

function normalizeString(value: unknown) {
  return String(value || '').trim()
}

function formatExerciseOption(exercise: any) {
  const extras = [normalizeString(exercise.base_movement), normalizeString(exercise.level2_category)].filter(Boolean)
  return extras.length ? `${exercise.name} | ${extras.join(' | ')}` : exercise.name
}

function syncExercisePicker(exerciseId: number, fallbackExercise?: any) {
  const exercise = props.exercises.find((item) => item.id === exerciseId) || fallbackExercise || null
  level1Category.value = normalizeString(exercise?.level1_category)
  level2Category.value = normalizeString(exercise?.level2_category)
  searchKeyword.value = ''
}

function clearExerciseSelection() {
  draft.exercise_id = 0
  searchKeyword.value = ''
}

function handleLevel1Change(value: string) {
  level1Category.value = value
  level2Category.value = ''
  clearExerciseSelection()
}

function handleLevel2Change(value: string) {
  level2Category.value = value
  clearExerciseSelection()
}

function handleExerciseQueryInput(value: string) {
  searchKeyword.value = value
  const normalized = value.trim().toLowerCase()
  const exactMatch = searchableExercises.value.find((exercise) => exercise.optionLabel.trim().toLowerCase() === normalized)
  if (exactMatch) {
    selectExercise(exactMatch)
  }
}

function openCombobox() {
  comboOpen.value = true
  searchKeyword.value = ''
  nextTick(() => {
    searchInput.value?.focus()
  })
}

function closeCombobox() {
  comboOpen.value = false
  searchKeyword.value = ''
}

function toggleCombobox() {
  if (comboOpen.value) {
    closeCombobox()
    return
  }
  openCombobox()
}

function selectExercise(exercise: any) {
  draft.exercise_id = exercise.id
  closeCombobox()
}

function handleDocumentPointerDown(event: PointerEvent) {
  if (!comboOpen.value) return
  const target = event.target as Node | null
  if (!target || comboRoot.value?.contains(target)) return
  closeCombobox()
}

onMounted(() => {
  document.addEventListener('pointerdown', handleDocumentPointerDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
})
</script>

<template>
  <article class="item-card">
    <header class="item-header">
      <div class="item-copy adaptive-card">
        <p class="item-index">模板动作</p>
        <h4 class="adaptive-card-title">{{ selectedExercise?.name || item.exercise?.name || '未选择动作' }}</h4>
        <span class="muted adaptive-card-subtitle adaptive-card-clamp-2">{{ loadModeLabel }}</span>
      </div>
      <div class="header-actions">
        <button class="slim-btn" type="button" @click="emit('move', item.id, 'up')">上移</button>
        <button class="slim-btn" type="button" @click="emit('move', item.id, 'down')">下移</button>
        <button class="ghost-btn slim-btn danger" type="button" @click="emit('remove', item.id)">删除</button>
      </div>
    </header>

    <div class="picker-row">
      <label class="field">
        <span>一级分类</span>
        <select :value="level1Category" class="text-input" @change="handleLevel1Change(($event.target as HTMLSelectElement).value)">
          <option value="">全部一级分类</option>
          <option v-for="option in level1Options" :key="option" :value="option">{{ option }}</option>
        </select>
      </label>
      <label class="field">
        <span>二级分类</span>
        <select :value="level2Category" class="text-input" @change="handleLevel2Change(($event.target as HTMLSelectElement).value)">
          <option value="">全部二级分类</option>
          <option v-for="option in level2Options" :key="option" :value="option">{{ option }}</option>
        </select>
      </label>
      <label ref="comboRoot" class="field search-field">
        <span>动作搜索</span>
        <div class="combo-shell" :class="{ open: comboOpen }">
          <button class="combo-trigger" type="button" @click="toggleCombobox">
            <span class="combo-trigger-text">
              {{ selectedExerciseLabel || '请选择动作' }}
            </span>
            <span class="combo-trigger-arrow" aria-hidden="true">▾</span>
          </button>

          <div v-if="comboOpen" class="combo-panel">
            <input
              ref="searchInput"
              :value="searchKeyword"
              class="text-input combo-search-input"
              placeholder="输入动作名、英文名、基础动作或分类搜索"
              @input="handleExerciseQueryInput(($event.target as HTMLInputElement).value)"
            />
            <div class="combo-options">
              <button
                v-for="exercise in searchableExercises"
                :key="exercise.id"
                class="combo-option"
                :class="{ active: exercise.id === draft.exercise_id }"
                type="button"
                @click="selectExercise(exercise)"
              >
                {{ exercise.optionLabel }}
              </button>
              <p v-if="!searchableExercises.length" class="combo-empty">当前筛选条件下没有匹配动作</p>
            </div>
          </div>
        </div>
      </label>
    </div>

    <div class="metrics-row">
      <label class="field metric metric--count">
        <span>组数</span>
        <input v-model.number="draft.prescribed_sets" type="number" class="text-input" />
      </label>
      <label class="field metric metric--count">
        <span>次数</span>
        <input v-model.number="draft.prescribed_reps" type="number" class="text-input" />
      </label>
      <label class="field metric metric--load">
        <span>{{ draft.initial_load_mode === 'percent_1rm' ? '负荷 (%)' : '负荷' }}</span>
        <input v-model.number="draft.initial_load_value" type="number" step="0.5" class="text-input" />
      </label>
      <label class="field metric metric--mode">
        <span>负荷方式</span>
        <select v-model="draft.initial_load_mode" class="text-input">
          <option value="fixed_weight">固定重量</option>
          <option value="percent_1rm">按最近测试的 1RM 百分比</option>
        </select>
      </label>
      <label class="field metric metric--goal">
        <span>训练目标</span>
        <input v-model="draft.progression_goal" class="text-input" placeholder="例如：力量、速度、技术稳定" />
      </label>
    </div>

    <label class="field">
      <span>动作备注</span>
      <textarea
        v-model="draft.target_note"
        class="text-input note-input"
        rows="1"
        placeholder="例如：保持速度、注意动作深度、优先技术稳定"
      />
    </label>

    <div class="toggle-row">
      <label><input v-model="draft.is_main_lift" type="checkbox" /> 主项动作</label>
      <label><input v-model="draft.enable_auto_load" type="checkbox" /> 启用自动调重</label>
      <label><input v-model="draft.ai_adjust_enabled" type="checkbox" /> 预留 AI 调整</label>
    </div>

    <section v-if="draft.enable_auto_load" class="progress-panel">
      <div class="progress-head">
        <h5>进阶逻辑</h5>
        <span class="muted adaptive-card-subtitle adaptive-card-clamp-2">按动作单独设置 RIR、加重和回退规则</span>
      </div>
      <div class="grid two">
        <label class="field">
          <span>目标 RIR</span>
          <input v-model.number="draft.progression_rules.target_rir" type="number" min="0" max="5" class="text-input" />
        </label>
        <label class="field">
          <span>加重步长（公斤）</span>
          <input v-model.number="draft.progression_rules.up_step" type="number" step="0.5" class="text-input" />
        </label>
        <label class="field">
          <span>降重步长（公斤）</span>
          <input v-model.number="draft.progression_rules.down_step" type="number" step="0.5" class="text-input" />
        </label>
        <label class="field">
          <span>未完成时处理</span>
          <input v-model="draft.progression_rules.miss_strategy" class="text-input" />
        </label>
      </div>
      <label class="field">
        <span>连续吃力时处理</span>
        <input v-model="draft.progression_rules.fatigue_strategy" class="text-input" />
      </label>
    </section>
  </article>
</template>

<style scoped>
.item-card {
  display: grid;
  gap: 16px;
  padding: 18px;
  border-radius: 20px;
  background: var(--panel-soft);
  border: 1px solid rgba(15, 118, 110, 0.12);
}

.item-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
  flex: 1;
}

.item-header,
.header-actions,
.toggle-row,
.progress-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.item-index,
.muted {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
}

.item-header h4,
.progress-head h5 {
  margin: 4px 0;
}

.grid {
  display: grid;
  gap: 12px;
}

.grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.picker-row,
.metrics-row {
  display: flex;
  gap: 12px;
  align-items: end;
  flex-wrap: nowrap;
}

.field {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.field span {
  font-size: 13px;
  color: var(--text-soft);
}

.search-field {
  flex: 1 1 0;
  min-width: 320px;
}

.combo-shell {
  position: relative;
}

.combo-trigger {
  width: 100%;
  min-height: var(--touch);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 0 14px 0 18px;
  background: white;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  text-align: left;
}

.combo-trigger-text {
  flex: 1;
  min-width: 0;
  font-size: 15px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.combo-trigger-arrow {
  flex: 0 0 auto;
  font-size: 18px;
  color: var(--text-soft);
}

.combo-shell.open .combo-trigger {
  border-color: rgba(15, 118, 110, 0.35);
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.08);
}

.combo-panel {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 0;
  z-index: 20;
  display: grid;
  gap: 8px;
  padding: 10px;
  border: 1px solid rgba(15, 118, 110, 0.16);
  border-radius: 16px;
  background: white;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.14);
}

.combo-search-input {
  min-height: 46px;
}

.combo-options {
  max-height: 320px;
  overflow-y: auto;
  display: grid;
  gap: 6px;
}

.combo-option {
  width: 100%;
  min-height: 46px;
  border: 1px solid transparent;
  border-radius: 14px;
  padding: 0 14px;
  background: #f8fafc;
  text-align: left;
  font-size: 15px;
  color: var(--text);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.combo-option:hover,
.combo-option.active {
  background: #ecfeff;
  border-color: rgba(15, 118, 110, 0.18);
}

.combo-empty {
  margin: 0;
  padding: 12px 8px;
  color: var(--text-soft);
  font-size: 14px;
}

.picker-row > .field:nth-child(1) {
  flex: 0 0 190px;
}

.picker-row > .field:nth-child(2) {
  flex: 0 0 220px;
}

.metric {
  min-width: 0;
}

.metric--count {
  flex: 0 0 84px;
}

.metric--load {
  flex: 0 0 128px;
}

.metric--mode {
  flex: 0 0 168px;
}

.metric--goal {
  flex: 1 1 0;
  min-width: 180px;
}

.progress-panel {
  display: grid;
  gap: 12px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.66);
}

.note-input {
  min-height: 48px;
  resize: vertical;
}

.slim-btn {
  min-height: 40px;
  padding: 0 14px;
}

.danger {
  color: #b91c1c;
}

@media (max-width: 980px) {
  .picker-row,
  .metrics-row {
    flex-wrap: wrap;
  }

  .picker-row > .field,
  .metrics-row > .field {
    flex: 1 1 100%;
    min-width: 0;
  }

  .grid.two {
    grid-template-columns: 1fr;
  }
}
</style>
