<script setup lang="ts">
import { computed, reactive, watch } from 'vue'

const props = defineProps<{
  item: any
  exercises: any[]
}>()

const emit = defineEmits<{
  save: [itemId: number, payload: Record<string, unknown>]
  remove: [itemId: number]
  move: [itemId: number, direction: 'up' | 'down']
}>()

const draft = reactive(buildDraft(props.item))
const goalOptions = ['速度', '力量', '耐力', '自定义']

watch(
  () => props.item,
  (item) => {
    Object.assign(draft, buildDraft(item))
  },
  { deep: true },
)

const selectedExercise = computed(() => props.exercises.find((exercise) => exercise.id === draft.exercise_id))
const loadModeLabel = computed(() => (draft.initial_load_mode === 'percent_1rm' ? '按最近测试百分比' : '固定重量'))

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
    rest_seconds: item.rest_seconds ?? 90,
    progression_goal: item.progression_goal || '力量',
    progression_rules: {
      target_rir: rules.target_rir ?? 2,
      up_step: rules.up_step ?? 2.5,
      down_step: rules.down_step ?? 2.5,
      miss_strategy: rules.miss_strategy || '降重后完成',
      fatigue_strategy: rules.fatigue_strategy || '连续吃力时停止加重',
    },
    ai_adjust_enabled: item.ai_adjust_enabled || false,
  }
}

function saveItem() {
  emit('save', props.item.id, {
    exercise_id: draft.exercise_id,
    sort_order: draft.sort_order,
    prescribed_sets: draft.prescribed_sets,
    prescribed_reps: draft.prescribed_reps,
    target_note: draft.target_note,
    is_main_lift: draft.is_main_lift,
    enable_auto_load: draft.enable_auto_load,
    initial_load_mode: draft.initial_load_mode,
    initial_load_value: draft.initial_load_value,
    rest_seconds: draft.rest_seconds,
    progression_goal: draft.progression_goal,
    progression_rules: { ...draft.progression_rules },
    ai_adjust_enabled: draft.ai_adjust_enabled,
  })
}
</script>

<template>
  <article class="item-card">
    <header class="item-header">
      <div class="item-copy adaptive-card">
        <p class="item-index">动作 {{ draft.sort_order }}</p>
        <h4 class="adaptive-card-title">{{ selectedExercise?.name || item.exercise?.name || '未选择动作' }}</h4>
        <span class="muted adaptive-card-subtitle adaptive-card-clamp-2">{{ loadModeLabel }}</span>
      </div>
      <div class="header-actions">
        <button class="slim-btn" type="button" @click="emit('move', item.id, 'up')">上移</button>
        <button class="slim-btn" type="button" @click="emit('move', item.id, 'down')">下移</button>
        <button class="ghost-btn slim-btn danger" type="button" @click="emit('remove', item.id)">删除</button>
      </div>
    </header>

    <div class="grid four">
      <label class="field">
        <span>动作</span>
        <select v-model.number="draft.exercise_id" class="text-input">
          <option v-for="exercise in exercises" :key="exercise.id" :value="exercise.id">{{ exercise.name }}</option>
        </select>
      </label>
      <label class="field">
        <span>顺序</span>
        <input v-model.number="draft.sort_order" type="number" class="text-input" />
      </label>
      <label class="field">
        <span>组数</span>
        <input v-model.number="draft.prescribed_sets" type="number" class="text-input" />
      </label>
      <label class="field">
        <span>次数</span>
        <input v-model.number="draft.prescribed_reps" type="number" class="text-input" />
      </label>
    </div>

    <div class="grid four">
      <label class="field">
        <span>负荷方式</span>
        <select v-model="draft.initial_load_mode" class="text-input">
          <option value="fixed_weight">固定重量</option>
          <option value="percent_1rm">按最近测试的 1RM 百分比</option>
        </select>
      </label>
      <label class="field">
        <span>{{ draft.initial_load_mode === 'percent_1rm' ? '百分比' : '重量（公斤）' }}</span>
        <input v-model.number="draft.initial_load_value" type="number" step="0.5" class="text-input" />
      </label>
      <label class="field">
        <span>休息时间（秒）</span>
        <input v-model.number="draft.rest_seconds" type="number" class="text-input" />
      </label>
      <label class="field">
        <span>训练目标</span>
        <select v-model="draft.progression_goal" class="text-input">
          <option v-for="option in goalOptions" :key="option" :value="option">{{ option }}</option>
        </select>
      </label>
    </div>

    <label class="field">
      <span>动作备注</span>
      <textarea v-model="draft.target_note" class="text-input area" placeholder="例如：保持速度、注意动作深度、优先技术稳定" />
    </label>

    <div class="toggle-row">
      <label><input v-model="draft.is_main_lift" type="checkbox" /> 主项动作</label>
      <label><input v-model="draft.enable_auto_load" type="checkbox" /> 启用自动调重</label>
      <label><input v-model="draft.ai_adjust_enabled" type="checkbox" /> 预留 AI 调整</label>
    </div>

    <section class="progress-panel">
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

    <div class="footer-actions">
      <button class="primary-btn slim" type="button" @click="saveItem">保存动作设置</button>
    </div>
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
.progress-head,
.footer-actions {
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

.grid.four {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.field {
  display: grid;
  gap: 6px;
}

.field span {
  font-size: 13px;
  color: var(--text-soft);
}

.progress-panel {
  display: grid;
  gap: 12px;
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.66);
}

.slim-btn {
  min-height: 40px;
  padding: 0 14px;
}

.danger {
  color: #b91c1c;
}

@media (max-width: 1200px) {
  .grid.four,
  .grid.two {
    grid-template-columns: 1fr;
  }
}
</style>
