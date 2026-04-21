<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'

import TemplateItemCard from './TemplateItemCard.vue'

const props = defineProps<{
  exercises: any[]
  template: any | null
  saveNoticeKey?: number
}>()

const emit = defineEmits<{
  saveTemplate: [payload: Record<string, unknown>]
  deleteTemplate: [templateId: number]
}>()

const templateForm = reactive({
  name: '',
  description: '',
  is_active: true,
})

const pendingScrollToNewItem = ref(false)
const lastItemElement = ref<HTMLElement | null>(null)
const draftItems = ref<any[]>([])
const removedItemIds = ref<number[]>([])
const nextTempId = ref(-1)
const saveNotice = ref('')
let saveNoticeTimer: number | null = null

watch(
  () => props.template,
  (template) => {
    templateForm.name = template?.name || ''
    templateForm.description = template?.description || ''
    templateForm.is_active = template?.is_active ?? true
    draftItems.value = [...(template?.items || [])]
      .sort((left, right) => left.sort_order - right.sort_order)
      .map((item) => ({
        ...item,
        progression_rules: { ...(item.progression_rules || {}) },
      }))
    removedItemIds.value = []
    nextTempId.value = -1
  },
  { immediate: true },
)

watch(
  () => props.saveNoticeKey,
  (current, previous) => {
    if (!current || current === previous) return
    saveNotice.value = '模板已保存'
    if (saveNoticeTimer) {
      window.clearTimeout(saveNoticeTimer)
    }
    saveNoticeTimer = window.setTimeout(() => {
      saveNotice.value = ''
      saveNoticeTimer = null
    }, 2200)
  },
)

const sortedItems = computed(() => [...draftItems.value].sort((left, right) => left.sort_order - right.sort_order))

function buildNewItemDraft() {
  return {
    id: nextTempId.value--,
    exercise_id: 0,
    sort_order: sortedItems.value.length + 1,
    prescribed_sets: 4,
    prescribed_reps: 5,
    target_note: '',
    is_main_lift: false,
    enable_auto_load: false,
    initial_load_mode: 'fixed_weight',
    initial_load_value: 60,
    progression_goal: '',
    progression_rules: {
      target_rir: 2,
      up_step: 2.5,
      down_step: 2.5,
      miss_strategy: '降低重量后完成目标次数',
      fatigue_strategy: '连续吃力则停止加重',
    },
    ai_adjust_enabled: false,
  }
}

function saveTemplate() {
  emit('saveTemplate', {
    template: {
      name: templateForm.name,
      description: templateForm.description,
      is_active: templateForm.is_active,
    },
    items: sortedItems.value.map((item, index) => ({
      id: item.id,
      exercise_id: item.exercise_id,
      sort_order: index + 1,
      prescribed_sets: item.prescribed_sets,
      prescribed_reps: item.prescribed_reps,
      target_note: item.target_note,
      is_main_lift: item.is_main_lift,
      enable_auto_load: item.enable_auto_load,
      initial_load_mode: item.initial_load_mode,
      initial_load_value: item.initial_load_value,
      progression_goal: item.progression_goal,
      progression_rules: { ...(item.progression_rules || {}) },
      ai_adjust_enabled: item.ai_adjust_enabled,
    })),
    removedItemIds: [...removedItemIds.value],
  })
}

function addItem() {
  pendingScrollToNewItem.value = true
  draftItems.value = [...sortedItems.value, buildNewItemDraft()]
}

function updateItemDraft(itemId: number, payload: Record<string, unknown>) {
  draftItems.value = draftItems.value.map((item) =>
    item.id === itemId
      ? {
          ...item,
          ...payload,
          progression_rules: payload.progression_rules ? { ...payload.progression_rules } : { ...(item.progression_rules || {}) },
        }
      : item,
  )
}

function removeItemDraft(itemId: number) {
  const target = draftItems.value.find((item) => item.id === itemId)
  if (!target) return
  if (target.id > 0) {
    removedItemIds.value = [...removedItemIds.value, target.id]
  }
  draftItems.value = draftItems.value
    .filter((item) => item.id !== itemId)
    .map((item, index) => ({ ...item, sort_order: index + 1 }))
}

function moveItemDraft(itemId: number, direction: 'up' | 'down') {
  const items = [...sortedItems.value]
  const index = items.findIndex((item) => item.id === itemId)
  const targetIndex = direction === 'up' ? index - 1 : index + 1
  if (index < 0 || targetIndex < 0 || targetIndex >= items.length) return
  ;[items[index], items[targetIndex]] = [items[targetIndex], items[index]]
  draftItems.value = items.map((item, currentIndex) => ({ ...item, sort_order: currentIndex + 1 }))
}

function removeTemplate() {
  if (!props.template?.id) return
  const confirmed = window.confirm('确认删除这个训练模板吗？删除后模板及其动作将不可恢复。')
  if (!confirmed) return
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
        <button v-if="template?.id" class="ghost-btn slim danger-btn" type="button" @click="removeTemplate">删除模板</button>
        <button class="primary-btn slim" type="button" @click="saveTemplate">保存模板</button>
      </div>

      <p v-if="saveNotice" class="save-notice">{{ saveNotice }}</p>

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
          <p class="eyebrow">添加动作</p>
          <h3>继续往模板里追加新的训练动作</h3>
        </div>
        <button class="primary-btn slim" type="button" @click="addItem">添加动作</button>
      </div>
      <p class="hint">点击“添加动作”后会生成一个新的空白动作卡片，再在卡片里选择动作并填写细节。</p>
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
          @change="updateItemDraft"
          @remove="removeItemDraft"
          @move="moveItemDraft"
        />
      </div>
      <div v-if="!sortedItems.length" class="panel empty-panel">
        <h4>当前模板还没有动作</h4>
        <p>先填写模板基础信息，再在上方选择动作，统一调整后点击保存模板。</p>
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
.hint,
.save-notice {
  color: var(--muted);
  font-size: 13px;
}

.eyebrow,
.hint,
.save-notice {
  margin: 0;
}

.save-notice {
  padding: 10px 12px;
  border-radius: 14px;
  background: #dcfce7;
  color: #166534;
  font-weight: 600;
}

.danger-btn {
  color: #b91c1c;
}

@media (max-width: 1200px) {
  .grid.two,
  .grid.four {
    grid-template-columns: 1fr;
  }
}
</style>
