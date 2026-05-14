<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { fetchAllExerciseListItems } from '@/api/exercises'
import {
  addPlanTemplateItem,
  addPlanTemplateModule,
  copyPlanTemplate,
  createPlanTemplate,
  deletePlanTemplate,
  deletePlanTemplateItem,
  deletePlanTemplateModule,
  fetchPlanTemplate,
  fetchPlanTemplates,
  type PlanTemplateVisibility,
  updatePlanTemplate,
  updatePlanTemplateItem,
  updatePlanTemplateModule,
} from '@/api/plans'
import { fetchTestDefinitions } from '@/api/testRecords'
import { fetchUsers, type UserManagementRead } from '@/api/users'
import AppShell from '@/components/layout/AppShell.vue'
import TemplateBuilder from '@/components/plan/TemplateBuilder.vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const templates = ref<any[]>([])
const exercises = ref<any[]>([])
const testMetricOptions = ref<any[]>([])
const coachUsers = ref<UserManagementRead[]>([])
const selectedTemplateId = ref<number | null>(null)
const selectedTemplateDetail = ref<any | null>(null)
const templateDetailLoading = ref(false)
const keyword = ref('')
const visibilityFilter = ref<'all' | PlanTemplateVisibility>('all')
const saveNoticeKey = ref(0)
const savingTemplate = ref(false)
const loadWarning = ref('')
const actionMessage = ref('')
const actionTone = ref<'success' | 'error'>('success')
const templateScopeForm = reactive({
  visibility: 'public' as PlanTemplateVisibility,
  ownerUserId: null as number | null,
})
const copyDialog = reactive({
  open: false,
  template: null as any | null,
  name: '',
  targetOwnerUserId: null as number | null,
  submitting: false,
})
let hydrateRequestId = 0
let templateDetailRequestId = 0
let editorCatalogLoadPromise: Promise<void> | null = null

const selectedTemplateSummary = computed(
  () => templates.value.find((template) => template.id === selectedTemplateId.value) || null,
)
const selectedTemplate = computed(() => {
  if (!selectedTemplateId.value) return null
  if (selectedTemplateDetail.value?.id === selectedTemplateId.value) return selectedTemplateDetail.value
  return selectedTemplateSummary.value
})
const isAdmin = computed(() => authStore.isAdmin)
const coachOptions = computed(() => coachUsers.value.filter((user) => user.role_code === 'coach' && user.is_active))
const selectedTemplateReadonly = computed(() => (
  Boolean(selectedTemplate.value?.id)
  && !isAdmin.value
  && resolveTemplateVisibility(selectedTemplate.value) === 'public'
))
const canCopySelectedTemplate = computed(() => Boolean(selectedTemplate.value?.id && resolveTemplateVisibility(selectedTemplate.value) === 'public'))
const scopedTemplates = computed(() => {
  if (visibilityFilter.value === 'public') {
    return templates.value.filter((template) => resolveTemplateVisibility(template) === 'public')
  }
  if (visibilityFilter.value === 'private') {
    return templates.value.filter((template) => {
      if (resolveTemplateVisibility(template) !== 'private') return false
      if (isAdmin.value) return true
      return template.owner_user_id === authStore.currentUser?.id
    })
  }
  return templates.value
})

const filteredTemplates = computed(() => {
  const search = keyword.value.trim()
  if (!search) return scopedTemplates.value
  return scopedTemplates.value.filter(
    (template) => template.name.includes(search) || (template.description || '').includes(search),
  )
})

watch(
  selectedTemplate,
  (template) => {
    if (!template) {
      templateScopeForm.visibility = isAdmin.value ? 'public' : 'private'
      templateScopeForm.ownerUserId = null
      return
    }
    templateScopeForm.visibility = resolveTemplateVisibility(template)
    templateScopeForm.ownerUserId = template.owner_user_id ?? null
  },
  { immediate: true },
)

