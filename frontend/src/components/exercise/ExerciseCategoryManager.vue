<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

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
  close: []
}>()

type FormMode = 'create_root' | 'create_child' | 'edit'

const formMode = ref<FormMode>('create_root')
const editingId = ref<number | null>(null)
const createParentId = ref<number | null>(null)
const expandedRootIds = ref<Set<number>>(new Set())
const submitting = ref(false)
const deletingId = ref<number | null>(null)
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
const rootCategories = computed(() => props.categoryTree.filter((category) => category.level === 1))
const editingCategory = computed(() => flatCategories.value.find((item) => item.id === editingId.value) || null)
const createParent = computed(() => rootCategories.value.find((item) => item.id === createParentId.value) || null)
const formTitle = computed(() => {
  if (formMode.value === 'edit') return '编辑动作分类'
  if (formMode.value === 'create_child') return `新增二级分类${createParent.value ? `：${createParent.value.name_zh}` : ''}`
  return '新增一级分类'
})
const submitLabel = computed(() => {
  if (submitting.value) return '保存中...'
  if (formMode.value === 'edit') return '保存修改'
  if (formMode.value === 'create_child') return '新增二级分类'
  return '新增一级分类'
})
const canSubmit = computed(() => {
  if (!form.name_zh.trim()) return false
  if (formMode.value === 'create_child') return Boolean(createParent.value)
  return true
})

function setMessage(message: string, tone: 'info' | 'error' = 'info') {
  actionMessage.value = message
  actionTone.value = tone
}

function resetForm() {
  Object.assign(form, {
    name_zh: '',
    name_en: '',
    code: '',
    sort_order: 0,
    is_system: false,
  })
}

function fillForm(category: ExerciseCategoryNode) {
  Object.assign(form, {
    name_zh: category.name_zh || '',
    name_en: category.name_en || '',
    code: category.code || '',
    sort_order: category.sort_order || 0,
    is_system: category.is_system || false,
  })
}

function startCreateRoot() {
  formMode.value = 'create_root'
  editingId.value = null
  createParentId.value = null
  resetForm()
}

function startCreateChild(parent: ExerciseCategoryNode) {
  formMode.value = 'create_child'
  editingId.value = null
  createParentId.value = parent.id
  expandedRootIds.value = new Set(expandedRootIds.value).add(parent.id)
  resetForm()
}

function startEdit(category: ExerciseCategoryNode) {
  formMode.value = 'edit'
  editingId.value = category.id
  createParentId.value = null
  if (category.parent_id) {
    expandedRootIds.value = new Set(expandedRootIds.value).add(category.parent_id)
  }
  fillForm(category)
}

function toggleRoot(rootId: number) {
  const next = new Set(expandedRootIds.value)
  if (next.has(rootId)) next.delete(rootId)
  else next.add(rootId)
  expandedRootIds.value = next
}

function getParentName(category: ExerciseCategoryNode) {
  if (!category.parent_id) return '无'
  return flatCategories.value.find((item) => item.id === category.parent_id)?.name_zh || '未知'
}

function childCountLabel(category: ExerciseCategoryNode) {
  return `二级分类：${category.children?.length || 0} 个`
}

