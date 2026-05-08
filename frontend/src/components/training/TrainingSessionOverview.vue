<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'

import { resolveTemplateModules } from '@/utils/templateModules'

const props = defineProps<{
  assignment?: any | null
  session?: any | null
  athleteName?: string | null
  activeItemId?: number | null
  onSelectItem?: ((itemId: number) => void) | null
}>()

const items = computed(() => props.session?.items || props.assignment?.template?.items || [])
const modules = computed(() => {
  if (props.session?.modules?.length) return props.session.modules
  if (props.assignment?.template) return resolveTemplateModules(props.assignment.template)
  return []
})
const showCurrentAthlete = computed(() => !props.session)
const itemListRef = ref<HTMLElement | null>(null)

function formatNumber(value: number) {
  if (Number.isInteger(value)) {
    return `${value}`
  }
  return `${value}`.replace(/\.?0+$/, '')
}

function findAssignmentOverride(item: any) {
  return props.assignment?.overrides?.find((override: any) => override.template_item_id === item.id) || null
}

function buildLoadText(item: any) {
  const override = findAssignmentOverride(item)
  if (override?.initial_load_override !== null && override?.initial_load_override !== undefined) {
    return `${formatNumber(Number(override.initial_load_override))} 公斤`
  }

  if (item.initial_load !== null && item.initial_load !== undefined) {
    return `${formatNumber(Number(item.initial_load))} 公斤`
  }

  if (item.initial_load_mode === 'fixed_weight') {
    return item.initial_load_value === null || item.initial_load_value === undefined
      ? '训练时设置'
      : `${formatNumber(Number(item.initial_load_value))} 公斤`
  }

  if (item.initial_load_mode === 'percent_1rm') {
    return item.initial_load_value === null || item.initial_load_value === undefined
      ? '按最近测试百分比'
      : `${formatNumber(Number(item.initial_load_value))}%`
  }

  return '训练时设置'
}

function buildPrescriptionSummary(item: any) {
  return `${item.prescribed_sets} 组 × ${item.prescribed_reps} 次 × ${buildLoadText(item)}`
}

function buildProgressSummary(item: any) {
  return `${item.records?.length || 0}/${item.prescribed_sets}组`
}

async function scrollActiveItemIntoView() {
  if (!props.session || !props.activeItemId) return
  await nextTick()
  const activeElement = itemListRef.value?.querySelector<HTMLElement>(`[data-item-id="${props.activeItemId}"]`)
  activeElement?.scrollIntoView({ block: 'nearest' })
}

watch(
  () => [props.activeItemId, items.value.length],
  () => {
    void scrollActiveItemIntoView()
  },
  { immediate: true },
)
</script>

<template>
  <section class="panel overview">
    <div v-if="session || assignment" class="heading">
      <div class="heading-copy">
        <p class="section-title">4. 查看计划</p>
        <h3>{{ assignment?.template?.name || '未选择计划' }}</h3>
        <p v-if="showCurrentAthlete" class="current-athlete">当前队员：{{ athleteName || '未选择队员' }}</p>
      </div>
      <div class="meta">
        <span>{{ modules.length || 0 }} 个模块 / {{ items.length }} 个动作</span>
        <span>{{ assignment?.notes || session?.coach_note || '按动作顺序完成即可' }}</span>
      </div>
    </div>

    <div v-else class="empty-state">
      <strong>先选择日期，再选择队员。</strong>
      <span>如果该队员当天有多份计划，会直接显示在队员名字下方供点击选择。</span>
    </div>

    <div v-if="items.length" ref="itemListRef" class="item-list">
      <section v-for="module in modules" :key="module.id || module.module_code" class="module-block">
        <header class="module-head">
          <div class="heading-copy">
            <p class="section-title">{{ module.display_label }}</p>
            <strong>{{ module.title || `${module.display_label}（未命名）` }}</strong>
            <span v-if="module.note" class="module-note">{{ module.note }}</span>
          </div>
        </header>

        <button
          v-for="item in module.items"
          :key="item.id"
          :data-item-id="item.id"
          class="item-card"
          :class="{
            active: session && item.id === activeItemId,
            'item-card--interactive': Boolean(session && onSelectItem),
          }"
          type="button"
          @click="session && onSelectItem && onSelectItem(item.id)"
        >
          <strong class="item-title" :title="item.exercise.name">
            {{ item.display_code ? `${item.display_code} ${item.exercise.name}` : item.exercise.name }}
          </strong>
          <span class="prescription-summary" :title="buildPrescriptionSummary(item)">{{ buildPrescriptionSummary(item) }}</span>
          <em v-if="session" class="progress-summary">{{ buildProgressSummary(item) }}</em>
        </button>
      </section>
    </div>
  </section>
</template>

<style scoped>
.overview,
.heading,
.item-list,
.module-block,
.empty-state {
  display: grid;
  gap: 12px;
}

.overview {
  gap: 16px;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 0;
}

.heading-copy {
  display: grid;
  gap: 8px;
}

.heading h3,
.section-title,
.meta span,
.empty-state span {
  margin: 0;
  color: var(--muted);
}

.current-athlete {
  margin: 0;
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  background: var(--panel-soft);
  color: var(--text);
  font-size: 13px;
  line-height: 1.2;
  font-weight: 700;
}

.item-list {
  min-height: 0;
  overflow-y: auto;
  padding-right: 6px;
  scrollbar-gutter: stable;
  align-content: start;
}

.module-block {
  padding: 14px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.9);
}

.module-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.module-note {
  color: var(--muted);
  font-size: 13px;
}

.item-card {
  background: var(--panel-soft);
  border-radius: 16px;
  padding: 13px 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  min-height: 56px;
  text-align: left;
  cursor: default;
}

.item-card--interactive {
  cursor: pointer;
}

.item-card.active {
  background: #dbeafe;
}

.item-title {
  flex: 1 1 auto;
  min-width: 0;
  margin: 0;
  color: var(--text);
  font-size: 1.12rem;
  line-height: 1.15;
  font-weight: 800;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.prescription-summary {
  flex: 0 1 auto;
  min-width: 0;
  margin: 0;
  color: var(--text);
  font-size: 0.98rem;
  line-height: 1.2;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.progress-summary {
  flex: 0 0 auto;
  margin: 0;
  font-style: normal;
  color: var(--primary);
  font-size: 0.96rem;
  line-height: 1.2;
  font-weight: 800;
  white-space: nowrap;
}

@media (min-width: 768px) and (max-width: 1199px) {
  .overview {
    gap: 12px;
  }

  .heading {
    gap: 8px;
  }

  .heading-copy {
    gap: 6px;
  }

  .current-athlete {
    padding: 5px 8px;
    font-size: 12px;
  }

  .item-list {
    padding-right: 4px;
  }

  .item-card {
    gap: 12px;
    padding: 11px 14px;
    border-radius: 14px;
  }

  .item-title {
    font-size: 1.03rem;
  }

  .prescription-summary,
  .progress-summary {
    font-size: 0.9rem;
  }
}
</style>