watch(visibilityFilter, () => {
  selectedTemplateId.value = null
  hydrate()
})

watch(selectedTemplateId, (templateId) => {
  if (!templateId) {
    templateDetailRequestId += 1
    templateDetailLoading.value = false
    selectedTemplateDetail.value = null
    void ensureEditorCatalogs()
    return
  }
  void loadTemplateDetail(templateId)
})

function normalizeTestMetricOptions(catalog: any): any[] {
  const types = Array.isArray(catalog?.types) ? catalog.types : []
  return types.flatMap((type: any) => {
    const metrics = Array.isArray(type?.metrics) ? type.metrics : Array.isArray(type?.items) ? type.items : []
    return metrics.map((metric: any) => ({
      id: metric.id,
      name: metric.name,
      test_type_id: type.id,
      test_type_name: type.name,
      label: `${type.name} / ${metric.name}`,
    }))
  })
}

async function hydrate(preferredTemplateId?: number | null) {
  const requestId = ++hydrateRequestId
  loadWarning.value = ''
  const templateResult = await fetchPlanTemplates({ visibility: visibilityFilter.value })
  if (requestId !== hydrateRequestId) return

  templates.value = templateResult

  if (preferredTemplateId && templates.value.some((template) => template.id === preferredTemplateId)) {
    selectedTemplateId.value = preferredTemplateId
    void loadTemplateDetail(preferredTemplateId)
    return
  }
  if (!selectedTemplateId.value && templates.value[0]) {
    selectedTemplateId.value = templates.value[0].id
    void loadTemplateDetail(templates.value[0].id)
    return
  }
  if (selectedTemplateId.value) {
    void loadTemplateDetail(selectedTemplateId.value)
  }
}

async function ensureEditorCatalogs() {
  if (exercises.value.length && testMetricOptions.value.length) return
  if (editorCatalogLoadPromise) return editorCatalogLoadPromise

  editorCatalogLoadPromise = (async () => {
    const [exerciseResult, testDefinitionResult] = await Promise.allSettled([
      fetchAllExerciseListItems(),
      fetchTestDefinitions(),
    ])

    exercises.value = exerciseResult.status === 'fulfilled' ? exerciseResult.value : []
    testMetricOptions.value =
      testDefinitionResult.status === 'fulfilled' ? normalizeTestMetricOptions(testDefinitionResult.value) : []

    const failedBlocks = [
      exerciseResult.status !== 'fulfilled' ? '动作目录' : '',
      testDefinitionResult.status !== 'fulfilled' ? '测试项目目录' : '',
    ].filter(Boolean)
    if (failedBlocks.length) {
      loadWarning.value = `模板已加载，但${failedBlocks.join('和')}暂时没有加载成功，当前只能先查看或修正已有模板。`
    }
  })()

  try {
    await editorCatalogLoadPromise
  } finally {
    editorCatalogLoadPromise = null
  }
}

async function loadTemplateDetail(templateId: number) {
  const requestId = ++templateDetailRequestId
  templateDetailLoading.value = true
  selectedTemplateDetail.value = null

  const [templateResult] = await Promise.allSettled([
    fetchPlanTemplate(templateId),
    ensureEditorCatalogs(),
  ])

  if (requestId !== templateDetailRequestId || selectedTemplateId.value !== templateId) return
  templateDetailLoading.value = false

  if (templateResult.status === 'fulfilled') {
    selectedTemplateDetail.value = templateResult.value
    return
  }
  showActionMessage('error', resolveErrorMessage(templateResult.reason))
}

async function hydrateCoaches() {
  if (!isAdmin.value) return
  coachUsers.value = await fetchUsers()
}

function createDraftTemplate() {
  actionMessage.value = ''
  selectedTemplateId.value = null
  selectedTemplateDetail.value = null
  templateScopeForm.visibility = isAdmin.value ? 'public' : 'private'
  templateScopeForm.ownerUserId = null
  void ensureEditorCatalogs()
}

