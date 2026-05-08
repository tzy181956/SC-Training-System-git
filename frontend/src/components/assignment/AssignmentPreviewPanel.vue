<script setup lang="ts">
import { computed } from 'vue'

import { formatRepeatWeekdays } from '@/constants/repeatWeekdays'
import { resolveTemplateModules } from '@/utils/templateModules'

const props = defineProps<{
  preview: any | null
  selectedTemplate: any | null
}>()

const displayTemplate = computed(() => props.preview?.template ?? props.selectedTemplate ?? null)
const hasGeneratedPreview = computed(() => Boolean(props.preview))

const athleteSummaries = computed(() =>
  (props.preview?.rows ?? []).map((row: any) => ({
    id: row.athlete.id,
    fullName: row.athlete.full_name,
    teamName: row.athlete.team?.name || '未分队',
  })),
)

const displayModules = computed(() => {
  const firstRowItems = new Map<number, any>(
    (props.preview?.rows?.[0]?.items ?? []).map((item: any) => [item.template_item_id, item]),
  )

  return resolveTemplateModules(displayTemplate.value).map((module: any) => ({
    ...module,
    items: (module.items || []).map((item: any) => {
      const previewItem = firstRowItems.get(item.id)
      return {
        ...item,
        exerciseName: item.exercise?.name || previewItem?.exercise_name || '未命名动作',
        loadModeLabel: buildLoadRuleLabel(item, previewItem),
        detailText: buildLoadDetailText(item),
      }
    }),
  }))
})

const missingBasisGroups = computed(() =>
  (props.preview?.rows ?? [])
    .map((row: any) => {
      const missingItems = (row.items ?? []).filter((item: any) => item.status === 'missing_basis')
      if (!missingItems.length) {
        return null
      }
      return {
        athleteId: row.athlete.id,
        fullName: row.athlete.full_name,
        teamName: row.athlete.team?.name || '未分队',
        exerciseNames: missingItems.map((item: any) => item.exercise_name),
      }
    })
    .filter(Boolean),
)

const missingBasisCount = computed(() => missingBasisGroups.value.length)

function buildLoadRuleLabel(templateItem: any, previewItem?: any) {
  if (templateItem.initial_load_mode === 'fixed_weight') {
    return '固定重量'
  }
  if (templateItem.initial_load_mode === 'percent_1rm') {
    return '按最近测试百分比'
  }
  return previewItem?.load_mode_label || '训练时设置'
}

function buildLoadDetailText(templateItem: any) {
  const value = templateItem.initial_load_value
  if (templateItem.initial_load_mode === 'fixed_weight') {
    return value === null || value === undefined ? '固定重量未设置' : `${formatNumber(value)} 公斤`
  }
  if (templateItem.initial_load_mode === 'percent_1rm') {
    return value === null || value === undefined ? '按最近测试结果计算' : `按最近测试的 ${formatNumber(value)}%`
  }
  return '训练时设置'
}

function formatNumber(value: number) {
  if (Number.isInteger(value)) {
    return `${value}`
  }
  return `${value}`.replace(/\.?0+$/, '')
}
</script>

