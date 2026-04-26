<script setup lang="ts">
import { computed, ref } from 'vue'

import MonitorShell from '@/components/layout/MonitorShell.vue'
import TrainingHeaderFilters from '@/components/training/TrainingHeaderFilters.vue'
import { ALL_TEAMS_VALUE, useTeamFilter } from '@/composables/useTeamFilter'
import type { MonitoringBoardSection } from '@/types/monitoring'
import { todayString } from '@/utils/date'

const monitorDate = ref(todayString())
const lastRefreshAt = ref<string | null>(null)
const monitorAthletes = ref<any[]>([])

const {
  selectedTeamFilter,
  teamOptions,
  selectedTeamLabel,
} = useTeamFilter({
  athletes: () => monitorAthletes.value,
})

const monitorTeamOptions = computed(() => (
  teamOptions.value.length
    ? teamOptions.value
    : [{ id: ALL_TEAMS_VALUE, name: '全部队伍' }]
))

const monitorTeamLabel = computed(() => (teamOptions.value.length ? selectedTeamLabel.value : '全部队伍'))
const monitorDateLabel = computed(() => formatMonitorDate(monitorDate.value))
const refreshHint = computed(() => (lastRefreshAt.value ? `占位刷新时间：${lastRefreshAt.value}` : '等待接入轮询与监控接口'))

const boardSections: MonitoringBoardSection[] = [
  {
    id: 'team-summary',
    title: '队伍汇总区预留',
    description: '后续放当天各队伍的未开始、进行中、已完成、未完全完成、缺席与同步异常数量。',
  },
  {
    id: 'athlete-board',
    title: '运动员状态看板预留',
    description: '后续放运动员卡片列表，显示当前动作、完成动作数、完成组数和最近一组数据。',
  },
  {
    id: 'sync-alerts',
    title: '同步异常区预留',
    description: '后续放待人工处理的同步异常、冲突提示和跳转入口。',
  },
]

function handleDateInput(value: string) {
  monitorDate.value = value
}

function handleTeamFilterInput(value: string) {
  selectedTeamFilter.value = value
}

function refreshPlaceholder() {
  lastRefreshAt.value = new Date().toLocaleString('zh-CN', { hour12: false })
}

function formatMonitorDate(value: string) {
  if (!value) return '监控日期'

  const parts = value.split('-')
  if (parts.length !== 3) return value

  const [year, month, day] = parts
  const monthNumber = Number(month)
  const dayNumber = Number(day)
  if (!year || Number.isNaN(monthNumber) || Number.isNaN(dayNumber)) return value

  return `${year}年${monthNumber}月${dayNumber}日`
}
</script>

<template>
  <MonitorShell>
    <template #header-filters>
      <TrainingHeaderFilters
        :session-date="monitorDate"
        :session-date-label="monitorDateLabel"
        :selected-team-value="selectedTeamFilter"
        :selected-team-label="monitorTeamLabel"
        :team-options="monitorTeamOptions"
        team-field-label="监控队伍"
        team-aria-label="监控队伍筛选"
        @update:session-date="handleDateInput"
        @update:team-value="handleTeamFilterInput"
      />
    </template>

    <template #header-actions>
      <button class="secondary-btn refresh-btn" type="button" @click="refreshPlaceholder">刷新占位</button>
    </template>

    <div class="monitor-dashboard">
      <section class="panel overview-panel">
        <div class="overview-copy">
          <p class="section-label">监控端</p>
          <h3>监控看板区域占位</h3>
          <p>{{ refreshHint }}</p>
        </div>
        <div class="overview-meta">
          <span class="meta-pill">日期：{{ monitorDateLabel }}</span>
          <span class="meta-pill">队伍：{{ monitorTeamLabel }}</span>
        </div>
      </section>

      <section class="board-grid">
        <article v-for="section in boardSections" :key="section.id" class="panel board-card">
          <p class="section-label">{{ section.title }}</p>
          <strong>{{ section.description }}</strong>
        </article>
      </section>
    </div>
  </MonitorShell>
</template>

<style scoped>
.monitor-dashboard {
  display: grid;
  gap: 16px;
  align-content: start;
}

.overview-panel {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
}

.overview-copy,
.overview-meta {
  display: grid;
  gap: 8px;
}

.overview-copy h3,
.overview-copy p,
.section-label {
  margin: 0;
}

.section-label {
  color: var(--text-soft);
}

.overview-meta {
  justify-items: flex-end;
}

.meta-pill {
  display: inline-flex;
  align-items: center;
  min-height: 36px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(14, 116, 144, 0.08);
  color: #155e75;
  font-weight: 700;
}

.board-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.board-card {
  display: grid;
  gap: 10px;
  min-height: 180px;
  align-content: start;
  padding: 18px;
  border: 1px dashed rgba(14, 116, 144, 0.24);
  background: rgba(255, 255, 255, 0.72);
}

.refresh-btn {
  min-height: 38px;
}

@media (max-width: 960px) {
  .overview-panel {
    flex-direction: column;
  }

  .overview-meta {
    justify-items: flex-start;
  }

  .board-grid {
    grid-template-columns: 1fr;
  }
}
</style>
