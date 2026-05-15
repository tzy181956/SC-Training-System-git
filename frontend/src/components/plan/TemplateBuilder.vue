<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from 'vue'

import TemplateItemCard from './TemplateItemCard.vue'
import { buildDisplayLabel, moduleCodeFromOrder, resolveTemplateModules } from '@/utils/templateModules'
import { confirmDangerousAction } from '@/utils/dangerousAction'

const props = defineProps<{
  exercises: any[]
  testMetricOptions?: Array<{ id: number; label: string; name?: string; test_type_name?: string }>
  template: any | null
  saveNoticeKey?: number
  saving?: boolean
  readonly?: boolean
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

const draftModules = ref<any[]>([])
const draftItems = ref<any[]>([])
const removedItemIds = ref<number[]>([])
const removedModuleIds = ref<number[]>([])
const nextTempId = ref(-1)
const saveNotice = ref('')
const activeItemId = ref<number | null>(null)
const expandedModuleIds = ref<number[]>([])
let saveNoticeTimer: number | null = null

watch(
  () => props.template,
  (template) => {
    templateForm.name = template?.name || ''
    templateForm.description = template?.description || ''
    templateForm.is_active = template?.is_active ?? true

    nextTempId.value = -1
    const resolvedModules = resolveTemplateModules(template).map((module: any, moduleIndex: number) => {
      const moduleId = typeof module.id === 'number' ? module.id : nextTempId.value--
      return {
        ...module,
        id: moduleId,
        sort_order: module.sort_order || moduleIndex + 1,
        module_code: module.module_code || moduleCodeFromOrder(moduleIndex + 1),
        display_label: module.display_label || buildDisplayLabel(module.module_code || moduleCodeFromOrder(moduleIndex + 1)),
      }
    })
    draftModules.value = resolvedModules
    draftItems.value = resolvedModules
      .flatMap((module: any) =>
        (module.items || []).map((item: any, itemIndex: number) => ({
          ...item,
          module_id: item.module_id ?? module.id,
          module_code: item.module_code || module.module_code,
          module_title: item.module_title || module.title || '',
          display_index: item.display_index ?? itemIndex + 1,
          display_code: item.display_code || `${module.module_code}.${itemIndex + 1}`,
          progression_rules: { ...(item.progression_rules || {}) },
        })),
      )
      .sort((left, right) => left.sort_order - right.sort_order)
      .map((item, index) => ({
        ...item,
        sort_order: index + 1,
      }))
    removedItemIds.value = []
    removedModuleIds.value = []
    syncInteractionState({
      preferredItemId: draftItems.value[0]?.id || null,
      preferredExpandedModuleIds: resolvedModules[0]?.id ? [resolvedModules[0].id] : [],
    })
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

const sortedModules = computed(() =>
  [...draftModules.value]
    .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
    .map((module, moduleIndex) => {
      const moduleCode = module.module_code || moduleCodeFromOrder(module.sort_order || moduleIndex + 1)
      const items = draftItems.value
        .filter((item) => item.module_id === module.id)
        .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
        .map((item, itemIndex) => ({
          ...item,
          module_code: moduleCode,
          module_title: module.title || '',
          display_index: itemIndex + 1,
          display_code: `${moduleCode}.${itemIndex + 1}`,
        }))

      return {
        ...module,
        sort_order: module.sort_order || moduleIndex + 1,
        module_code: moduleCode,
        display_label: buildDisplayLabel(moduleCode),
        items,
      }
    }),
)

const moduleOptions = computed(() =>
  sortedModules.value.map((module) => ({
    id: module.id,
    label: module.title ? `${module.display_label} · ${module.title}` : module.display_label,
  })),
)
const saveButtonLabel = computed(() => {
  if (props.saving) return '保存中...'
  if (saveNotice.value) return '已保存'
  return '保存模板'
})
const readonlyNotice = computed(() => (props.readonly ? '公共模板只读，请先复制到我的模板后再修改。' : ''))

function buildNewModuleDraft() {
  return {
    id: nextTempId.value--,
    sort_order: draftModules.value.length + 1,
    title: '',
    note: '',
  }
}

function buildNewItemDraft(moduleId: number) {
  const moduleItems = [...draftItems.value]
    .filter((item) => item.module_id === moduleId)
    .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
  const lastItem = moduleItems[moduleItems.length - 1]

  return {
    id: nextTempId.value--,
    module_id: moduleId,
    exercise_id: 0,
    sort_order: draftItems.value.length + 1,
    prescribed_sets: lastItem?.prescribed_sets ?? 4,
    prescribed_reps: 5,
    target_note: '',
    is_main_lift: false,
    enable_auto_load: false,
    initial_load_mode: 'fixed_weight',
    initial_load_value: 60,
    initial_load_test_metric_definition_id: null,
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

function buildItemGroups(sourceItems = draftItems.value) {
  const groups = new Map<number, any[]>()
  sourceItems.forEach((item) => {
    const moduleId = item.module_id
    const bucket = groups.get(moduleId) || []
    bucket.push({
      ...item,
      progression_rules: { ...(item.progression_rules || {}) },
    })
    groups.set(moduleId, bucket)
  })
  return groups
}

function normalizeBuilderState(modulesInput = draftModules.value, itemGroups = buildItemGroups()) {
  const normalizedModules = [...modulesInput]
    .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
    .map((module, index) => {
      const moduleCode = moduleCodeFromOrder(index + 1)
      return {
        ...module,
        sort_order: index + 1,
        module_code: moduleCode,
        display_label: buildDisplayLabel(moduleCode),
      }
    })

  const normalizedItems: any[] = []
  normalizedModules.forEach((module) => {
    const moduleItems = [...(itemGroups.get(module.id) || [])]
    moduleItems.forEach((item, itemIndex) => {
      normalizedItems.push({
        ...item,
        module_id: module.id,
        module_code: module.module_code,
        module_title: module.title || '',
        display_index: itemIndex + 1,
        display_code: `${module.module_code}.${itemIndex + 1}`,
        sort_order: normalizedItems.length + 1,
        progression_rules: { ...(item.progression_rules || {}) },
      })
    })
  })

  draftModules.value = normalizedModules
  draftItems.value = normalizedItems
}

function syncInteractionState(options: {
  preferredItemId?: number | null
  preferredExpandedModuleIds?: number[]
} = {}) {
  const moduleIdSet = new Set(draftModules.value.map((module) => module.id))
  const nextExpanded = new Set(
    (options.preferredExpandedModuleIds ?? expandedModuleIds.value).filter((moduleId) => moduleIdSet.has(moduleId)),
  )

  let nextActiveItemId = options.preferredItemId ?? activeItemId.value
  if (!nextActiveItemId || !draftItems.value.some((item) => item.id === nextActiveItemId)) {
    nextActiveItemId = draftItems.value[0]?.id ?? null
  }
  activeItemId.value = nextActiveItemId

  const activeModuleId = draftItems.value.find((item) => item.id === activeItemId.value)?.module_id ?? null
  if (activeModuleId && moduleIdSet.has(activeModuleId)) {
    nextExpanded.add(activeModuleId)
  }

  if (!nextExpanded.size && draftModules.value[0]) {
    nextExpanded.add(draftModules.value[0].id)
  }

  expandedModuleIds.value = Array.from(nextExpanded)
}

function isPendingNewItem(item: any) {
  return Number(item?.id) < 0 && Number(item?.exercise_id || 0) <= 0
}

function getPinnedPendingItem(module: any) {
  const pendingItems = module.items.filter((item: any) => isPendingNewItem(item))
  if (!pendingItems.length) return null
  return pendingItems.find((item: any) => item.id === activeItemId.value) || pendingItems[pendingItems.length - 1]
}

function getVisibleModuleItems(module: any) {
  const pinnedItem = getPinnedPendingItem(module)
  return module.items.filter((item: any) => item.id !== pinnedItem?.id)
}

function getModuleItemIndex(module: any, itemId: number) {
  return module.items.findIndex((item: any) => item.id === itemId)
}

function keepSinglePendingItem(moduleId: number, preferredItemId?: number | null) {
  const pendingItems = [...draftItems.value]
    .filter((item) => item.module_id === moduleId && isPendingNewItem(item))
    .sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
  if (!pendingItems.length) return null

  const keptItem =
    pendingItems.find((item) => item.id === preferredItemId)
    || pendingItems[pendingItems.length - 1]
  const removedPendingIds = new Set(
    pendingItems
      .filter((item) => item.id !== keptItem.id)
      .map((item) => item.id),
  )

  if (removedPendingIds.size) {
    normalizeBuilderState(
      draftModules.value,
      buildItemGroups(draftItems.value.filter((item) => !removedPendingIds.has(item.id))),
    )
  }

  return draftItems.value.find((item) => item.id === keptItem.id) || keptItem
}

function scrollItemIntoView(itemId: number) {
  nextTick(() => {
    const target = document.querySelector<HTMLElement>(`[data-template-item-id="${itemId}"]`)
    if (!target) return

    window.requestAnimationFrame(() => {
      const scrollContainer = target.closest<HTMLElement>('.builder-panel')
      if (scrollContainer && scrollContainer.scrollHeight > scrollContainer.clientHeight) {
        const containerRect = scrollContainer.getBoundingClientRect()
        const targetRect = target.getBoundingClientRect()
        const targetOffset = targetRect.top - containerRect.top - (scrollContainer.clientHeight - targetRect.height) / 2
        scrollContainer.scrollTo({
          top: scrollContainer.scrollTop + targetOffset,
          behavior: 'smooth',
        })
        return
      }

      target.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
  })
}

function isModuleExpanded(moduleId: number) {
  return expandedModuleIds.value.includes(moduleId)
}

function toggleModuleExpanded(moduleId: number) {
  if (isModuleExpanded(moduleId)) {
    expandedModuleIds.value = expandedModuleIds.value.filter((id) => id !== moduleId)
    if (draftItems.value.find((item) => item.id === activeItemId.value)?.module_id === moduleId) {
      activeItemId.value = null
    }
    if (!expandedModuleIds.value.length && draftModules.value[0]) {
      expandedModuleIds.value = [draftModules.value[0].id]
    }
    return
  }

  expandedModuleIds.value = Array.from(new Set([...expandedModuleIds.value, moduleId]))
}

function toggleItemOpen(itemId: number) {
  if (activeItemId.value === itemId) {
    activeItemId.value = null
    return
  }

  activeItemId.value = itemId
  const moduleId = draftItems.value.find((item) => item.id === itemId)?.module_id
  if (moduleId && !expandedModuleIds.value.includes(moduleId)) {
    expandedModuleIds.value = Array.from(new Set([...expandedModuleIds.value, moduleId]))
  }
}

function focusItem(itemId: number) {
  activeItemId.value = itemId
  const moduleId = draftItems.value.find((item) => item.id === itemId)?.module_id
  if (moduleId && !expandedModuleIds.value.includes(moduleId)) {
    expandedModuleIds.value = Array.from(new Set([...expandedModuleIds.value, moduleId]))
  }
}

function addModule() {
  if (props.readonly) return
  normalizeBuilderState([...draftModules.value, buildNewModuleDraft()], buildItemGroups())
  syncInteractionState({
    preferredExpandedModuleIds: draftModules.value.map((module) => module.id),
  })
}

function updateModuleDraft(moduleId: number, payload: Record<string, unknown>) {
  if (props.readonly) return
  normalizeBuilderState(
    draftModules.value.map((module) => (module.id === moduleId ? { ...module, ...payload } : module)),
    buildItemGroups(),
  )
}

function moveModuleDraft(moduleId: number, direction: 'up' | 'down') {
  if (props.readonly) return
  const modules = [...draftModules.value].sort((left, right) => left.sort_order - right.sort_order || left.id - right.id)
  const index = modules.findIndex((module) => module.id === moduleId)
  const targetIndex = direction === 'up' ? index - 1 : index + 1
  if (index < 0 || targetIndex < 0 || targetIndex >= modules.length) return
  ;[modules[index], modules[targetIndex]] = [modules[targetIndex], modules[index]]
  normalizeBuilderState(modules, buildItemGroups())
  syncInteractionState()
}

function removeModuleDraft(moduleId: number) {
  if (props.readonly) return
  const targetModule = draftModules.value.find((module) => module.id === moduleId)
  if (!targetModule) return
  const moduleItems = draftItems.value.filter((item) => item.module_id === moduleId)
  if (
    (targetModule.id > 0 || moduleItems.length) &&
    !confirmDangerousAction({
      title: '删除训练模块',
      impactLines: [
        `${targetModule.display_label || '该模块'} ${targetModule.title ? `· ${targetModule.title}` : ''}`,
        `模块内动作数：${moduleItems.length}`,
        '保存模板后，该模块和仍留在其中的动作会一并删除',
      ],
    })
  ) {
    return
  }

  if (targetModule.id > 0) {
    removedModuleIds.value = Array.from(new Set([...removedModuleIds.value, targetModule.id]))
  }
  removedItemIds.value = Array.from(
    new Set([
      ...removedItemIds.value,
      ...moduleItems.filter((item) => item.id > 0).map((item) => item.id),
    ]),
  )

  normalizeBuilderState(
    draftModules.value.filter((module) => module.id !== moduleId),
    buildItemGroups(draftItems.value.filter((item) => item.module_id !== moduleId)),
  )
  syncInteractionState()
}

function addItem(moduleId: number) {
  if (props.readonly) return
  const existingPendingItem = keepSinglePendingItem(moduleId, activeItemId.value)
  if (existingPendingItem) {
    syncInteractionState({
      preferredItemId: existingPendingItem.id,
      preferredExpandedModuleIds: Array.from(new Set([...expandedModuleIds.value, moduleId])),
    })
    scrollItemIntoView(existingPendingItem.id)
    return
  }

  const itemGroups = buildItemGroups()
  const nextItem = buildNewItemDraft(moduleId)
  itemGroups.set(moduleId, [...(itemGroups.get(moduleId) || []), nextItem])
  normalizeBuilderState(draftModules.value, itemGroups)
  syncInteractionState({
    preferredItemId: nextItem.id,
    preferredExpandedModuleIds: Array.from(new Set([...expandedModuleIds.value, moduleId])),
  })
  scrollItemIntoView(nextItem.id)
}

function updateItemDraft(itemId: number, payload: Record<string, unknown>) {
  if (props.readonly) return
  const current = draftItems.value.find((item) => item.id === itemId)
  if (!current) return
  const nextItem = {
    ...current,
    ...payload,
    progression_rules: payload.progression_rules ? { ...payload.progression_rules } : { ...(current.progression_rules || {}) },
  }

  if (payload.module_id !== undefined && payload.module_id !== current.module_id) {
    const itemGroups = buildItemGroups(draftItems.value.filter((item) => item.id !== itemId))
    const targetModuleId = Number(payload.module_id)
    itemGroups.set(targetModuleId, [...(itemGroups.get(targetModuleId) || []), nextItem])
    normalizeBuilderState(draftModules.value, itemGroups)
    syncInteractionState({
      preferredItemId: itemId,
      preferredExpandedModuleIds: Array.from(new Set([...expandedModuleIds.value, targetModuleId])),
    })
    return
  }

  normalizeBuilderState(
    draftModules.value,
    buildItemGroups(
      draftItems.value.map((item) =>
        item.id === itemId
          ? nextItem
          : {
              ...item,
              progression_rules: { ...(item.progression_rules || {}) },
            },
      ),
    ),
  )
  syncInteractionState({
    preferredItemId: itemId,
  })
}

function removeItemDraft(itemId: number) {
  if (props.readonly) return
  const target = draftItems.value.find((item) => item.id === itemId)
  if (!target) return
  if (
    target.id > 0 &&
    !confirmDangerousAction({
      title: '删除模板动作',
      impactLines: [
        `模板内将移除动作“${target.exercise?.name || `动作 ${target.exercise_id}`}”`,
        '保存模板后，这条动作配置会从数据库删除',
      ],
    })
  ) {
    return
  }
  if (target.id > 0) {
    removedItemIds.value = Array.from(new Set([...removedItemIds.value, target.id]))
  }
  normalizeBuilderState(
    draftModules.value,
    buildItemGroups(draftItems.value.filter((item) => item.id !== itemId)),
  )
  syncInteractionState()
}

function moveItemDraft(itemId: number, direction: 'up' | 'down') {
  if (props.readonly) return
  const current = draftItems.value.find((item) => item.id === itemId)
  if (!current) return
  const itemGroups = buildItemGroups()
  const moduleItems = [...(itemGroups.get(current.module_id) || [])]
  const index = moduleItems.findIndex((item) => item.id === itemId)
  const targetIndex = direction === 'up' ? index - 1 : index + 1
  if (index < 0 || targetIndex < 0 || targetIndex >= moduleItems.length) return
  ;[moduleItems[index], moduleItems[targetIndex]] = [moduleItems[targetIndex], moduleItems[index]]
  itemGroups.set(current.module_id, moduleItems)
  normalizeBuilderState(draftModules.value, itemGroups)
  syncInteractionState({
    preferredItemId: itemId,
  })
}

function findFirstInvalidItem() {
  for (const module of sortedModules.value) {
    for (const item of module.items) {
      if (Number(item.exercise_id) > 0) continue
      return {
        moduleId: module.id,
        itemId: item.id,
        displayCode: item.display_code || `${module.module_code}.${item.display_index || 1}`,
      }
    }
  }
  return null
}

function saveTemplate() {
  if (props.readonly) return
  if (props.saving) return
  const invalidItem = findFirstInvalidItem()
  if (invalidItem) {
    expandedModuleIds.value = Array.from(new Set([...expandedModuleIds.value, invalidItem.moduleId]))
    activeItemId.value = invalidItem.itemId
    scrollItemIntoView(invalidItem.itemId)
    window.alert(`${invalidItem.displayCode} 还没有选择动作，请先补全或删除后再保存。`)
    return
  }
  emit('saveTemplate', {
    template: {
      name: templateForm.name,
      description: templateForm.description,
      is_active: templateForm.is_active,
    },
    modules: sortedModules.value.map((module, index) => ({
      id: module.id,
      sort_order: index + 1,
      title: module.title || null,
      note: module.note || null,
    })),
    items: draftItems.value.map((item, index) => ({
      id: item.id,
      module_id: item.module_id,
      exercise_id: item.exercise_id,
      sort_order: index + 1,
      prescribed_sets: item.prescribed_sets,
      prescribed_reps: item.prescribed_reps,
      target_note: item.target_note,
      is_main_lift: item.is_main_lift,
      enable_auto_load: item.enable_auto_load,
      initial_load_mode: item.initial_load_mode,
      initial_load_value: item.initial_load_value,
      initial_load_test_metric_definition_id:
        item.initial_load_mode === 'percent_1rm' ? item.initial_load_test_metric_definition_id : null,
      progression_goal: item.progression_goal,
      progression_rules: { ...(item.progression_rules || {}) },
      ai_adjust_enabled: item.ai_adjust_enabled,
    })),
    removedItemIds: [...removedItemIds.value],
    removedModuleIds: [...removedModuleIds.value],
  })
}

function moduleSummary(module: any) {
  if (module.note) return module.note
  if (module.items.length) return `${module.items.length} 个动作`
  return '当前模块还没有动作。'
}

function removeTemplate() {
  if (props.readonly) return
  if (!props.template?.id) return
  const confirmed = confirmDangerousAction({
    title: '删除训练模板',
    impactLines: [
      `模板名称：${props.template.name}`,
      `模板模块数：${props.template.modules?.length || sortedModules.value.length || 0}`,
      `模板动作数：${props.template.items?.length || draftItems.value.length || 0}`,
      '删除后模板本身及其动作配置将不可直接恢复',
    ],
  })
  if (!confirmed) return
  emit('deleteTemplate', props.template.id)
}
</script>

<template>
  <section class="builder-wrap">
    <div class="panel builder-header">
      <div class="header-copy">
        <p class="eyebrow">模板基础信息</p>
        <h3>{{ readonly ? '查看训练模板' : template?.id ? '编辑训练模板' : '新建训练模板' }}</h3>
      </div>
      <div class="header-actions">
        <button v-if="template?.id && !readonly" class="ghost-btn slim danger-btn" type="button" @click="removeTemplate">删除模板</button>
        <button v-if="!readonly" class="primary-btn slim" type="button" :disabled="saving" @click="saveTemplate">{{ saveButtonLabel }}</button>
      </div>

      <p v-if="saveNotice" class="save-notice">{{ saveNotice }}</p>
      <p v-if="readonlyNotice" class="readonly-notice">{{ readonlyNotice }}</p>

      <div class="grid two">
        <label class="field">
          <span class="field-label">模板名称 <strong class="required-mark">*</strong></span>
          <input v-model="templateForm.name" class="text-input" :disabled="readonly" placeholder="例如：力量训练 A、下肢爆发 B" />
        </label>
        <label class="field">
          <span class="field-label">状态</span>
          <select v-model="templateForm.is_active" class="text-input" :disabled="readonly">
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
          :disabled="readonly"
          placeholder="例如：适用于下肢主项日，目标是基础力量与动作质量。"
        />
      </label>
    </div>

    <div class="panel quick-add-panel">
      <div class="quick-header">
        <div>
          <p class="eyebrow">添加模块</p>
          <h3>训练模块</h3>
        </div>
        <button v-if="!readonly" class="primary-btn slim" type="button" @click="addModule">添加模块</button>
      </div>
      <p class="hint">一个模块代表一段连续训练内容，例如模块 A 中的 4 个动作循环完成后，再进入模块 B。</p>
    </div>

    <div class="module-list">
      <section
        v-for="(module, moduleIndex) in sortedModules"
        :key="module.id"
        class="panel module-card"
        :class="{ 'module-card--collapsed': !isModuleExpanded(module.id) }"
      >
        <div class="module-head">
          <div class="module-copy">
            <p class="module-eyebrow">{{ module.display_label }}</p>
            <h4>{{ module.title || `${module.display_label}（未命名）` }}</h4>
            <p class="module-meta">{{ module.items.length }} 个动作</p>
          </div>
          <div class="header-actions">
            <button class="ghost-btn slim-btn" type="button" @click="toggleModuleExpanded(module.id)">
              {{ isModuleExpanded(module.id) ? '收起模块' : '展开模块' }}
            </button>
            <button v-if="!readonly" class="slim-btn" type="button" :disabled="moduleIndex === 0" @click="moveModuleDraft(module.id, 'up')">上移模块</button>
            <button
              v-if="!readonly"
              class="slim-btn"
              type="button"
              :disabled="moduleIndex === sortedModules.length - 1"
              @click="moveModuleDraft(module.id, 'down')"
            >
              下移模块
            </button>
            <button v-if="!readonly" class="ghost-btn slim-btn danger-btn" type="button" @click="removeModuleDraft(module.id)">删除模块</button>
          </div>
        </div>

        <p v-if="!isModuleExpanded(module.id)" class="module-collapsed-summary">{{ moduleSummary(module) }}</p>

        <template v-else>
          <div class="grid two">
            <label class="field">
              <span class="field-label">模块标题</span>
              <input
                :value="module.title"
                class="text-input"
                :disabled="readonly"
                placeholder="例如：主项循环、辅助力量、速度补充"
                @input="updateModuleDraft(module.id, { title: ($event.target as HTMLInputElement).value })"
              />
            </label>
            <label class="field">
              <span class="field-label">模块说明</span>
              <input
                :value="module.note"
                class="text-input"
                :disabled="readonly"
                placeholder="例如：4 个动作循环 3 轮，组间快切"
                @input="updateModuleDraft(module.id, { note: ($event.target as HTMLInputElement).value })"
              />
            </label>
          </div>

          <div class="module-actions">
            <button v-if="!readonly" class="primary-btn slim" type="button" @click="addItem(module.id)">在 {{ module.display_label }} 中添加动作</button>
          </div>

          <div
            v-if="getPinnedPendingItem(module)"
            class="template-item-anchor pending-item-anchor"
            :data-template-item-id="getPinnedPendingItem(module).id"
          >
            <TemplateItemCard
              :item="getPinnedPendingItem(module)"
              :item-label="getPinnedPendingItem(module).display_code"
              :module-options="moduleOptions"
              :move-up-disabled="getModuleItemIndex(module, getPinnedPendingItem(module).id) <= 0"
              :move-down-disabled="getModuleItemIndex(module, getPinnedPendingItem(module).id) === module.items.length - 1"
              :exercises="exercises"
              :test-metric-options="testMetricOptions || []"
              :readonly="readonly"
              :active="true"
              :open="true"
              @change="updateItemDraft"
              @remove="removeItemDraft"
              @move="moveItemDraft"
              @toggle-open="toggleItemOpen"
              @focus="focusItem"
            />
          </div>

          <div class="module-items">
            <div
              v-for="item in getVisibleModuleItems(module)"
              :key="`${template?.id || 'draft'}-${item.id}`"
              class="template-item-anchor"
              :data-template-item-id="item.id"
            >
              <TemplateItemCard
                :item="item"
                :item-label="item.display_code"
                :module-options="moduleOptions"
                :move-up-disabled="getModuleItemIndex(module, item.id) <= 0"
                :move-down-disabled="getModuleItemIndex(module, item.id) === module.items.length - 1"
                :exercises="exercises"
                :test-metric-options="testMetricOptions || []"
                :readonly="readonly"
                :active="item.id === activeItemId"
                :open="item.id === activeItemId"
                @change="updateItemDraft"
                @remove="removeItemDraft"
                @move="moveItemDraft"
                @toggle-open="toggleItemOpen"
                @focus="focusItem"
              />
            </div>
            <div v-if="!module.items.length" class="empty-module">
              <h5>{{ module.display_label }} 还没有动作</h5>
              <p>可在这个模块中添加动作。</p>
            </div>
          </div>
        </template>
      </section>

      <div v-if="!sortedModules.length" class="panel empty-panel">
        <h4>当前模板还没有模块</h4>
        <p>填写模板基础信息后，可添加训练模块和动作。</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.builder-wrap,
.builder-header,
.quick-add-panel,
.module-list,
.empty-panel,
.module-card,
.module-items {
  display: grid;
  gap: 16px;
}

.builder-wrap {
  height: 100%;
  min-height: 0;
  align-content: start;
}

.header-actions,
.quick-header,
.module-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.module-copy {
  display: grid;
  gap: 6px;
}

.module-copy h4,
.module-copy p {
  margin: 0;
}

.module-eyebrow,
.module-meta,
.eyebrow,
.hint,
.save-notice,
.readonly-notice {
  color: var(--muted);
  font-size: 13px;
}

.eyebrow,
.hint,
.save-notice,
.readonly-notice,
.module-eyebrow,
.module-meta {
  margin: 0;
}

.save-notice {
  padding: 10px 12px;
  border-radius: 14px;
  background: #dcfce7;
  color: #166534;
  font-weight: 600;
}

.readonly-notice {
  padding: 10px 12px;
  border-radius: 14px;
  background: #f8fafc;
  color: #475569;
  font-weight: 700;
}

.grid {
  display: grid;
  gap: 12px;
}

.grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.module-card {
  background: rgba(240, 253, 250, 0.76);
  border: 1px solid rgba(15, 118, 110, 0.14);
}

.template-item-anchor {
  min-width: 0;
}

.pending-item-anchor {
  padding: 4px;
  border-radius: 22px;
  background: rgba(15, 118, 110, 0.08);
  border: 1px dashed rgba(15, 118, 110, 0.28);
}

.module-card--collapsed {
  gap: 12px;
}

.module-actions {
  display: flex;
  justify-content: flex-start;
}

.module-collapsed-summary {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
  line-height: 1.5;
}

.empty-module {
  padding: 18px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.66);
}

.empty-module h5,
.empty-module p {
  margin: 0;
}

@media (max-width: 1200px) {
  .grid.two {
    grid-template-columns: 1fr;
  }
}
</style>