async function submitForm() {
  if (!canSubmit.value) {
    setMessage('分类名称不能为空；新增二级分类时必须先选择一级分类。', 'error')
    return
  }

  submitting.value = true
  try {
    if (formMode.value === 'edit') {
      if (!editingCategory.value) {
        setMessage('请先选择一个要编辑的分类。', 'error')
        return
      }
      const updated = await updateExerciseCategory(editingCategory.value.id, {
        parent_id: editingCategory.value.parent_id,
        name_zh: form.name_zh.trim(),
        name_en: form.name_en.trim() || null,
        code: form.code.trim() || null,
        sort_order: Number(form.sort_order || 0),
        is_system: form.is_system,
      })
      editingId.value = updated.id
      fillForm(updated)
      setMessage('分类已保存。')
      emit('refreshed')
      return
    }

    const parentId = formMode.value === 'create_child' ? createParentId.value : null
    const created = await createExerciseCategory({
      parent_id: parentId,
      level: parentId ? 2 : 1,
      name_zh: form.name_zh.trim(),
      name_en: form.name_en.trim() || null,
      code: form.code.trim() || null,
      sort_order: Number(form.sort_order || 0),
      is_system: form.is_system,
    })
    if (created.parent_id) {
      expandedRootIds.value = new Set(expandedRootIds.value).add(created.parent_id)
    }
    formMode.value = 'edit'
    editingId.value = created.id
    createParentId.value = null
    fillForm(created)
    setMessage('分类已创建。')
    emit('refreshed')
  } catch (error: any) {
    setMessage(error?.response?.data?.detail || '保存分类失败，请稍后重试。', 'error')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(category: ExerciseCategoryNode) {
  const confirmed = confirmDangerousAction({
    title: '删除动作分类',
    impactLines: [
      `分类名称：${category.name_zh}`,
      `层级：第 ${category.level} 层`,
      '如果分类下还有子分类或动作，后端会拒绝删除。',
    ],
  })
  if (!confirmed) return

  deletingId.value = category.id
  try {
    await deleteExerciseCategory(category.id, { confirmed: true, actor_name: '管理端' })
    if (editingId.value === category.id) startCreateRoot()
    setMessage('分类已删除。')
    emit('refreshed')
  } catch (error: any) {
    setMessage(error?.response?.data?.detail || '删除分类失败，请先确认没有子分类或动作引用。', 'error')
  } finally {
    deletingId.value = null
  }
}
</script>

<template>
  <teleport to="body">
    <div class="category-manager-overlay" @click="emit('close')">
      <section class="category-manager panel" role="dialog" aria-modal="true" aria-labelledby="exercise-category-manager-title" @click.stop>
        <div class="category-manager-head">
          <div>
            <p class="eyebrow">动作库</p>
            <h3 id="exercise-category-manager-title">分类管理</h3>
            <small>按测试项目管理方式维护：左侧选分类，右侧新增或编辑；一级分类默认不展开下级。</small>
          </div>
          <div class="category-head-actions">
            <button class="primary-btn slim" type="button" @click="startCreateRoot">新增一级分类</button>
            <button class="ghost-btn slim" type="button" @click="emit('close')">关闭</button>
          </div>
        </div>

        <div class="category-manager-body">
          <div class="manager-list-block">
            <div class="manager-block-head">
              <strong>已有动作分类</strong>
              <span>{{ flatCategories.length }} 个</span>
            </div>

            <div v-if="!rootCategories.length" class="empty-state manager-empty">当前还没有动作分类，请先新增一级分类。</div>
            <div v-else class="manager-list">
              <div v-for="root in rootCategories" :key="root.id" class="category-group">
                <div class="manager-row" :class="{ active: editingId === root.id }">
                  <div class="manager-row-copy">
                    <strong>{{ root.name_zh }}</strong>
                    <span class="scope-tag" :class="root.is_system ? 'scope-tag-system' : 'scope-tag-custom'">
                      {{ root.is_system ? '系统分类' : '自建分类' }}
                    </span>
                    <span class="manager-row-meta">编码：{{ root.code }}</span>
                    <span class="manager-row-meta">{{ childCountLabel(root) }}</span>
                  </div>
                  <div class="manager-row-actions">
                    <button
                      class="ghost-btn slim"
                      type="button"
                      :disabled="!root.children?.length"
                      @click="toggleRoot(root.id)"
                    >
                      {{ expandedRootIds.has(root.id) ? '收起' : '展开' }}
                    </button>
                    <button class="ghost-btn slim" type="button" @click="startCreateChild(root)">新增下级</button>
                    <button class="ghost-btn slim" type="button" @click="startEdit(root)">编辑</button>
                    <button
                      class="ghost-btn slim danger-btn"
                      type="button"
                      :disabled="deletingId === root.id"
                      @click="handleDelete(root)"
                    >
                      {{ deletingId === root.id ? '删除中...' : '删除' }}
                    </button>
                  </div>
                </div>

                <div v-if="expandedRootIds.has(root.id)" class="child-list">
                  <div v-if="!root.children?.length" class="child-empty">当前一级分类下还没有二级分类。</div>
                  <div
                    v-for="child in root.children || []"
                    :key="child.id"
                    class="manager-row child-row"
                    :class="{ active: editingId === child.id }"
                  >
                    <div class="manager-row-copy">
                      <strong>{{ child.name_zh }}</strong>
                      <span class="scope-tag" :class="child.is_system ? 'scope-tag-system' : 'scope-tag-custom'">
                        {{ child.is_system ? '系统分类' : '自建分类' }}
                      </span>
                      <span class="manager-row-meta">父分类：{{ root.name_zh }}</span>
                      <span class="manager-row-meta">编码：{{ child.code }}</span>
                    </div>
                    <div class="manager-row-actions">
                      <button class="ghost-btn slim" type="button" @click="startEdit(child)">编辑</button>
                      <button
                        class="ghost-btn slim danger-btn"
                        type="button"
                        :disabled="deletingId === child.id"
                        @click="handleDelete(child)"
                      >
                        {{ deletingId === child.id ? '删除中...' : '删除' }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <form class="manager-form-block" @submit.prevent="submitForm">
            <div class="manager-block-head">
              <strong>{{ formTitle }}</strong>
              <button v-if="formMode !== 'create_root'" class="ghost-btn slim" type="button" @click="startCreateRoot">
                取消编辑
              </button>
            </div>

            <div v-if="formMode === 'edit' && editingCategory" class="category-context">
              <span>当前层级：{{ editingCategory.level }}级</span>
              <span>父分类：{{ getParentName(editingCategory) }}</span>
            </div>
            <div v-else-if="formMode === 'create_child'" class="category-context">
              <span>父分类：{{ createParent?.name_zh || '未选择' }}</span>
              <span>将创建为二级分类</span>
            </div>

            <label class="field">
              <span>分类名称 <strong class="required-mark">*</strong></span>
              <input v-model="form.name_zh" class="text-input" placeholder="例如：水平推" />
            </label>
            <label class="field">
              <span>英文名</span>
              <input v-model="form.name_en" class="text-input" placeholder="可选" />
            </label>
            <label class="field">
              <span>编码</span>
              <input v-model="form.code" class="text-input" placeholder="为空自动生成" />
            </label>
            <label class="field">
              <span>排序</span>
              <input v-model.number="form.sort_order" class="text-input" type="number" />
            </label>
            <label class="checkbox-field">
              <input v-model="form.is_system" type="checkbox" />
              <span>系统分类</span>
            </label>

            <p class="manager-help">
              动作库分类删除属于危险操作；如果分类下仍有子分类或动作引用，后端会拒绝删除。
            </p>

            <div class="manager-form-actions">
              <button class="primary-btn" type="submit" :disabled="submitting || !canSubmit">
                {{ submitLabel }}
              </button>
            </div>

            <p v-if="actionMessage" class="category-message" :class="`category-message--${actionTone}`">{{ actionMessage }}</p>
          </form>
        </div>
      </section>
    </div>
  </teleport>
</template>

<style scoped>
.category-manager-overlay {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.36);
  backdrop-filter: blur(4px);
}

.category-manager {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 14px;
  width: min(1080px, 100%);
  max-height: calc(100vh - 48px);
  padding: 14px;
  border: 1px solid rgba(15, 118, 110, 0.16);
  overflow: hidden;
}

.category-manager-head,
.category-head-actions,
.manager-block-head,
.manager-row,
.manager-row-actions,
.manager-form-actions,
.category-context {
  display: flex;
  gap: 10px;
}

.category-manager-head,
.manager-block-head,
.manager-row,
.category-context {
  align-items: center;
  justify-content: space-between;
}

.category-manager-head > div,
.manager-row-copy,
.manager-form-block,
.manager-list-block,
.manager-list,
.child-list {
  display: grid;
  gap: 10px;
}

.category-manager-body {
  display: grid;
  grid-template-columns: minmax(0, 1.12fr) minmax(260px, 0.88fr);
  gap: 14px;
  min-height: 0;
  overflow: hidden;
}

.manager-list-block {
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 0;
}

.manager-list {
  overflow-y: auto;
  padding-right: 6px;
}

.category-group {
  display: grid;
  gap: 8px;
}

.manager-row {
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 12px 14px;
  background: rgba(255, 255, 255, 0.72);
}

.manager-row.active {
  border-color: rgba(15, 118, 110, 0.42);
  background: rgba(209, 250, 229, 0.7);
}

.child-list {
  margin-left: 18px;
  padding-left: 14px;
  border-left: 2px solid rgba(15, 118, 110, 0.14);
}

.child-row {
  background: rgba(255, 255, 255, 0.55);
}

.child-empty,
.manager-empty,
.manager-help,
.manager-row-meta {
  color: var(--muted);
  font-size: 13px;
}

.manager-empty,
.child-empty {
  padding: 14px;
  border: 1px dashed var(--line);
  border-radius: 14px;
  text-align: center;
}

.manager-form-block {
  align-content: start;
  overflow-y: auto;
  padding-right: 6px;
}

.manager-row-copy strong,
.manager-help {
  margin: 0;
}

.manager-row-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.scope-tag {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.scope-tag-system {
  color: #1d4ed8;
  background: rgba(37, 99, 235, 0.12);
}

.scope-tag-custom {
  color: #0f766e;
  background: rgba(20, 184, 166, 0.12);
}

.field {
  display: grid;
  gap: 8px;
}

.eyebrow {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
}

.checkbox-field {
  display: flex;
  gap: 8px;
  align-items: center;
}

.danger-btn {
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
  .category-manager-body {
    grid-template-columns: 1fr;
  }

  .category-manager-head,
  .manager-row,
  .manager-row-actions {
    align-items: stretch;
    flex-direction: column;
  }
}
</style>