async function saveTemplate(payload: Record<string, any>) {
  savingTemplate.value = true
  const templatePayload = payload.template || {}
  const modulesPayload = (payload.modules || []) as Record<string, any>[]
  const itemsPayload = (payload.items || []) as Record<string, any>[]
  const removedItemIds = (payload.removedItemIds || []) as number[]
  const removedModuleIds = (payload.removedModuleIds || []) as number[]

  async function persistTemplateGraph(templateId: number) {
    const moduleIdMap = new Map<number, number>()

    for (const module of modulesPayload) {
      const normalized: Record<string, any> = { ...module }
      delete normalized.id
      if (module.id > 0) {
        const updated = await updatePlanTemplateModule(module.id, normalized)
        moduleIdMap.set(module.id, updated.id)
      } else {
        const created = await addPlanTemplateModule(templateId, normalized)
        moduleIdMap.set(module.id, created.id)
      }
    }

    for (const itemId of removedItemIds) {
      await deletePlanTemplateItem(itemId, { confirmed: true, actor_name: '管理端' })
    }

    for (const item of itemsPayload) {
      const normalized: Record<string, any> = {
        ...item,
        module_id: moduleIdMap.get(item.module_id) ?? item.module_id,
      }
      delete normalized.id
      if (item.id > 0) {
        await updatePlanTemplateItem(item.id, normalized)
      } else {
        await addPlanTemplateItem(templateId, normalized)
      }
    }

    for (const moduleId of removedModuleIds) {
      await deletePlanTemplateModule(moduleId, { confirmed: true, actor_name: '管理端' })
    }
  }

  try {
    if (selectedTemplate.value?.id) {
      const updatePayload = isAdmin.value
        ? {
            ...templatePayload,
            visibility: templateScopeForm.visibility,
            owner_user_id: templateScopeForm.visibility === 'private' ? templateScopeForm.ownerUserId : null,
          }
        : templatePayload
      if (isAdmin.value && updatePayload.visibility === 'private' && !updatePayload.owner_user_id) {
        showActionMessage('error', '管理员保存自建模板时必须选择归属教练。')
        return
      }
      await updatePlanTemplate(selectedTemplate.value.id, updatePayload)
      await persistTemplateGraph(selectedTemplate.value.id)
      await hydrate(selectedTemplate.value.id)
      saveNoticeKey.value += 1
      return
    }

    if (isAdmin.value && templateScopeForm.visibility === 'private' && !templateScopeForm.ownerUserId) {
      showActionMessage('error', '管理员新建自建模板时必须选择归属教练。')
      return
    }
    const created = await createPlanTemplate({
      ...templatePayload,
      sport_id: null,
      team_id: null,
      visibility: isAdmin.value ? templateScopeForm.visibility : 'private',
      owner_user_id: isAdmin.value && templateScopeForm.visibility === 'private' ? templateScopeForm.ownerUserId : null,
    })
    await persistTemplateGraph(created.id)
    await hydrate(created.id)
    saveNoticeKey.value += 1
  } finally {
    savingTemplate.value = false
  }
}

async function removeTemplate(templateId: number) {
  await deletePlanTemplate(templateId, { confirmed: true, actor_name: '管理端' })
  selectedTemplateId.value = null
  await hydrate()
}

function templateBadgeLabel(template: any) {
  if (resolveTemplateVisibility(template) === 'public') return '公共模板'
  if (isAdmin.value) return template.owner_name ? `${template.owner_name} 模板` : '自建模板'
  return '我的模板'
}

function resolveTemplateVisibility(template: any): PlanTemplateVisibility {
  return template?.visibility === 'private' ? 'private' : 'public'
}

function templateSourceLabel(template: any) {
  return template.source_template_name ? `复制自：${template.source_template_name}` : ''
}

function showActionMessage(tone: 'success' | 'error', message: string) {
  actionTone.value = tone
  actionMessage.value = message
}

