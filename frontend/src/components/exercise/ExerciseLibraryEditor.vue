<script setup lang="ts">
import { computed, reactive, watch } from 'vue'

import type { ExerciseCategoryNode, ExerciseLibraryItem } from '@/types/exerciseLibrary'
import { confirmDangerousAction } from '@/utils/dangerousAction'
import {
  EXERCISE_DETAIL_FACETS,
  EXERCISE_TAG_FACETS,
  buildCategoryPathLabel,
  flattenCategoryTree,
} from '@/utils/exerciseLibrary'

const props = defineProps<{
  modelValue?: ExerciseLibraryItem | null
  categoryTree: ExerciseCategoryNode[]
  facetOptions: Record<string, string[]>
  readOnly?: boolean
}>()

const emit = defineEmits<{
  submit: [payload: Record<string, unknown>]
  remove: [exerciseId: number]
}>()

const activeTab = reactive({ value: 'detail' })

const form = reactive<Record<string, any>>({
  name: '',
  name_en: '',
  alias: '',
  code: '',
  source_type: 'custom_manual',
  base_category_id: null as number | null,
  description: '',
  video_url: '',
  coaching_points: '',
  common_errors: '',
  notes: '',
  default_increment: 2.5,
  is_main_lift_candidate: false,
  structured_tags: {},
})

const baseCategoryOptions = computed(() => {
  const flattened = flattenCategoryTree(props.categoryTree)
  const byId = new Map<number, ExerciseCategoryNode>(flattened.map((item) => [item.id, item]))
  return flattened
    .filter((item) => item.level === 3)
    .map((item) => {
      const level2 = item.parent_id ? byId.get(item.parent_id) || null : null
      const level1 = level2?.parent_id ? byId.get(level2.parent_id) || null : null
      return {
        ...item,
        path_label: buildCategoryPathLabel([level1, level2, item].filter(Boolean) as ExerciseCategoryNode[]),
      }
    })
})

const categoryLineage = computed(() => {
  const byId = new Map<number, ExerciseCategoryNode>()
  flattenCategoryTree(props.categoryTree).forEach((item) => byId.set(item.id, item))
  if (!form.base_category_id) return { level1: null, level2: null, path: null }
  const level3 = byId.get(form.base_category_id) || null
  const level2 = level3?.parent_id ? byId.get(level3.parent_id) || null : null
  const level1 = level2?.parent_id ? byId.get(level2.parent_id) || null : null
  return {
    level1: level1?.name_zh || null,
    level2: level2?.name_zh || null,
    path: [level1?.name_zh, level2?.name_zh, level3?.name_zh].filter(Boolean).join(' / ') || null,
  }
})

watch(
  () => props.modelValue,
  (value) => {
    const tags = Object.fromEntries(EXERCISE_TAG_FACETS.map(({ key }) => [key, [...(value?.structured_tags?.[key] || [])]]))
    Object.assign(form, {
      name: value?.name || '',
      name_en: value?.name_en || value?.alias || '',
      alias: value?.name_en || value?.alias || '',
      code: value?.code || '',
      source_type: value?.source_type || 'custom_manual',
      base_category_id: value?.base_category_id ?? value?.base_category?.id ?? null,
      description: value?.description || '',
      video_url: value?.video_url || '',
      coaching_points: value?.coaching_points || '',
      common_errors: value?.common_errors || '',
      notes: value?.notes || '',
      default_increment: value?.default_increment ?? 2.5,
      is_main_lift_candidate: value?.is_main_lift_candidate ?? false,
      structured_tags: tags,
    })
    activeTab.value = value || props.readOnly ? 'detail' : 'edit'
  },
  { immediate: true },
)

const selectedCategory = computed(
  () => baseCategoryOptions.value.find((item) => item.id === form.base_category_id) || null,
)

const detailEntries = computed(() =>
  EXERCISE_DETAIL_FACETS.map(({ key, label }) => ({
    key,
    label,
    values: props.modelValue?.structured_tags?.[key] || [],
  })).filter((entry) => entry.values.length),
)

function toggleTagValue(key: string, value: string) {
  const current = new Set(form.structured_tags[key] || [])
  if (current.has(value)) current.delete(value)
  else current.add(value)
  form.structured_tags[key] = Array.from(current)
}

