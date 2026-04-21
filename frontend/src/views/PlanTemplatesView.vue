<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { fetchExercises } from '@/api/exercises'
import {
  addPlanTemplateItem,
  createPlanTemplate,
  deletePlanTemplate,
  deletePlanTemplateItem,
  fetchPlanTemplates,
  updatePlanTemplate,
  updatePlanTemplateItem,
} from '@/api/plans'
import AppShell from '@/components/layout/AppShell.vue'
import TemplateBuilder from '@/components/plan/TemplateBuilder.vue'

const templates = ref<any[]>([])
const exercises = ref<any[]>([])
const selectedTemplateId = ref<number | null>(null)
const keyword = ref('')
const saveNoticeKey = ref(0)

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

async function hydrate(preferredTemplateId?: number | null) {
  const [templateData, exerciseData] = await Promise.all([fetchPlanTemplates(), fetchExercises()])
  templates.value = templateData
  exercises.value = exerciseData
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
  const templatePayload = payload.template || {}
  const itemsPayload = (payload.items || []) as Record<string, any>[]
  const removedItemIds = (payload.removedItemIds || []) as number[]

  if (selectedTemplate.value?.id) {
    await updatePlanTemplate(selectedTemplate.value.id, templatePayload)
    for (const itemId of removedItemIds) {
      await deletePlanTemplateItem(itemId)
    }
    for (const item of itemsPayload) {
      const normalized = { ...item }
      delete normalized.id
      if (item.id > 0) {
        await updatePlanTemplateItem(item.id, normalized)
      } else {
        await addPlanTemplateItem(selectedTemplate.value.id, normalized)
      }
    }
    await hydrate(selectedTemplate.value.id)
    saveNoticeKey.value += 1
    return
  }

  const created = await createPlanTemplate({
    ...templatePayload,
    sport_id: null,
    team_id: null,
  })
  for (const item of itemsPayload) {
    const normalized = { ...item }
    delete normalized.id
    await addPlanTemplateItem(created.id, normalized)
  }
  await hydrate(created.id)
  saveNoticeKey.value += 1
}

async function removeTemplate(templateId: number) {
  await deletePlanTemplate(templateId)
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
              <small>{{ template.items.length }} 个动作</small>
            </button>
          </div>
        </div>
      </aside>

      <TemplateBuilder
        class="builder-panel"
        :template="selectedTemplate"
        :exercises="exercises"
        :save-notice-key="saveNoticeKey"
        @save-template="saveTemplate"
        @delete-template="removeTemplate"
      />
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

@media (max-width: 1180px) {
  .template-layout {
    grid-template-columns: 1fr;
    height: auto;
  }
}
</style>