function resolveErrorMessage(error: unknown) {
  const detail = (error as any)?.response?.data?.detail
  if (Array.isArray(detail)) return detail.map((item) => item.msg || String(item)).join('；')
  return detail || (error as Error)?.message || '操作失败，请稍后重试。'
}

function openCopyDialog(template: any) {
  if (resolveTemplateVisibility(template) !== 'public') return
  copyDialog.open = true
  copyDialog.template = template
  copyDialog.name = isAdmin.value ? `${template.name} - 教练副本` : `${template.name} - 我的副本`
  copyDialog.targetOwnerUserId = null
  actionMessage.value = ''
}

function closeCopyDialog() {
  if (copyDialog.submitting) return
  copyDialog.open = false
  copyDialog.template = null
  copyDialog.name = ''
  copyDialog.targetOwnerUserId = null
}

async function submitCopyTemplate() {
  if (!copyDialog.template?.id || copyDialog.submitting) return
  if (isAdmin.value && !copyDialog.targetOwnerUserId) {
    showActionMessage('error', '管理员复制公共模板时必须选择目标教练。')
    return
  }

  copyDialog.submitting = true
  try {
    const copied = await copyPlanTemplate(copyDialog.template.id, {
      name: copyDialog.name || null,
      target_owner_user_id: isAdmin.value ? copyDialog.targetOwnerUserId : null,
    })
    copyDialog.open = false
    copyDialog.template = null
    copyDialog.name = ''
    copyDialog.targetOwnerUserId = null
    visibilityFilter.value = 'all'
    await hydrate(copied.id)
    showActionMessage('success', `已复制为“${copied.name}”。`)
  } catch (error) {
    showActionMessage('error', resolveErrorMessage(error))
  } finally {
    copyDialog.submitting = false
  }
}

onMounted(async () => {
  const jobs = [hydrate()]
  if (isAdmin.value) {
    jobs.push(hydrateCoaches())
  }
  await Promise.all(jobs)
})
</script>