function handleSubmit() {
  if (props.readOnly) return
  emit('submit', {
    name: form.name,
    name_en: form.name_en || null,
    alias: form.name_en || null,
    code: form.code || null,
    source_type: form.source_type,
    base_category_id: form.base_category_id,
    level1_category: categoryLineage.value.level1 || props.modelValue?.level1_category || null,
    level2_category: categoryLineage.value.level2 || props.modelValue?.level2_category || null,
    base_movement: selectedCategory.value?.name_zh || props.modelValue?.base_movement || null,
    category_path: categoryLineage.value.path || props.modelValue?.category_path || null,
    description: form.description || null,
    video_url: form.video_url || null,
    coaching_points: form.coaching_points || null,
    common_errors: form.common_errors || null,
    notes: form.notes || null,
    default_increment: form.default_increment ?? null,
    is_main_lift_candidate: form.is_main_lift_candidate,
    structured_tags: form.structured_tags,
  })
}

function handleDelete() {
  if (props.readOnly) return
  if (!props.modelValue?.id) return
  const confirmed = confirmDangerousAction({
    title: '删除动作',
    impactLines: [
      `动作名称：${props.modelValue.name}`,
      `来源：${props.modelValue.source_type === 'exos_excel' ? 'Excel 导入动作' : '自定义动作'}`,
      `分类：${props.modelValue.category_path || '未分类'}`,
    ],
  })
  if (!confirmed) return
  emit('remove', props.modelValue.id)
}
</script>

<template>
  <div class="panel editor-shell" :class="{ 'editor-shell--readonly': readOnly }">
    <div class="editor-head">
      <div>
        <p class="eyebrow">动作详情</p>
        <h3>{{ modelValue?.name || '新建动作' }}</h3>
      </div>
      <div class="head-actions">
        <button v-if="modelValue?.id" class="tab-btn danger-tab" type="button" @click="handleDelete">删除</button>
        <div class="tab-switch">
          <button class="tab-btn" :class="{ active: activeTab.value === 'detail' }" @click="activeTab.value = 'detail'">详情</button>
          <button class="tab-btn" :class="{ active: activeTab.value === 'edit' }" @click="activeTab.value = 'edit'">编辑</button>
        </div>
      </div>
    </div>

    <div v-if="(activeTab.value === 'detail' || readOnly) && modelValue" class="detail-grid">
      <div class="summary-card">
        <strong>{{ modelValue.name }}</strong>
        <span>{{ modelValue.name_en || modelValue.alias || '无英文名' }}</span>
        <small>{{ modelValue.level1_category || '未分类' }} / {{ modelValue.level2_category || '未分类' }} / {{ modelValue.base_movement || '未分类' }}</small>
        <small>{{ modelValue.category_path || '无分类路径' }}</small>
      </div>
      <div class="detail-section">
        <h4>分类信息</h4>
        <div class="detail-meta-grid">
          <div><strong>一级分类</strong><span>{{ modelValue.level1_category || '无' }}</span></div>
          <div><strong>二级分类</strong><span>{{ modelValue.level2_category || '无' }}</span></div>
          <div><strong>基础动作</strong><span>{{ modelValue.base_movement || '无' }}</span></div>
          <div><strong>动作编码</strong><span>{{ modelValue.code || '无' }}</span></div>
        </div>
      </div>
      <div class="detail-section">
        <h4>结构化标签</h4>
        <div v-for="entry in detailEntries" :key="entry.key" class="detail-tags">
          <strong>{{ entry.label }}</strong>
          <span v-for="value in entry.values" :key="value" class="tag-chip">{{ value }}</span>
        </div>
      </div>
      <div class="detail-section">
        <h4>标签词条</h4>
        <p>{{ modelValue.tag_text || '无' }}</p>
      </div>
      <div class="detail-section">
        <h4>原始英文分类字段</h4>
        <pre>{{ modelValue.original_english_fields || {} }}</pre>
      </div>
    </div>

    <div v-else-if="!readOnly" class="form-grid">
      <div class="grid two">
        <label class="field">
          <span class="field-label">动作名称</span>
          <input v-model="form.name" class="text-input" />
        </label>
        <label class="field">
          <span class="field-label">动作英文原名</span>
          <input v-model="form.name_en" class="text-input" />
        </label>
      </div>
      <div class="grid two">
        <label class="field">
          <span class="field-label">动作编码</span>
          <input v-model="form.code" class="text-input" placeholder="为空时自动生成" />
        </label>
        <label class="field">
          <span class="field-label">基础动作分类</span>
          <select v-model.number="form.base_category_id" class="text-input">
            <option :value="null">未选择</option>
            <option v-for="option in baseCategoryOptions" :key="option.id" :value="option.id">
              {{ option.path_label }}
            </option>
          </select>
        </label>
      </div>
      <label class="field">
        <span class="field-label">默认步长</span>
        <input v-model.number="form.default_increment" type="number" step="0.5" class="text-input" />
      </label>
      <label class="field">
        <span class="field-label">视频链接</span>
        <input v-model="form.video_url" class="text-input" />
      </label>
      <label class="field">
        <span class="field-label">动作描述</span>
        <textarea v-model="form.description" class="text-input area" />
      </label>
      <label class="field">
        <span class="field-label">技术要点</span>
        <textarea v-model="form.coaching_points" class="text-input area" />
      </label>
      <label class="field">
        <span class="field-label">常见错误</span>
        <textarea v-model="form.common_errors" class="text-input area" />
      </label>
      <label class="field">
        <span class="field-label">备注</span>
        <textarea v-model="form.notes" class="text-input area" />
      </label>

      <div class="detail-section">
        <h4>结构化标签</h4>
        <div v-for="facet in EXERCISE_TAG_FACETS" :key="facet.key" class="facet-block">
          <strong>{{ facet.label }}</strong>
          <div class="tag-grid">
            <button
              v-for="option in facetOptions[facet.key] || []"
              :key="option"
              type="button"
              class="tag-btn"
              :class="{ active: (form.structured_tags[facet.key] || []).includes(option) }"
              @click="toggleTagValue(facet.key, option)"
            >
              {{ option }}
            </button>
          </div>
        </div>
      </div>

      <label class="toggle-line">
        <input v-model="form.is_main_lift_candidate" type="checkbox" />
        <span>可作为主项动作</span>
      </label>

      <button class="primary-btn" @click="handleSubmit">保存动作</button>
    </div>

    <div v-else class="empty-state">
      先在左侧筛选并选择一个动作，再查看详情。
    </div>
  </div>
