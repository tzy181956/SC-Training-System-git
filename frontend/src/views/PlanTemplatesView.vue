<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchAllExerciseListItems } from '@/api/exercises'
import {
  addPlanTemplateItem,
  addPlanTemplateModule,
  createPlanTemplate,
  deletePlanTemplate,
  deletePlanTemplateItem,
  deletePlanTemplateModule,
  fetchPlanTemplates,
  updatePlanTemplate,
  updatePlanTemplateItem,
  updatePlanTemplateModule,
} from '@/api/plans'
import { fetchTestDefinitions } from '@/api/testRecords'
import AppShell from '@/components/layout/AppShell.vue'
import TemplateBuilder from '@/components/plan/TemplateBuilder.vue'

const templates = ref<any[]>([])
const exercises = ref<any[]>([])
const testMetricOptions = ref<any[]>([])
const selectedTemplateId = ref<number | null>(null)
const keyword = ref('')
const saveNoticeKey = ref(0)
const savingTemplate = ref(false)
const loadWarning = ref('')

const selectedTemplate = computed(
  () => templates.value.find((template) => template.id === selectedTemplateId.value) || null,
)

const filteredTemplates = computed(() => {
  const search = keyword.value.trim()
  if (!search) return templates.value
  return templates.value.filter(
    (template) => template.name.includes(search) || (template.description || '').includes(search),
  )
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
  loadWarning.value = ''
  const [templateResult, exerciseResult, testDefinitionResult] = await Promise.allSettled([
    fetchPlanTemplates(),
    fetchAllExerciseListItems(),
    fetchTestDefinitions(),
  ])
  if (templateResult.status !== 'fulfilled') {
    throw templateResult.reason
  }

  templates.value = templateResult.value
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

  if (preferredTemplateId && templates.value.some((template) => template.id === preferredTemplateId)) {
    selectedTemplateId.value = preferredTemplateId
    return
  }
  if (!selectedTemplateId.value && templates.value[0]) {
    selectedTemplateId.value = templates.value[0].id
  }
}

function createDraftTemplate() {
  selectedTemplateId.value = null
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
      await updatePlanTemplate(selectedTemplate.value.id, templatePayload)
      await persistTemplateGraph(selectedTemplate.value.id)
      await hydrate(selectedTemplate.value.id)
      saveNoticeKey.value += 1
      return
    }

    const created = await createPlanTemplate({
      ...templatePayload,
      sport_id: null,
      team_id: null,
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

onMounted(() => hydrate())
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

        <div class="template-scroll">
          <div class="template-list">
            <button
              v-for="template in filteredTemplates"
              :key="template.id"
              class="template-row"
              :class="{ active: template.id === selectedTemplateId }"
              type="button"
              @click="selectedTemplateId = template.id"
            >
              <strong>{{ template.name }}</strong>
              <span>{{ template.description || '暂无说明' }}</span>
              <small>{{ template.modules?.length || 0 }} 个模块 / {{ template.items?.length || 0 }} 个动作</small>
            </button>
          </div>
        </div>
      </aside>

      <TemplateBuilder
        class="builder-panel"
        :template="selectedTemplate"
        :exercises="exercises"
        :test-metric-options="testMetricOptions"
        :save-notice-key="saveNoticeKey"
        :saving="savingTemplate"
        @save-template="saveTemplate"
        @delete-template="removeTemplate"
      />
    </div>
    <p v-if="loadWarning" class="load-warning">{{ loadWarning }}</p>
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
.template-list {
  display: grid;
  gap: 14px;
  align-content: start;
}

.sidebar,
.builder-panel {
  min-height: 0;
}

.sidebar {
  grid-template-rows: auto auto minmax(0, 1fr);
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

.template-row {
  min-height: var(--touch);
  border-radius: 18px;
  padding: 16px;
  text-align: left;
  background: var(--panel-soft);
  border: 1px solid transparent;
  display: grid;
  gap: 6px;
  width: 100%;
  min-width: 0;
}

.template-row strong,
.template-row span,
.template-row small {
  min-width: 0;
  overflow-wrap: anywhere;
}

.template-row.active {
  background: #d1fae5;
  border-color: rgba(15, 118, 110, 0.18);
}

.template-row span,
.template-row small {
  color: var(--text-soft);
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
}
</style>