<template>
  <AppShell>
    <div class="template-layout">
      <aside class="panel sidebar">
        <div class="sidebar-head">
          <div>
            <p class="eyebrow">模板列表</p>
            <h3>训练模板</h3>
          </div>
          <button class="primary-btn slim" type="button" @click="createDraftTemplate">新建模板</button>
        </div>

        <label class="field">
          <span class="field-label">搜索模板</span>
          <input v-model="keyword" class="text-input" placeholder="按模板名称或说明搜索" />
        </label>

        <div class="template-filter" role="group" aria-label="模板可见性筛选">
          <button type="button" :class="{ active: visibilityFilter === 'all' }" @click="visibilityFilter = 'all'">全部</button>
          <button type="button" :class="{ active: visibilityFilter === 'public' }" @click="visibilityFilter = 'public'">公共模板</button>
          <button type="button" :class="{ active: visibilityFilter === 'private' }" @click="visibilityFilter = 'private'">
            {{ isAdmin ? '自建模板' : '我的模板' }}
          </button>
        </div>

        <div class="template-scroll">
          <div class="template-list">
            <article
              v-for="template in filteredTemplates"
              :key="template.id"
              class="template-row"
              :class="{ active: template.id === selectedTemplateId }"
            >
              <button class="template-pick" type="button" @click="selectedTemplateId = template.id">
                <span class="template-row-head">
                  <strong>{{ template.name }}</strong>
                  <em>{{ templateBadgeLabel(template) }}</em>
                </span>
                <span>{{ template.description || '暂无说明' }}</span>
                <small>{{ template.modules_count ?? template.modules?.length ?? 0 }} 个模块 / {{ template.items_count ?? template.items?.length ?? 0 }} 个动作</small>
                <small v-if="templateSourceLabel(template)">{{ templateSourceLabel(template) }}</small>
              </button>
            </article>
          </div>
        </div>
      </aside>

      <div class="builder-column">
        <section class="panel template-scope-panel">
          <div>
            <p class="eyebrow">模板归属</p>
            <h3>
              {{ selectedTemplate ? templateBadgeLabel(selectedTemplate) : isAdmin ? '新建模板' : '新建我的模板' }}
            </h3>
          </div>

          <div v-if="!selectedTemplate && isAdmin" class="scope-fields">
            <label class="field">
              <span class="field-label">创建类型</span>
              <select v-model="templateScopeForm.visibility" class="text-input">
                <option value="public">公共模板</option>
                <option value="private">指定教练自建模板</option>
              </select>
            </label>
            <label v-if="templateScopeForm.visibility === 'private'" class="field">
              <span class="field-label">归属教练</span>
              <select v-model.number="templateScopeForm.ownerUserId" class="text-input">
                <option :value="null">请选择教练</option>
                <option v-for="coach in coachOptions" :key="coach.id" :value="coach.id">{{ coach.display_name }}</option>
              </select>
            </label>
          </div>

          <div v-else-if="selectedTemplate && isAdmin" class="scope-fields">
            <label class="field">
              <span class="field-label">模板类型</span>
              <select v-model="templateScopeForm.visibility" class="text-input">
                <option value="public">公共模板</option>
                <option value="private">指定教练自建模板</option>
              </select>
            </label>
            <label v-if="templateScopeForm.visibility === 'private'" class="field">
              <span class="field-label">归属教练</span>
              <select v-model.number="templateScopeForm.ownerUserId" class="text-input">
                <option :value="null">请选择教练</option>
                <option v-for="coach in coachOptions" :key="coach.id" :value="coach.id">{{ coach.display_name }}</option>
              </select>
            </label>
          </div>

          <p v-else-if="selectedTemplateReadonly" class="scope-hint">公共模板只读，复制到我的模板后可以继续修改。</p>
          <p v-else class="scope-hint">自建模板仅本人和管理员可见。</p>

          <p v-if="selectedTemplate?.source_template_name" class="scope-hint">复制自：{{ selectedTemplate.source_template_name }}</p>
          <button
            v-if="canCopySelectedTemplate"
            class="primary-btn slim"
            type="button"
            @click="openCopyDialog(selectedTemplate)"
          >
            {{ isAdmin ? '复制给教练' : '复制到我的模板' }}
          </button>
        </section>

        <p v-if="actionMessage" class="action-message" :class="`action-message--${actionTone}`">{{ actionMessage }}</p>

        <p v-if="templateDetailLoading" class="detail-loading">正在加载模板详情...</p>
        <TemplateBuilder
          v-else-if="!selectedTemplateId || selectedTemplateDetail"
          class="builder-panel"
          :template="selectedTemplateId ? selectedTemplateDetail : null"
          :exercises="exercises"
          :test-metric-options="testMetricOptions"
          :save-notice-key="saveNoticeKey"
          :saving="savingTemplate"
          :readonly="selectedTemplateReadonly"
          @save-template="saveTemplate"
          @delete-template="removeTemplate"
        />
        <p v-else class="detail-loading">模板详情加载失败，请重新选择模板或刷新页面。</p>
      </div>
    </div>
    <p v-if="loadWarning" class="load-warning">{{ loadWarning }}</p>

    <div v-if="copyDialog.open" class="copy-dialog-backdrop">
      <section class="panel copy-dialog" role="dialog" aria-modal="true">
        <div>
          <p class="eyebrow">复制公共模板</p>
          <h3>{{ copyDialog.template?.name }}</h3>
        </div>
        <label class="field">
          <span class="field-label">新模板名称</span>
          <input v-model="copyDialog.name" class="text-input" placeholder="请输入副本名称" />
        </label>
        <label v-if="isAdmin" class="field">
          <span class="field-label">目标教练</span>
          <select v-model.number="copyDialog.targetOwnerUserId" class="text-input">
            <option :value="null">请选择教练</option>
            <option v-for="coach in coachOptions" :key="coach.id" :value="coach.id">{{ coach.display_name }}</option>
          </select>
        </label>
        <div class="dialog-actions">
          <button class="ghost-btn slim" type="button" :disabled="copyDialog.submitting" @click="closeCopyDialog">取消</button>
          <button class="primary-btn slim" type="button" :disabled="copyDialog.submitting" @click="submitCopyTemplate">
            {{ copyDialog.submitting ? '复制中...' : '确认复制' }}
          </button>
        </div>
      </section>
    </div>
  </AppShell>
