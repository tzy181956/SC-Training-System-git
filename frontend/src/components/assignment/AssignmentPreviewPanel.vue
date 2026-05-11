<script setup lang="ts">
import { computed, ref } from 'vue'

import { resolveTemplateModules } from '@/utils/templateModules'

const props = defineProps<{
  preview: any | null
  selectedTemplate: any | null
  selectedAthletes: any[]
  scheduleSummary: string
  scheduleHint: string
  selectedTeamNames: string[]
  selectedWithExistingPlans: number
  selectedUnassignedCount: number
  notes: string
  canSubmit: boolean
  submitting: boolean
  validationMessage: string
}>()

const emit = defineEmits<{
  submit: []
}>()

const detailsExpanded = ref(false)
const displayTemplate = computed(() => props.preview?.template ?? props.selectedTemplate ?? null)
const hasGeneratedPreview = computed(() => Boolean(props.preview))

const athleteSummaries = computed(() =>
  hasGeneratedPreview.value
    ? (props.preview?.rows ?? []).map((row: any) => ({
        id: row.athlete.id,
        fullName: row.athlete.full_name,
        teamName: row.athlete.team?.name || '未分队',
      }))
    : (props.selectedAthletes ?? []).map((athlete: any) => ({
        id: athlete.id,
        fullName: athlete.full_name,
        teamName: athlete.team?.name || '未分队',
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
        detailText: buildLoadDetailText(item, previewItem),
      }
    }),
  }))
})

