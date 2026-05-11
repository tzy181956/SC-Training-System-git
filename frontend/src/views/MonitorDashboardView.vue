<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { fetchMonitoringAthleteDetail, fetchMonitoringToday } from '@/api/monitoring'
import MonitorShell from '@/components/layout/MonitorShell.vue'
import MonitoringAlertPanel from '@/components/monitoring/MonitoringAlertPanel.vue'
import MonitoringAthleteBoard from '@/components/monitoring/MonitoringAthleteBoard.vue'
import MonitoringAthleteDetailOverlay from '@/components/monitoring/MonitoringAthleteDetailOverlay.vue'
import MonitoringSummaryCards from '@/components/monitoring/MonitoringSummaryCards.vue'
import TrainingHeaderFilters from '@/components/training/TrainingHeaderFilters.vue'
import { ALL_TEAMS_VALUE, UNASSIGNED_TEAM_VALUE } from '@/composables/useTeamFilter'
import type { MonitoringAthleteCard, MonitoringAthleteDetailResponse, MonitoringTodayResponse } from '@/types/monitoring'
import { todayString } from '@/utils/date'
import { buildMonitoringAlertKey, buildMonitoringAlertStorageKey } from '@/utils/monitoringAlerts'
import { sortMonitoringAthletes } from '@/utils/monitoringSort'

const AUTO_REFRESH_OPTIONS = [
  { label: '5 秒', value: 5000 },
  { label: '10 秒', value: 10000 },
  { label: '30 秒', value: 30000 },
] as const

const router = useRouter()
const monitorDate = ref(todayString())
const selectedTeamFilter = ref(ALL_TEAMS_VALUE)
const monitoringData = ref<MonitoringTodayResponse | null>(null)
const loading = ref(false)
const loadError = ref('')
const monitorNotice = ref('')
const lastRefreshAt = ref<string | null>(null)
const autoRefreshEnabled = ref(true)
const refreshIntervalMs = ref(5000)
const backgroundRefreshing = ref(false)
const pageVisible = ref(true)
const selectedAthleteId = ref<number | null>(null)
const selectedAthleteDetail = ref<MonitoringAthleteDetailResponse | null>(null)
const detailLoading = ref(false)
const detailError = ref('')
const dismissedAlertKeys = ref<string[]>([])
const deletedAlertKeys = ref<string[]>([])

let refreshTimerId: number | null = null
let activeRequestId = 0
let activeDetailRequestId = 0

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
const hiddenAlertKeys = computed(() => Array.from(new Set([...dismissedAlertKeys.value, ...deletedAlertKeys.value])))
const presentationAthletes = computed<MonitoringAthleteCard[]>(() => {
  const hiddenKeySet = new Set(hiddenAlertKeys.value)
  return displayedAthletes.value.map((athlete) => {
    if (!hiddenKeySet.has(buildMonitoringAlertKey(monitorDate.value, athlete))) return athlete
    return {
      ...athlete,
      alert_level: 'none',
      has_alert: false,
    }
  })
})
const sortedAthletes = computed(() => sortMonitoringAthletes(presentationAthletes.value))
const selectedAthlete = computed(() => {
  if (!selectedAthleteId.value) return null
  return sortedAthletes.value.find((athlete) => athlete.athlete_id === selectedAthleteId.value) || null
})
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
  if (selectedAthleteId.value) {
    await loadAthleteDetail(selectedAthleteId.value)
  }
  restartAutoRefreshTimer()
}

async function handleTeamFilterInput(value: string) {
  selectedTeamFilter.value = value
  await loadMonitoringData()
  if (selectedAthleteId.value) {
    await loadAthleteDetail(selectedAthleteId.value)
  }
  restartAutoRefreshTimer()
}