<template>
  <section class="panel preview-panel">
    <div class="section-head">
      <div>
        <p class="eyebrow">第四步</p>
        <h3>分配预览</h3>
      </div>
      <div v-if="displayTemplate" class="meta">
        <span v-if="preview">{{ preview.start_date }} 至 {{ preview.end_date }}</span>
        <span v-if="preview">{{ formatRepeatWeekdays(preview.repeat_weekdays) }}</span>
        <span v-else>已加载模板内容</span>
        <strong>{{ displayTemplate.name }}</strong>
      </div>
    </div>

    <div v-if="!displayTemplate" class="empty-state">
      <h4>请先选择训练模板</h4>
      <p>模板一经选中，这里就会先显示模板内容；选择队员、时间范围和循环星期后，会继续显示完整分配预览。</p>
    </div>

    <div v-else class="preview-body">
      <article v-if="hasGeneratedPreview" class="preview-card">
        <div class="card-head">
          <div>
            <p class="eyebrow">将分配给以下队员</p>
            <h4>共 {{ athleteSummaries.length }} 人</h4>
          </div>
        </div>
        <div class="athlete-list">
          <div v-for="athlete in athleteSummaries" :key="athlete.id" class="athlete-chip">
            <strong>{{ athlete.fullName }}</strong>
            <span>{{ athlete.teamName }}</span>
          </div>
        </div>
      </article>

      <article class="preview-card">
        <div class="card-head">
          <div>
            <p class="eyebrow">本次分配的训练模板</p>
            <h4>{{ displayTemplate.name }}</h4>
          </div>
        </div>
        <p v-if="displayTemplate.description" class="template-description">{{ displayTemplate.description }}</p>
        <div class="module-grid">
          <section v-for="module in displayModules" :key="module.id || module.module_code" class="module-block">
            <header class="module-head">
              <div>
                <p class="eyebrow">{{ module.display_label }}</p>
                <h5>{{ module.title || `${module.display_label}（未命名）` }}</h5>
                <p v-if="module.note" class="module-note">{{ module.note }}</p>
              </div>
            </header>
            <div class="item-grid">
              <div v-for="item in module.items" :key="item.id" class="item-row">
                <div>
                  <strong>{{ item.display_code }} {{ item.exerciseName }}</strong>
                  <p>{{ item.loadModeLabel }}</p>
                </div>
                <div class="item-side">
                  <span>{{ item.detailText }}</span>
                </div>
              </div>
            </div>
          </section>
        </div>
      </article>

      <article v-if="!hasGeneratedPreview" class="preview-card helper-panel">
        <div class="card-head">
          <div>
            <p class="eyebrow">下一步</p>
            <h4>继续选择队员、时间范围和循环星期</h4>
          </div>
        </div>
        <p class="muted">当前先展示模板内容。选择队员、时间范围和循环星期后，这里会继续显示分配对象与异常提示。</p>
      </article>

      <article v-if="hasGeneratedPreview && missingBasisGroups.length" class="preview-card warning-panel">
        <div class="card-head">
          <div>
            <p class="eyebrow">需要先补齐的测试基准</p>
            <h4>{{ missingBasisCount }} 名队员存在缺失项</h4>
          </div>
        </div>
        <div class="warning-list">
          <div v-for="group in missingBasisGroups" :key="group.athleteId" class="warning-row">
            <div>
              <strong>{{ group.fullName }}</strong>
              <span>{{ group.teamName }}</span>
            </div>
            <small>{{ group.exerciseNames.join('、') }}</small>
          </div>
        </div>
      </article>
    </div>
  </section>
</template>

<style scoped>
.preview-panel,
.preview-body,
.preview-card,
.module-grid,
.module-block,
.item-grid,
.athlete-list,
.warning-list {
  display: grid;
  gap: 14px;
}

.section-head,
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.eyebrow,
.meta span,
.athlete-chip span,
.item-row p,
.warning-row span,
.warning-row small {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
}

.meta,
.item-side {
  display: grid;
  gap: 4px;
  text-align: right;
}

.preview-card {
  padding: 16px;
  border-radius: 18px;
  background: var(--panel-soft);
}

.module-block {
  padding: 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
}

.module-head h5,
.module-note {
  margin: 0;
}

.module-note {
  color: var(--text-soft);
  font-size: 13px;
}

.template-description {
  margin: 0;
  color: var(--text-soft);
}

.athlete-list {
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}

.athlete-chip,
.item-row,
.warning-row {
  display: grid;
  gap: 4px;
  padding: 12px 14px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
}

.item-row {
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: center;
}

.warning-panel {
  border: 1px solid rgba(220, 38, 38, 0.16);
  background: rgba(254, 242, 242, 0.86);
}

.helper-panel {
  border: 1px solid rgba(15, 118, 110, 0.12);
  background: rgba(240, 253, 250, 0.8);
}

.warning-list {
  gap: 10px;
}

.warning-row {
  grid-template-columns: 1fr auto;
  align-items: center;
  background: rgba(255, 255, 255, 0.78);
}

.empty-state {
  padding: 28px;
  border-radius: 18px;
  background: var(--panel-soft);
}

@media (max-width: 900px) {
  .item-row,
  .warning-row {
    grid-template-columns: 1fr;
  }

  .item-side {
    text-align: left;
  }
}
</style>
