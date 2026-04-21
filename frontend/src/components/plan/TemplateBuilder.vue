<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'

import TemplateItemCard from './TemplateItemCard.vue'
import { buildExerciseOptionLabel } from '@/utils/exerciseLibrary'

const props = defineProps<{
  exercises: any[]
  template: any | null
}>()

const emit = defineEmits<{
  saveTemplate: [payload: Record<string, unknown>]
  deleteTemplate: [templateId: number]
  addItem: [payload: Record<string, unknown>]
  updateItem: [itemId: number, payload: Record<string, unknown>]
  deleteItem: [itemId: number]
  moveItem: [itemId: number, direction: 'up' | 'down']
}>()

const templateForm = reactive({
  name: '',
  description: '',
  is_active: true,
})

const newItem = reactive({
  exercise_id: 0,
  prescribed_sets: 4,
  prescribed_reps: 5,
  target_note: '',
  is_main_lift: true,
  enable_auto_load: true,
  initial_load_mode: 'fixed_weight',
  initial_load_value: 60,
  rest_seconds: 120,
  progression_goal: '力量',
  progression_rules: {
    target_rir: 2,
    up_step: 2.5,
    down_step: 2.5,
    miss_strategy: '降低重量后完成目标次数',
    fatigue_strategy: '连续吃力则停止加重',
  },
  ai_adjust_enabled: false,
})

const pendingScrollToNewItem = ref(false)
const lastItemElement = ref<HTMLElement | null>(null)

watch(
  () => props.template,
  (template) => {
    templateForm.name = template?.name || ''
    templateForm.description = template?.description || ''
    templateForm.is_active = template?.is_active ?? true
  },
  { immediate: true },
)

const sortedItems = computed(() =>
  [...(props.template?.items || [])].sort((left, right) => left.sort_order - right.sort_order),
)

const canAddItem = computed(() => Boolean(props.template?.id) && newItem.exercise_id > 0)
const addItemHint = computed(() => {
  if (!props.template?.id) return '请先保存模板，再继续添加训练动作。'
  if (!newItem.exercise_id) return '请先选择一个训练动作，再添加到模板中。'
  return `当前模板已有 ${sortedItems.value.length} 个动作，可继续扩展到 8-15 个或更多。`
})

function saveTemplate() {
  emit('saveTemplate', {
    name: templateForm.name,
    description: templateForm.description,
    is_active: templateForm.is_active,
  })
}

function addItem() {
  if (!canAddItem.value) return
  const lastItem = sortedItems.value.length ? sortedItems.value[sortedItems.value.length - 1] : null
  pendingScrollToNewItem.value = true
  emit('addItem', {
    ...newItem,
    sort_order: (lastItem?.sort_order || 0) + 1,
    progression_rules: { ...newItem.progression_rules },
  })
}

function removeTemplate() {
  if (!props.template?.id) return
  emit('deleteTemplate', props.template.id)
}

watch(
  () => sortedItems.value.length,
  async (current, previous) => {
    if (!pendingScrollToNewItem.value || current <= previous) return
    await nextTick()
    lastItemElement.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    pendingScrollToNewItem.value = false
  },
)
</script>

<template>
  <section class="builder-wrap">
    <div class="panel builder-header">
      <div class="header-copy">
        <p class="eyebrow">模板基础信息</p>
        <h3>{{ template?.id ? '编辑训练模板' : '新建训练模板' }}</h3>
      </div>
      <div class="header-actions">
        <button v-if="template?.id" class="ghost-btn slim danger" type="button" @click="removeTemplate">删除模板</button>
        <button class="primary-btn slim" type="button" @click="saveTemplate">保存模板</button>
      </div>

      <div class="grid two">
        <label class="field">
          <span class="field-label">模板名称 <strong class="required-mark">*</strong></span>
          <input v-model="templateForm.name" class="text-input" placeholder="例如：力量训练 A、下肢爆发 B" />
        </label>
        <label class="field">
          <span class="field-label">状态</span>
          <select v-model="templateForm.is_active" class="text-input">
            <option :value="true">启用</option>
            <option :value="false">停用</option>
          </select>
        </label>
      </div>

      <label class="field">
        <span class="field-label">模板说明</span>
        <textarea
          v-model="templateForm.description"
          class="text-input area"
          placeholder="例如：适用于下肢主项日，目标是基础力量与动作质量。"
        />
      </label>
    </div>

    <div class="panel quick-add-panel">
      <div class="quick-header">
        <div>
          <p class="eyebrow">快速添加动作</p>
          <h3>继续往模板里追加新的训练动作</h3>
        </div>
        <button class="primary-btn slim" type="button" :disabled="!canAddItem" @click="addItem">新增动作卡片</button>
      </div>
      <p class="hint">{{ addItemHint }}</p>

      <div class="grid four">
        <label class="field">
          <span class="field-label">动作 <strong class="required-mark">*</strong></span>
          <select v-model.number="newItem.exercise_id" class="text-input">
            <option :value="0">请选择动作</option>
            <option v-for="exercise in exercises" :key="exercise.id" :value="exercise.id">
              {{ buildExerciseOptionLabel(exercise) }}
            </option>
          </select>
        </label>
        <label class="field">
          <span class="field-label">组数</span>
          <input v-model.number="newItem.prescribed_sets" type="number" class="text-input" />
        </label>
        <label class="field">
          <span class="field-label">次数</span>
          <input v-model.number="newItem.prescribed_reps" type="number" class="text-input" />
        </label>
        <label class="field">
          <span class="field-label">负荷方式</span>
          <select v-model="newItem.initial_load_mode" class="text-input">
            <option value="fixed_weight">固定重量</option>
            <option value="percent_1rm">按最近测试的 1RM 百分比</option>
          </select>
        </label>
      </div>
    </div>

    <div class="item-list">
      <div
        v-for="(item, index) in sortedItems"
        :key="item.id"
        :ref="(element) => { if (index === sortedItems.length - 1) lastItemElement = element as HTMLElement | null }"
      >
        <TemplateItemCard
          :item="item"
          :exercises="exercises"
          @save="(itemId, payload) => emit('updateItem', itemId, payload)"
          @remove="(itemId) => emit('deleteItem', itemId)"
          @move="(itemId, direction) => emit('moveItem', itemId, direction)"
        />
      </div>
      <div v-if="!sortedItems.length" class="panel empty-panel">
        <h4>当前模板还没有动作</h4>
        <p>先填写模板基础信息并保存，然后在上方选择动作，逐个加入这份训练计划。</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.builder-wrap,
.builder-header,
.quick-add-panel,
.item-list,
.empty-panel {
  display: grid;
  gap: 16px;
}

.builder-wrap {
  height: 100%;
  min-height: 0;
  align-content: start;
}

.header-actions,
.quick-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.grid {
  display: grid;
  gap: 12px;
}

.grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.grid.four {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.eyebrow,
.hint {
  color: var(--muted);
  font-size: 13px;
}

.eyebrow,
.hint {
  margin: 0;
}

.danger {
  color: #b91c1c;
}

@media (max-width: 1200px) {
  .grid.two,
  .grid.four {
    grid-template-columns: 1fr;
  }
}
</style>