async function handleManualRefresh() {
  await loadMonitoringData()
  if (selectedAthleteId.value) {
    await loadAthleteDetail(selectedAthleteId.value)
  }
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

function setRefreshInterval(value: number) {
  if (refreshIntervalMs.value === value) return
  refreshIntervalMs.value = value
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
  selectedAthleteId.value = athlete.athlete_id
  void loadAthleteDetail(athlete.athlete_id)
}

function closeAthleteDetail() {
  activeDetailRequestId += 1
  selectedAthleteId.value = null
  selectedAthleteDetail.value = null
  detailLoading.value = false
  detailError.value = ''
}

async function loadAthleteDetail(athleteId: number) {
  const requestId = activeDetailRequestId + 1
  activeDetailRequestId = requestId
  selectedAthleteDetail.value = null
  detailError.value = ''
  detailLoading.value = true

  try {
    const detail = await fetchMonitoringAthleteDetail({
      session_date: monitorDate.value,
      athlete_id: athleteId,
    })
    if (requestId !== activeDetailRequestId || selectedAthleteId.value !== athleteId) return
    selectedAthleteDetail.value = detail
  } catch {
    if (requestId === activeDetailRequestId && selectedAthleteId.value === athleteId) {
      detailError.value = '训练明细加载失败，请稍后重试。'
    }
  } finally {
    if (requestId === activeDetailRequestId) {
      detailLoading.value = false
    }
  }
}

function retryLoadAthleteDetail() {
  if (!selectedAthleteId.value) return
  void loadAthleteDetail(selectedAthleteId.value)
}

function openTrainingSessionFromDetail() {
  const sessionId = resolveDetailSessionId()
  if (!sessionId) return
  router.push({
    name: 'training-session',
    params: { sessionId },
  })
}

function openTrainingReportFromDetail() {
  if (!selectedAthlete.value) return

  router.push({
    name: 'training-reports',
    query: {
      athleteId: String(selectedAthlete.value.athlete_id),
      dateFrom: monitorDate.value,
      dateTo: monitorDate.value,
    },
  })
}

function resolveDetailSessionId() {
  if (selectedAthleteDetail.value) {
    const preferredAssignment = selectedAthleteDetail.value.assignments.find(
      (assignment) => assignment.session_id && !['completed', 'absent'].includes(assignment.session_status),
    )
    if (preferredAssignment?.session_id) return preferredAssignment.session_id

    const firstAssignmentWithSession = selectedAthleteDetail.value.assignments.find((assignment) => assignment.session_id)
    if (firstAssignmentWithSession?.session_id) return firstAssignmentWithSession.session_id
  }
  return selectedAthlete.value?.session_id || null
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

function loadStoredAlertKeys(bucket: 'dismissed' | 'deleted', sessionDate: string) {
  if (typeof window === 'undefined') return []
  try {
    const raw = window.localStorage.getItem(buildMonitoringAlertStorageKey(sessionDate, bucket))
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed.filter((item): item is string => typeof item === 'string') : []
  } catch {
    return []
  }
}

function persistStoredAlertKeys(bucket: 'dismissed' | 'deleted', sessionDate: string, keys: string[]) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(buildMonitoringAlertStorageKey(sessionDate, bucket), JSON.stringify(keys))
}

function dismissAlert(key: string) {
  if (dismissedAlertKeys.value.includes(key)) return
  dismissedAlertKeys.value = [...dismissedAlertKeys.value, key]
  deletedAlertKeys.value = deletedAlertKeys.value.filter((item) => item !== key)
}

function restoreAlert(key: string) {
  dismissedAlertKeys.value = dismissedAlertKeys.value.filter((item) => item !== key)
  deletedAlertKeys.value = deletedAlertKeys.value.filter((item) => item !== key)
}

function deleteAlert(key: string) {
  if (deletedAlertKeys.value.includes(key)) return
  deletedAlertKeys.value = [...deletedAlertKeys.value, key]
  dismissedAlertKeys.value = dismissedAlertKeys.value.filter((item) => item !== key)
}

watch(sortedAthletes, (athletes) => {
  if (!selectedAthleteId.value) return
  if (!athletes.some((athlete) => athlete.athlete_id === selectedAthleteId.value)) {
    closeAthleteDetail()
  }
})

watch(
  monitorDate,
  (sessionDate) => {
    dismissedAlertKeys.value = loadStoredAlertKeys('dismissed', sessionDate)
    deletedAlertKeys.value = loadStoredAlertKeys('deleted', sessionDate)
  },
  { immediate: true },
)

watch(
  dismissedAlertKeys,
  (keys) => {
    persistStoredAlertKeys('dismissed', monitorDate.value, keys)
  },
  { deep: true },
)

watch(
  deletedAlertKeys,
  (keys) => {
    persistStoredAlertKeys('deleted', monitorDate.value, keys)
  },
  { deep: true },
)

onMounted(() => {
  pageVisible.value = !document.hidden
  document.addEventListener('visibilitychange', handleVisibilityChange)
  restartAutoRefreshTimer()
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
      <div class="refresh-interval-group" role="group" aria-label="自动刷新频率">
        <button
          v-for="option in AUTO_REFRESH_OPTIONS"
          :key="option.value"
          class="secondary-btn refresh-interval-btn"
          :class="{ active: refreshIntervalMs === option.value }"
          type="button"
          @click="setRefreshInterval(option.value)"
        >
          {{ option.label }}
        </button>
      </div>
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
          <p class="section-label">实时模式</p>
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
          :session-date="monitorDate"
          :dismissed-alert-keys="hiddenAlertKeys"
          :loading="loading"
          @select-athlete="handleAthleteClick"
        />
        <MonitoringAlertPanel
          class="board-side"
          :athletes="displayedAthletes"
          :session-date="monitorDate"
          :dismissed-alert-keys="dismissedAlertKeys"
          :deleted-alert-keys="deletedAlertKeys"
          :loading="loading"
          @dismiss-alert="dismissAlert"
          @restore-alert="restoreAlert"
          @delete-alert="deleteAlert"
        />
      </section>

      <MonitoringAthleteDetailOverlay
        :athlete="selectedAthlete"
        :detail="selectedAthleteDetail"
        :loading="detailLoading"
        :error="detailError"
        :session-date="monitorDateLabel"
        :visible="selectedAthlete !== null"
        @close="closeAthleteDetail"
        @open-report="openTrainingReportFromDetail"
        @open-session="openTrainingSessionFromDetail"
        @retry-load="retryLoadAthleteDetail"
      />
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
  align-items: start;
}

.board-main,
.board-side {
  min-width: 0;
}

.refresh-btn {
  min-height: 38px;
}

.refresh-interval-group {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 8px;
}

.refresh-interval-btn {
  min-height: 38px;
  min-width: 64px;
}

.refresh-interval-btn.active {
  border-color: #0f766e;
  background: rgba(15, 118, 110, 0.12);
  color: #0f766e;
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
