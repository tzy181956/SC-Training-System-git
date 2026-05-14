<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import {
  createExerciseCategory,
  deleteExerciseCategory,
  updateExerciseCategory,
} from '@/api/exercises'
import type { ExerciseCategoryNode } from '@/types/exerciseLibrary'
import { confirmDangerousAction } from '@/utils/dangerousAction'
import { flattenCategoryTree } from '@/utils/exerciseLibrary'

const props = defineProps<{
  categoryTree: ExerciseCategoryNode[]
}>()

const emit = defineEmits<{
  refreshed: []
}>()

const selectedId = ref<number | null>(null)
const actionMessage = ref('')
const actionTone = ref<'info' | 'error'>('info')

const form = reactive({
  name_zh: '',
  name_en: '',
  code: '',
  sort_order: 0,
  is_system: false,
})

const flatCategories = computed(() => flattenCategoryTree(props.categoryTree))
const selectedCategory = computed(() => flatCategories.value.find((item) => item.id === selectedId.value) || null)
const selectedParent = computed(() => (
  selectedCategory.value?.parent_id
    ? flatCategories.value.find((item) => item.id === selectedCategory.value?.parent_id) || null
    : null
))
const canCreateChild = computed(() => Boolean(selectedCategory.value && selectedCategory.value.level < 2))

watch(
  selectedCategory,
  (category) => {
    Object.assign(form, {
      name_zh: category?.name_zh || '',
      name_en: category?.name_en || '',
      code: category?.code || '',
      sort_order: category?.sort_order || 0,
      is_system: category?.is_system || false,
    })
  },
  { immediate: true },
)

function setMessage(message: string, tone: 'info' | 'error' = 'info') {
  actionMessage.value = message
  actionTone.value = tone
}

function resetFormForChild() {
  if (!canCreateChild.value || !selectedCategory.value) return
  selectedId.value = null
  Object.assign(form, {
    name_zh: '',
    name_en: '',
    code: '',
    sort_order: 0,
    is_system: false,
  })
}

async function handleCreateRoot() {
  await submitCreate({ parent_id: null, level: 1 })
}

async function handleCreateChild() {
  if (!selectedCategory.value || selectedCategory.value.level >= 3) return
  await submitCreate({
    parent_id: selectedCategory.value.id,
    level: selectedCategory.value.level + 1,
  })
}

async function submitCreate(scope: { parent_id: number | null; level: number }) {
  if (!form.name_zh.trim()) {
    setMessage('分类名称不能为空。', 'error')
    return
  }
  try {
    const created = await createExerciseCategory({
      ...scope,
      name_zh: form.name_zh.trim(),
      name_en: form.name_en.trim() || null,
      code: form.code.trim() || null,
      sort_order: Number(form.sort_order || 0),
      is_system: form.is_system,
    })
    selectedId.value = created.id
    setMessage('分类已创建。')
    emit('refreshed')
  } catch (error: any) {
    setMessage(error?.response?.data?.detail || '创建分类失败，请稍后重试。', 'error')
  }
}

async function handleSave() {
  if (!selectedCategory.value) {
    setMessage('请先选择一个要编辑的分类。', 'error')
    return
  }
  if (!form.name_zh.trim()) {
    setMessage('分类名称不能为空。', 'error')
    return
  }
  try {
    const updated = await updateExerciseCategory(selectedCategory.value.id, {
      parent_id: selectedCategory.value.parent_id,
      name_zh: form.name_zh.trim(),
      name_en: form.name_en.trim() || null,
      code: form.code.trim() || null,
      sort_order: Number(form.sort_order || 0),
      is_system: form.is_system,
    })
    selectedId.value = updated.id
    setMessage('分类已保存。')
    emit('refreshed')
  } catch (error: any) {
    setMessage(error?.response?.data?.detail || '保存分类失败，请稍后重试。', 'error')
  }
}