</template>

<style scoped>
.editor-shell,
.detail-grid,
.form-grid,
.detail-section,
.facet-block {
  display: grid;
  gap: 12px;
}

.editor-shell {
  grid-template-rows: auto minmax(0, 1fr);
  align-content: start;
  height: 100%;
  min-height: 0;
  overflow: hidden;
}

.detail-grid,
.form-grid {
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
  padding-right: 8px;
}

.editor-head,
.head-actions,
.tab-switch,
.grid.two {
  display: grid;
  gap: 12px;
}

.editor-head {
  grid-template-columns: 1fr auto;
  align-items: center;
}

.head-actions {
  grid-auto-flow: column;
  align-items: center;
}

.tab-switch {
  grid-auto-flow: column;
}

.tab-btn {
  min-height: 40px;
  border-radius: 12px;
  padding: 0 14px;
  background: #e2e8f0;
}

.tab-btn.active {
  background: var(--primary);
  color: white;
}

.danger-tab {
  background: rgba(185, 28, 28, 0.12);
  color: #b91c1c;
  border: 1px solid rgba(185, 28, 28, 0.18);
}

.danger-tab:hover {
  background: rgba(185, 28, 28, 0.18);
}

.summary-card {
  display: grid;
  gap: 6px;
  padding: 14px;
  border-radius: 16px;
  background: var(--panel-soft);
}

.editor-shell--readonly .danger-tab,
.editor-shell--readonly .tab-switch .tab-btn:last-child {
  display: none;
}

.empty-state {
  display: grid;
  place-items: center;
  min-height: 240px;
  color: var(--text-soft);
}

.detail-tags,
.tag-grid,
.detail-meta-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.detail-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.detail-meta-grid > div {
  display: grid;
  gap: 4px;
}

.tag-chip,
.tag-btn {
  min-height: 36px;
  border-radius: 999px;
  padding: 0 12px;
  display: inline-flex;
  align-items: center;
  background: #e2e8f0;
}

.tag-btn.active {
  background: var(--primary);
  color: white;
}

.field {
  display: grid;
  gap: 8px;
}

.area {
  min-height: 96px;
}

.eyebrow {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
}

.toggle-line {
  display: flex;
  align-items: center;
  gap: 10px;
}

pre {
  margin: 0;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

@media (max-width: 1100px) {
  .editor-head,
  .head-actions,
  .grid.two,
  .detail-meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