const missingBasisGroups = computed(() =>
  (props.preview?.rows ?? [])
    .map((row: any) => {
      const missingItems = (row.items ?? []).filter((item: any) => item.status === 'manual_control')
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
const visibleItemCount = computed(() => displayModules.value.reduce((sum, module) => sum + (module.items?.length || 0), 0))

function buildLoadRuleLabel(templateItem: any, previewItem?: any) {
  if (templateItem.initial_load_mode === 'fixed_weight') {
    return '固定重量'
  }
  if (templateItem.initial_load_mode === 'percent_1rm') {
    return previewItem?.status === 'manual_control' ? '训练时控制' : previewItem?.load_mode_label || '按最近测试百分比'
  }
  return previewItem?.load_mode_label || '训练时设置'
}

function buildLoadDetailText(templateItem: any, previewItem?: any) {
  if (previewItem?.status === 'manual_control') {
    return '控制'
  }
  const value = templateItem.initial_load_value
  if (templateItem.initial_load_mode === 'fixed_weight') {
    return value === null || value === undefined ? '固定重量未设置' : `${formatNumber(value)} 千克`
  }
  if (templateItem.initial_load_mode === 'percent_1rm') {
    if (value === null || value === undefined) {
      return '按最近测试结果计算'
    }
    return previewItem?.basis_label
      ? `${formatNumber(value)}% · ${previewItem.basis_label}`
      : `按最近测试的 ${formatNumber(value)}%`
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
        <p class="eyebrow">分配摘要</p>
        <h3>右侧随时确认本次分配</h3>
      </div>
    </div>

    <div class="preview-body">
      <article v-if="hasGeneratedPreview && missingBasisGroups.length" class="preview-card warning-panel">
        <div class="card-head">
          <div>
            <p class="eyebrow">训练时需现场控制</p>
            <h4>{{ missingBasisCount }} 名队员缺少对应测试结果</h4>
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

      <article class="preview-card">
        <div class="card-head">
          <div>
            <p class="eyebrow">当前摘要</p>
            <h4>{{ athleteSummaries.length }} 人待确认</h4>
          </div>
        </div>

        <div class="summary-list">
          <div class="summary-row">
            <span>训练模板</span>
            <strong>{{ displayTemplate?.name || '未选择模板' }}</strong>
          </div>
          <div class="summary-row">
            <span>日期配置</span>
            <strong>{{ scheduleSummary || '待设置' }}</strong>
          </div>
          <div v-if="scheduleHint" class="summary-row">
            <span>执行说明</span>
            <strong>{{ scheduleHint }}</strong>
          </div>
          <div class="summary-row">
            <span>涉及队伍</span>
            <strong>{{ selectedTeamNames.length ? selectedTeamNames.join('、') : '待选择队员' }}</strong>
          </div>
          <div class="summary-row">
            <span>已有后续计划</span>
            <strong>{{ selectedWithExistingPlans }} 人</strong>
          </div>
          <div class="summary-row">
            <span>当前未分配</span>
            <strong>{{ selectedUnassignedCount }} 人</strong>
          </div>
          <div v-if="notes" class="summary-row summary-row--stack">
            <span>分配备注</span>
            <strong>{{ notes }}</strong>
          </div>
        </div>
      </article>

      <article class="preview-card">
        <div class="card-head">
          <div>
            <p class="eyebrow">分配对象</p>
            <h4>已选 {{ athleteSummaries.length }} 人</h4>
          </div>
        </div>

        <div v-if="athleteSummaries.length" class="athlete-list">
          <div v-for="athlete in athleteSummaries.slice(0, 8)" :key="athlete.id" class="athlete-chip">
            <strong>{{ athlete.fullName }}</strong>
            <span>{{ athlete.teamName }}</span>
          </div>
        </div>
        <div v-else class="helper-panel">
          <p class="muted">先在左侧选择队员，右侧会同步更新分配摘要。</p>
        </div>
      </article>

      <article class="preview-card">
        <div class="card-head">
          <div>
            <p class="eyebrow">模板内容</p>
            <h4>{{ displayTemplate ? `${visibleItemCount} 个动作` : '请先选择模板' }}</h4>
          </div>
          <button v-if="displayTemplate" class="ghost-btn slim" type="button" @click="detailsExpanded = !detailsExpanded">
            {{ detailsExpanded ? '收起模板内容' : '查看模板内容' }}
          </button>
        </div>

        <div v-if="!displayTemplate" class="helper-panel">
          <p class="muted">模板选中后，这里显示模块与动作摘要；默认折叠，避免遮挡主流程。</p>
        </div>

        <div v-else-if="detailsExpanded" class="module-grid">
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

      <article class="preview-card action-panel">
        <button class="primary-btn action-btn" type="button" :disabled="!canSubmit || submitting" @click="emit('submit')">
          {{ submitting ? '正在提交...' : '确认分配计划' }}
        </button>
        <p v-if="validationMessage" class="muted">{{ validationMessage }}</p>
        <p v-else class="muted">确认前请核对模板、对象人数和日期摘要。右侧按钮会始终保留在可视区域附近。</p>
      </article>
    </div>
  </section>
</template>

<style scoped>
.preview-panel,
.preview-body,
.preview-card,
.summary-list,
.module-grid,
.module-block,
.item-grid,
.athlete-list,
.warning-list {
  display: grid;
  gap: 14px;
}

.preview-panel {
  position: sticky;
  top: 18px;
  align-content: start;
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
.athlete-chip span,
.item-row p,
.warning-row span,
.warning-row small,
.muted,
.summary-row span {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
}

.preview-card {
  padding: 16px;
  border-radius: 18px;
  background: var(--panel-soft);
}

.summary-list {
  gap: 10px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: baseline;
}

.summary-row strong {
  text-align: right;
}

.summary-row--stack {
  display: grid;
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

.item-row,
.warning-row {
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: center;
}

.item-side {
  display: grid;
  gap: 4px;
  text-align: right;
}

.warning-panel {
  border: 1px solid rgba(220, 38, 38, 0.16);
  background: rgba(254, 242, 242, 0.86);
}

.warning-list {
  gap: 10px;
}

.warning-row {
  background: rgba(255, 255, 255, 0.78);
}

.helper-panel {
  padding: 14px;
  border-radius: 14px;
  border: 1px solid rgba(15, 118, 110, 0.12);
  background: rgba(240, 253, 250, 0.8);
}

.action-panel {
  gap: 12px;
}

.action-btn {
  width: 100%;
}

@media (max-width: 1280px) {
  .preview-panel {
    position: static;
  }
}

@media (max-width: 900px) {
  .summary-row,
  .item-row,
  .warning-row {
    display: grid;
  }

  .summary-row strong,
  .item-side {
    text-align: left;
  }
}
</style>