async function handleDelete() {
  if (!selectedCategory.value) return
  const confirmed = confirmDangerousAction({
    title: '删除动作分类',
    impactLines: [
      `分类名称：${selectedCategory.value.name_zh}`,
      `层级：第 ${selectedCategory.value.level} 层`,
      '如果分类下还有子分类或动作，后端会拒绝删除。',
    ],
  })
  if (!confirmed) return
  try {
    await deleteExerciseCategory(selectedCategory.value.id, { confirmed: true, actor_name: '管理端' })
    selectedId.value = null
    setMessage('分类已删除。')
    emit('refreshed')
  } catch (error: any) {
    setMessage(error?.response?.data?.detail || '删除分类失败，请先确认没有子分类或动作引用。', 'error')
  }
}

</script>

<template>
  <section class="category-manager">
    <div class="category-manager-head">
      <div>
        <strong>分类管理</strong>
        <small>管理员维护全局分类；教练找不到合适项时可选“待定”。</small>
      </div>
    </div>

    <label class="field">
      <span class="field-label">选择分类</span>
      <select v-model.number="selectedId" class="text-input">
        <option :value="null">未选择</option>
        <option v-for="category in flatCategories" :key="category.id" :value="category.id">
          {{ '　'.repeat(Math.max(category.level - 1, 0)) }}{{ category.name_zh }}（{{ category.level }}级）
        </option>
      </select>
    </label>

    <div v-if="selectedCategory" class="category-context">
      <span>当前层级：{{ selectedCategory.level }}级</span>
      <span>父分类：{{ selectedParent?.name_zh || '无' }}</span>
    </div>

    <div class="grid two">
      <label class="field">
        <span class="field-label">分类名称</span>
        <input v-model="form.name_zh" class="text-input" placeholder="例如：水平推" />
      </label>
      <label class="field">
        <span class="field-label">英文名</span>
        <input v-model="form.name_en" class="text-input" placeholder="可选" />
      </label>
    </div>

    <div class="grid two">
      <label class="field">
        <span class="field-label">编码</span>
        <input v-model="form.code" class="text-input" placeholder="为空自动生成" />
      </label>
      <label class="field">
        <span class="field-label">排序</span>
        <input v-model.number="form.sort_order" class="text-input" type="number" />
      </label>
    </div>

    <label class="toggle-line">
      <input v-model="form.is_system" type="checkbox" />
      <span>系统分类</span>
    </label>

    <div class="category-actions">
      <button class="primary-btn slim" type="button" @click="handleCreateRoot">新建一级分类</button>
      <button class="secondary-btn slim" type="button" :disabled="!canCreateChild" @click="handleCreateChild">
        新建下级分类
      </button>
      <button class="secondary-btn slim" type="button" :disabled="!selectedCategory" @click="handleSave">保存当前分类</button>
      <button class="ghost-btn slim danger" type="button" :disabled="!selectedCategory" @click="handleDelete">删除分类</button>
    </div>

    <button v-if="canCreateChild" class="ghost-btn slim" type="button" @click="resetFormForChild">
      清空表单用于新建下级
    </button>

    <p v-if="actionMessage" class="category-message" :class="`category-message--${actionTone}`">{{ actionMessage }}</p>
  </section>
</template>

<style scoped>
.category-manager {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid rgba(15, 118, 110, 0.16);
  border-radius: 18px;
  background: rgba(240, 253, 250, 0.72);
}

.category-manager-head,
.category-actions,
.category-context {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;
  justify-content: space-between;
}

.category-manager-head > div {
  display: grid;
  gap: 4px;
}

.grid.two {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.field {
  display: grid;
  gap: 8px;
}

.toggle-line {
  display: flex;
  gap: 8px;
  align-items: center;
}

.danger {
  color: #b91c1c;
}

.category-message {
  margin: 0;
  padding: 10px 12px;
  border-radius: 12px;
}

.category-message--info {
  color: #0f766e;
  background: rgba(20, 184, 166, 0.12);
}

.category-message--error {
  color: #b91c1c;
  background: rgba(254, 226, 226, 0.8);
}

@media (max-width: 900px) {
  .grid.two {
    grid-template-columns: 1fr;
  }
}
</style>
