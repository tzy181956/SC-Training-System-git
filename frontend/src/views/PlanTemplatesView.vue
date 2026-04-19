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

async function saveTemplate(payload: Record<string, unknown>) {
  if (selectedTemplate.value?.id) {
    await updatePlanTemplate(selectedTemplate.value.id, payload)
    await hydrate(selectedTemplate.value.id)
    return
  }

  const created = await createPlanTemplate({
    ...payload,
    sport_id: null,
    team_id: null,
  })
  await hydrate(created.id)
}

async function removeTemplate(templateId: number) {
  await deletePlanTemplate(templateId)
  selectedTemplateId.value = null
  await hydrate()
}

async function addItem(payload: Record<string, unknown>) {
  if (!selectedTemplate.value?.id) return
  await addPlanTemplateItem(selectedTemplate.value.id, payload)
  await hydrate(selectedTemplate.value.id)
}

async function updateItem(itemId: number, payload: Record<string, unknown>) {
  await updatePlanTemplateItem(itemId, payload)
  await hydrate(selectedTemplate.value?.id)
}

async function removeItem(itemId: number) {
  await deletePlanTemplateItem(itemId)
  await hydrate(selectedTemplate.value?.id)
}

async function moveItem(itemId: number, direction: 'up' | 'down') {
  if (!selectedTemplate.value) return
  const items = [...selectedTemplate.value.items].sort((left, right) => left.sort_order - right.sort_order)
  const index = items.findIndex((item) => item.id === itemId)
  const targetIndex = direction === 'up' ? index - 1 : index + 1
  if (index < 0 || targetIndex < 0 || targetIndex >= items.length) return

  const current = items[index]
  const target = items[targetIndex]

  await Promise.all([
    updatePlanTemplateItem(current.id, { sort_order: target.sort_order }),
    updatePlanTemplateItem(target.id, { sort_order: current.sort_order }),
  ])
  await hydrate(selectedTemplate.value.id)
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
        <input v-model="keyword" class="text-input" placeholder="搜索模板名称或说明" />
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
      </aside>

      <TemplateBuilder
        :template="selectedTemplate"
        :exercises="exercises"
        @save-template="saveTemplate"
        @delete-template="removeTemplate"
        @add-item="addItem"
        @update-item="updateItem"
        @delete-item="removeItem"
        @move-item="moveItem"
      />
    </div>
  </AppShell>
</template>

<style scoped>
.template-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 18px;
}

.sidebar,
.sidebar-head,
.template-list {
  display: grid;
  gap: 14px;
  align-content: start;
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
  }
}
</style>