</template>

<style scoped>
.template-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 18px;
  height: 100%;
  min-height: 0;
}

.sidebar,
.sidebar-head,
.template-list,
.builder-column,
.scope-fields {
  display: grid;
  gap: 14px;
  align-content: start;
}

.sidebar,
.builder-panel,
.builder-column {
  min-height: 0;
}

.sidebar {
  grid-template-rows: auto auto auto minmax(0, 1fr);
  overflow: hidden;
}

.template-scroll,
.builder-panel {
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.template-scroll {
  padding-right: 4px;
}

.sidebar-head {
  grid-template-columns: 1fr auto;
  align-items: center;
}

.eyebrow {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
}

.template-filter {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  padding: 6px;
  border-radius: 16px;
  background: var(--panel-soft);
}

.template-filter button {
  min-height: 38px;
  border: 1px solid transparent;
  border-radius: 12px;
  background: transparent;
  color: var(--text-soft);
  font-weight: 700;
}

.template-filter button.active {
  background: white;
  color: var(--text);
  border-color: rgba(15, 118, 110, 0.16);
}

.template-row {
  border-radius: 18px;
  background: var(--panel-soft);
  border: 1px solid transparent;
  display: grid;
  gap: 10px;
  padding: 12px;
  width: 100%;
  min-width: 0;
}

.template-pick {
  display: grid;
  gap: 6px;
  width: 100%;
  min-width: 0;
  padding: 4px;
  border: 0;
  background: transparent;
  text-align: left;
}

.template-row-head {
  display: flex;
  align-items: center;
  gap: 8px;
  justify-content: space-between;
  min-width: 0;
}

.template-row-head em {
  flex: 0 0 auto;
  padding: 4px 8px;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.1);
  color: #0f766e;
  font-style: normal;
  font-size: 12px;
  font-weight: 800;
}

.template-row strong,
.template-pick span,
.template-row small {
  min-width: 0;
  overflow-wrap: anywhere;
}

.template-row.active {
  background: #d1fae5;
  border-color: rgba(15, 118, 110, 0.18);
}

.template-pick span,
.template-row small {
  color: var(--text-soft);
}

.template-scope-panel {
  display: grid;
  gap: 12px;
}

.scope-fields {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.scope-hint {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
  font-weight: 700;
}

.action-message {
  margin: 0;
  padding: 12px 14px;
  border-radius: 14px;
  font-size: 13px;
  font-weight: 700;
}

.action-message--success {
  background: #dcfce7;
  color: #166534;
}

.action-message--error {
  background: #fee2e2;
  color: #991b1b;
}

.detail-loading {
  margin: 0;
  padding: 16px;
  border-radius: 18px;
  background: white;
  color: var(--text-soft);
  font-size: 14px;
  font-weight: 700;
}

.copy-dialog-backdrop {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: grid;
  place-items: center;
  padding: 20px;
  background: rgba(15, 23, 42, 0.42);
}

.copy-dialog {
  width: min(520px, 100%);
  display: grid;
  gap: 14px;
}

.dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.load-warning {
  margin: 12px 0 0;
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid rgba(245, 158, 11, 0.22);
  background: rgba(255, 247, 237, 0.92);
  color: #9a3412;
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 1180px) {
  .template-layout {
    grid-template-columns: 1fr;
    height: auto;
  }

  .scope-fields {
    grid-template-columns: 1fr;
  }
}
</style>
