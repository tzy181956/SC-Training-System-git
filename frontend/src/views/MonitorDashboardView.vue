<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchMonitoringToday } from '@/api/monitoring'
import MonitorShell from '@/components/layout/MonitorShell.vue'
import MonitoringAlertPanel from '@/components/monitoring/MonitoringAlertPanel.vue'
import MonitoringAthleteBoard from '@/components/monitoring/MonitoringAthleteBoard.vue'
import MonitoringSummaryCards from '@/components/monitoring/MonitoringSummaryCards.vue'
import TrainingHeaderFilters from '@/components/training/TrainingHeaderFilters.vue'
import { ALL_TEAMS_VALUE, UNASSIGNED_TEAM_VALUE } from '@/composables/useTeamFilter'
import type { MonitoringAthleteCard, MonitoringTodayResponse } from '@/types/monitoring'
import { todayString } from '@/utils/date'
import { sortMonitoringAthletes } from '@/utils/monitoringSort'

const router = useRouter()
const monitorDate = ref(todayString())
const selectedTeamFilter = ref(ALL_TEAMS_VALUE)
const monitoringData = ref<MonitoringTodayResponse | null>(null)
const loading = ref(false)
const loadError = ref('')
const monitorNotice = ref('')
const lastRefreshAt = ref<string | null>(null)
const autoRefreshEnabled = ref(false)
const refreshIntervalMs = ref(30000)
const backgroundRefreshing = ref(false)
const pageVisible = ref(true)

let refreshTimerId: number | null = null
let activeRequestId = 0

type LoadMonitoringOptions = {
  background?: boolean
}

const monitorTeamOptions = computed(() => (
  [
    { id: ALL_TEAMS_VALUE, name: '全部队伍' },
    ...(monitoringData.value?.teams || []).map((team) => ({
      id: team.team_id == null ? UNASSIGNED_TEAM_VALUE : String(team.team_id),
      name: team.team_name,
    })),
  ]
))

const monitorTeamLabel = computed(() => (
  monitorTeamOptions.value.find((team) => team.id === selectedTeamFilter.value)?.name || '全部队伍'
))
const monitorDateLabel = computed(() => formatMonitorDate(monitorDate.value))
const displayedAthletes = computed<MonitoringAthleteCard[]>(() => {
  const athletes = monitoringData.value?.athletes || []
  if (selectedTeamFilter.value === UNASSIGNED_TEAM_VALUE) {
    return athletes.filter((athlete) => !athlete.team_id)
  }
  return athletes
})
const sortedAthletes = computed(() => sortMonitoringAthletes(displayedAthletes.value))
const refreshHint = computed(() => {
  if (loading.value) return '正在刷新监控数据'
  if (loadError.value) return loadError.value
  if (monitorNotice.value) return monitorNotice.value
  if (!lastRefreshAt.value) return '尚未完成刷新'
  return `${lastRefreshAt.value} 刷新`
})
const refreshModeLabel = computed(() =>
  autoRefreshEnabled.value
    ? pageVisible.value
      ? `自动刷新 ${Math.round(refreshIntervalMs.value / 1000)} 秒`
      : '自动刷新已暂停'
    : '手动刷新',
)

async function handleDateInput(value: string) {
  monitorDate.value = value
  await loadMonitoringData()
  restartAutoRefreshTimer()
}

async function handleTeamFilterInput(value: string) {
  selectedTeamFilter.value = value
  await loadMonitoringData()
  restartAutoRefreshTimer()
}

async function handleManualRefresh() {
  await loadMonitoringData()
  restartAutoRefreshTimer()
}

async function loadMonitoringData(options: LoadMonitoringOptions = {}) {
  const isBackground = options.background === true
  if (isBackground && (loading.value || backgroundRefreshing.value)) return

  const requestId = activeRequestId + 1
  activeRequestId = requestId
  if (isBackground) {
    backgroundRefreshing.value = true
  } else {
    loading.value = true
    monitorNotice.value = ''
  }

  try {
    const nextData = await fetchMonitoringToday({
      session_date: monitorDate.value,
      team_id: resolveSelectedTeamId(),
      include_unassigned: selectedTeamFilter.value !== ALL_TEAMS_VALUE ? selectedTeamFilter.value === UNASSIGNED_TEAM_VALUE : true,
    })
    if (requestId !== activeRequestId) return

    monitoringData.value = nextData
    loadError.value = ''
    lastRefreshAt.value = new Date().toLocaleTimeString('zh-CN', { hour12: false })
  } catch {
    if (requestId === activeRequestId) {
      loadError.value = '最近刷新失败，数据可能不是最新。'
    }
  } finally {
    if (isBackground) {
      backgroundRefreshing.value = false
    } else {
      loading.value = false
    }
  }
}

function toggleAutoRefresh() {
  autoRefreshEnabled.value = !autoRefreshEnabled.value
  restartAutoRefreshTimer()
}

function restartAutoRefreshTimer() {
  stopAutoRefreshTimer()
  if (!autoRefreshEnabled.value || !pageVisible.value) return

  refreshTimerId = window.setInterval(() => {
    void loadMonitoringData({ background: true })
  }, refreshIntervalMs.value)
}

function stopAutoRefreshTimer() {
  if (refreshTimerId === null) return
  window.clearInterval(refreshTimerId)
  refreshTimerId = null
}

function handleVisibilityChange() {
  pageVisible.value = !document.hidden
  if (!pageVisible.value) {
    stopAutoRefreshTimer()
    return
  }

  restartAutoRefreshTimer()
  if (autoRefreshEnabled.value) {
    void loadMonitoringData({ background: true })
  }
}

function handleAthleteClick(athlete: MonitoringAthleteCard) {
  monitorNotice.value = ''

  if (athlete.session_id && athlete.session_status === 'in_progress') {
    router.push({ name: 'training-session', params: { sessionId: athlete.session_id } })
    return
  }

  if (['completed', 'partial_complete', 'absent'].includes(athlete.session_status)) {
    router.push({
      name: 'training-reports',
      query: {
        athleteId: String(athlete.athlete_id),
        dateFrom: monitorDate.value,
        dateTo: monitorDate.value,
      },
    })
    return
  }

  if (athlete.session_status === 'not_started') {
    router.push({
      name: 'training-mode',
      query: {
        sessionDate: monitorDate.value,
      },
    })
    return
  }

  monitorNotice.value = `${athlete.athlete_name} 当天没有有效训练计划。`
}

function resolveSelectedTeamId() {
  if (selectedTeamFilter.value === ALL_TEAMS_VALUE || selectedTeamFilter.value === UNASSIGNED_TEAM_VALUE) {
    return null
  }
  const teamId = Number(selectedTeamFilter.value)
  return Number.isNaN(teamId) ? null : teamId
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

onMounted(() => {
  pageVisible.value = !document.hidden
  document.addEventListener('visibilitychange', handleVisibilityChange)
  void loadMonitoringData()
})

onBeforeUnmount(() => {
  stopAutoRefreshTimer()
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
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
      <button class="secondary-btn refresh-btn" type="button" @click="toggleAutoRefresh">
        {{ autoRefreshEnabled ? '关闭自动刷新' : '开启自动刷新' }}
      </button>
      <button class="secondary-btn refresh-btn" type="button" :disabled="loading" @click="handleManualRefresh">
        {{ loading ? '刷新中...' : '刷新' }}
      </button>
    </template>

    <div class="monitor-dashboard">
      <section class="panel overview-panel">
        <div class="overview-copy">
          <p class="section-label">监控端</p>
          <h3>今日训练状态看板</h3>
          <p>{{ refreshHint }}</p>
        </div>
        <div class="overview-meta">
          <span class="meta-pill">日期：{{ monitorDateLabel }}</span>
          <span class="meta-pill">队伍：{{ monitorTeamLabel }}</span>
          <span class="meta-pill">{{ refreshModeLabel }}</span>
        </div>
      </section>

      <MonitoringSummaryCards :athletes="sortedAthletes" :loading="loading" />

      <section class="dashboard-grid">
        <MonitoringAthleteBoard
          class="board-main"
          :athletes="sortedAthletes"
          :loading="loading"
          @select-athlete="handleAthleteClick"
        />
        <MonitoringAlertPanel class="board-side" :athletes="sortedAthletes" :loading="loading" />
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

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 16px;
}

.board-main,
.board-side {
  min-width: 0;
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

  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 1180px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
