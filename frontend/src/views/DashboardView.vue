<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter, type RouteLocationRaw } from 'vue-router'

import { fetchAthletes, fetchSports, type AthleteRead, type SportRead } from '@/api/athletes'
import { fetchMonitoringToday } from '@/api/monitoring'
import {
  fetchTrainingSyncIssues,
  retryTrainingSyncIssue,
  type TrainingSyncIssue,
} from '@/api/sessions'
import { fetchDashboardMemo, fetchServerTime, updateDashboardMemo } from '@/api/system'
import AppShell from '@/components/layout/AppShell.vue'
import { ALL_SPORTS_VALUE, ALL_TEAMS_VALUE } from '@/composables/useTeamFilter'
import { getTrainingSyncIssueLabel, isTrainingSyncConflictSummary } from '@/constants/trainingSync'
import { useAuthStore } from '@/stores/auth'
import type { MonitoringAthleteCard, MonitoringTeamOption, MonitoringTodayResponse } from '@/types/monitoring'
import { todayString } from '@/utils/date'
import { isSportScoped, resolveScopedSportId } from '@/utils/projectTeamScope'

type DashboardCardTone = 'neutral' | 'progress' | 'success' | 'warning' | 'danger'

type DashboardSummaryMetric = {
  key: string
  label: string
  value: number
  hint: string
  tone: DashboardCardTone
}

type DashboardTaskAction = 'focus-sync' | 'monitor' | 'assignments' | 'reports'

type DashboardTaskItem = {
  key: string
  label: string
  count: number
  description: string
  tone: DashboardCardTone
  actionLabel: string
  action: DashboardTaskAction
}

type DashboardQuickAction = {
  key: string
  label: string
  description: string
  route: RouteLocationRaw
  tone: 'primary' | 'secondary'
}

const router = useRouter()
const authStore = useAuthStore()

const dashboardDate = todayString()
const sports = ref<SportRead[]>([])
const selectedSportFilter = ref(ALL_SPORTS_VALUE)
const selectedTeamFilter = ref(ALL_TEAMS_VALUE)
const monitoringData = ref<MonitoringTodayResponse | null>(null)
const visibleTeams = ref<MonitoringTeamOption[]>([])
const athleteDirectory = ref<AthleteRead[]>([])
const syncIssues = ref<TrainingSyncIssue[]>([])
const monitoringError = ref('')
const syncError = ref('')
const syncNotice = ref('')
const syncNoticeTone = ref<'success' | 'warning' | 'error'>('success')
const loading = ref(false)
const retryingIssueId = ref<number | null>(null)
const lastRefreshAt = ref<string | null>(null)
const syncPanelRef = ref<HTMLElement | null>(null)
const serverTimeBaseMs = ref<number | null>(null)
const serverTimeFetchedAtMs = ref<number | null>(null)
const serverTimeOffsetMinutes = ref(0)
const serverTimeZone = ref('')
const displayedServerTimeMs = ref<number | null>(null)
const serverTimeError = ref('')
const coachMemo = ref('')
const coachMemoSavedAt = ref('')
const coachMemoError = ref('')
const coachMemoSaving = ref(false)
const scopedSportId = computed(() => resolveScopedSportId(authStore.currentUser?.sport_id))
const isSportFilterLocked = computed(() => isSportScoped(authStore.currentUser?.sport_id))
let serverTimeTimerId: number | null = null
let coachMemoSaveTimerId: number | null = null
let coachMemoSaveRequestId = 0

const dashboardDateLabel = formatDashboardDate(dashboardDate)
const sportOptions = computed(() => {
  if (isSportFilterLocked.value) {
    const matched = sports.value.find((sport) => sport.id === scopedSportId.value)
    return [{ id: String(scopedSportId.value), name: matched?.name || '当前项目' }]
  }

  return [
    { id: ALL_SPORTS_VALUE, name: '全部项目' },
    ...sports.value.map((sport) => ({
      id: String(sport.id),
      name: sport.name,
    })),
  ]
})

const selectedSportId = computed<number | null>(() => {
  if (selectedSportFilter.value === ALL_SPORTS_VALUE) return null
  const parsed = Number(selectedSportFilter.value)
  return Number.isNaN(parsed) ? null : parsed
})

const selectedSportLabel = computed(() => {
  const matched = sportOptions.value.find((sport) => sport.id === selectedSportFilter.value)
  return matched?.name || '全部项目'
})

const teamOptions = computed(() => {
  if (selectedSportId.value === null) {
    return [{ id: ALL_TEAMS_VALUE, name: '全部队伍' }]
  }

  const namedTeams = visibleTeams.value.filter((team) => team.team_id !== null)
  const options = namedTeams.map((team) => ({
    id: String(team.team_id),
    name: team.team_name,
  }))

  return [{ id: ALL_TEAMS_VALUE, name: '全部队伍' }, ...options]
})

const showTeamFilter = computed(
  () => selectedSportId.value !== null,
)

const selectedTeamId = computed<number | null>(() => {
  if (selectedTeamFilter.value === ALL_TEAMS_VALUE) return null
  const parsed = Number(selectedTeamFilter.value)
  return Number.isNaN(parsed) ? null : parsed
})

const selectedTeamLabel = computed(() => {
  const matched = teamOptions.value.find((team) => team.id === selectedTeamFilter.value)
  if (matched) return matched.name
  return '全部队伍'
})

const refreshStatusLabel = computed(() => {
  if (loading.value) return '正在刷新'
  if (monitoringError.value) return '今日概况加载失败，可重新进入总览重试'
  if (!lastRefreshAt.value) return '尚未刷新'
  return `最近刷新 ${lastRefreshAt.value}`
})

const serverTimeLabel = computed(() => {
  if (serverTimeError.value) return serverTimeError.value
  if (displayedServerTimeMs.value === null) return '服务器时间：校准中'
  const timezoneLabel = serverTimeZone.value || formatUtcOffset(serverTimeOffsetMinutes.value)
  return `服务器时间：${formatServerDateTime(displayedServerTimeMs.value, serverTimeOffsetMinutes.value)} ${timezoneLabel}`
})

const coachMemoStatusLabel = computed(() => (
  coachMemoError.value
    ? coachMemoError.value
    : coachMemoSaving.value
      ? '保存中...'
      : coachMemoSavedAt.value
        ? `已保存 ${coachMemoSavedAt.value}`
        : '服务器自动保存'
))

const athletesById = computed(() => (
  new Map(athleteDirectory.value.map((athlete) => [athlete.id, athlete]))
))

const monitoringAthletes = computed<MonitoringAthleteCard[]>(() => monitoringData.value?.athletes || [])

const filteredSyncIssues = computed(() => {
  return syncIssues.value.filter((issue) => {
    const athlete = athletesById.value.get(issue.athlete_id)
    if (selectedSportId.value !== null && athlete?.sport_id !== selectedSportId.value) return false
    if (selectedTeamId.value !== null && athlete?.team_id !== selectedTeamId.value) return false
    return true
  })
})

const summaryMetrics = computed<DashboardSummaryMetric[]>(() => {
  const athletes = monitoringAthletes.value
  const alertCount = athletes.filter((athlete) => athlete.has_alert || athlete.sync_status !== 'synced').length

  return [
    {
      key: 'athletes',
      label: '当前范围队员',
      value: athletes.length,
      hint: '当前筛选范围内可见的训练对象',
      tone: 'neutral',
    },
    {
      key: 'in-progress',
      label: '进行中',
      value: countByStatus(athletes, 'in_progress'),
      hint: '正在训练，需要实时关注',
      tone: 'progress',
    },
    {
      key: 'completed',
      label: '已完成',
      value: countByStatus(athletes, 'completed'),
      hint: '今天已完成训练',
      tone: 'success',
    },
    {
      key: 'partial',
      label: '已结束未完成',
      value: countByStatus(athletes, 'partial_complete'),
      hint: '课后建议复核训练执行',
      tone: 'warning',
    },
    {
      key: 'alerts',
      label: '异常 / 待关注',
      value: alertCount,
      hint: '同步异常、冲突或训练告警',
      tone: 'danger',
    },
    {
      key: 'no-plan',
      label: '今日无计划',
      value: countByStatus(athletes, 'no_plan'),
      hint: '今天没有命中可执行计划',
      tone: 'neutral',
    },
  ]
})

const taskItems = computed<DashboardTaskItem[]>(() => {
  const athletes = monitoringAthletes.value
  const items: DashboardTaskItem[] = []
  const alertCount = athletes.filter((athlete) => athlete.has_alert || athlete.sync_status !== 'synced').length
  const noPlanCount = countByStatus(athletes, 'no_plan')
  const partialCount = countByStatus(athletes, 'partial_complete')

  if (filteredSyncIssues.value.length) {
    items.push({
      key: 'sync-issues',
      label: '同步异常待处理',
      count: filteredSyncIssues.value.length,
      description: '训练端自动重试未恢复，建议优先处理，避免课后数据长时间堆积。',
      tone: 'danger',
      actionLabel: '查看异常明细',
      action: 'focus-sync',
    })
  }

  if (alertCount) {
    items.push({
      key: 'monitor-alerts',
      label: '训练中异常需关注',
      count: alertCount,
      description: '当前有队员存在同步告警、训练冲突或需要教练留意的训练状态。',
      tone: 'warning',
      actionLabel: '去实时模式',
      action: 'monitor',
    })
  }

  if (noPlanCount) {
    items.push({
      key: 'no-plan',
      label: '今日无计划待分配',
      count: noPlanCount,
      description: '当前范围内仍有队员今天没有命中训练安排，建议先补齐计划。',
      tone: 'neutral',
      actionLabel: '去计划分配',
      action: 'assignments',
    })
  }

  if (partialCount) {
    items.push({
      key: 'partial-complete',
      label: '课后待确认 / 补看',
      count: partialCount,
      description: '有训练课已结束但未完全完成，建议回看训练记录并确认是否需要补录或备注。',
      tone: 'warning',
      actionLabel: '去训练数据',
      action: 'reports',
    })
  }

  return items
})

const calmState = computed(() => {
  if (monitoringError.value || loading.value) return null
  if (taskItems.value.length) return null

  if (!monitoringAthletes.value.length) {
    return {
      title: '当前范围今天没有训练安排',
      description: '没有命中今天的训练对象，可以先去计划分配准备今天或接下来的安排。',
      actionLabel: '去计划分配',
      action: 'assignments' as DashboardTaskAction,
    }
  }

  return {
    title: '今天运行正常',
    description: '当前没有同步异常、训练告警或待补分配任务，建议去实时模式继续看现场进度。',
    actionLabel: '去实时模式查看现场进度',
    action: 'monitor' as DashboardTaskAction,
  }
})

const quickActions = computed<DashboardQuickAction[]>(() => ([
  {
    key: 'assignments',
    label: '计划分配',
    description: '补计划、看未分配和调整今天后续安排。',
    route: { name: 'assignments' },
    tone: 'primary',
  },
  {
    key: 'reports',
    label: '训练数据',
    description: '回看训练执行、补录组记录和处理课后确认。',
    route: { name: 'training-reports', query: { dateFrom: dashboardDate, dateTo: dashboardDate } },
    tone: 'secondary',
  },
  {
    key: 'plans',
    label: '训练模板',
    description: '维护模板结构和动作顺序，准备后续分配。',
    route: { name: 'plans' },
    tone: 'secondary',
  },
  {
    key: 'monitor',
    label: '实时模式',
    description: '查看全队今天训练状态、异常和当前进度。',
    route: { name: 'monitor-dashboard' },
    tone: 'secondary',
  },
]))

const systemActions = computed<DashboardQuickAction[]>(() => {
  if (!authStore.isAdmin) return []
  return [
    {
      key: 'users',
      label: '账号管理',
      description: '维护管理账号、绑定队伍和启停用。',
      route: { name: 'users' },
      tone: 'secondary',
    },
    {
      key: 'backups',
      label: '备份恢复',
      description: '检查备份列表并在危险操作前确认恢复入口。',
      route: { name: 'backups' },
      tone: 'secondary',
    },
    {
      key: 'logs',
      label: '日志',
      description: '回看危险操作、模板修改和训练记录变更。',
      route: { name: 'logs' },
      tone: 'secondary',
    },
  ]
})

const syncPreviewIssues = computed(() => filteredSyncIssues.value.slice(0, 3))
const hasSyncOverflow = computed(() => filteredSyncIssues.value.length > syncPreviewIssues.value.length)

onMounted(async () => {
  if (isSportFilterLocked.value) {
    selectedSportFilter.value = String(scopedSportId.value)
  }
  startServerTimeTicker()
  await hydrateDashboard()
})

onBeforeUnmount(() => {
  stopServerTimeTicker()
  if (coachMemoSaveTimerId !== null) {
    void saveCoachMemoNow()
  }
})

async function hydrateDashboard() {
  loading.value = true
  await Promise.allSettled([
    loadSports(),
    loadMonitoringData({ refreshTeams: true }),
    loadSyncIssues(),
    loadAthleteDirectory(),
    loadServerTime(),
    loadCoachMemo(),
  ])
  loading.value = false
}

async function loadMonitoringData(options: { refreshTeams: boolean }) {
  monitoringError.value = ''
  try {
    const nextData = await fetchMonitoringToday({
      session_date: dashboardDate,
      sport_id: selectedSportId.value,
      team_id: selectedTeamId.value,
      include_unassigned: selectedTeamId.value === null,
    })
    monitoringData.value = nextData
    if (options.refreshTeams || !visibleTeams.value.length) {
      visibleTeams.value = nextData.teams || []
      syncSelectedTeamFilter()
    }
    lastRefreshAt.value = formatRefreshTime(new Date())
  } catch {
    monitoringError.value = '今日概况加载失败，可重新进入总览重试。'
  }
}

async function loadSports() {
  try {
    sports.value = await fetchSports()
  } catch {
    sports.value = []
  }
}

async function loadSyncIssues() {
  syncError.value = ''
  try {
    syncIssues.value = await fetchTrainingSyncIssues({ issue_status: 'manual_retry_required' })
  } catch {
    syncError.value = '同步异常列表加载失败，请稍后重试。'
    syncIssues.value = []
  }
}

async function loadAthleteDirectory() {
  try {
    athleteDirectory.value = await fetchAthletes()
  } catch {
    athleteDirectory.value = []
  }
}

async function handleTeamFilterChange() {
  loading.value = true
  await Promise.allSettled([
    loadMonitoringData({ refreshTeams: selectedTeamId.value === null }),
    loadServerTime(),
  ])
  loading.value = false
}

async function handleSportFilterChange() {
  if (isSportFilterLocked.value) {
    selectedSportFilter.value = String(scopedSportId.value)
  }
  selectedTeamFilter.value = ALL_TEAMS_VALUE
  loading.value = true
  await Promise.allSettled([
    loadMonitoringData({ refreshTeams: true }),
    loadServerTime(),
  ])
  loading.value = false
}

async function loadServerTime() {
  try {
    const result = await fetchServerTime()
    const parsedTime = new Date(result.server_time).getTime()
    if (Number.isNaN(parsedTime)) {
      throw new Error('Invalid server time')
    }
    serverTimeBaseMs.value = parsedTime
    serverTimeFetchedAtMs.value = Date.now()
    serverTimeOffsetMinutes.value = result.utc_offset_minutes
    serverTimeZone.value = result.timezone
    displayedServerTimeMs.value = parsedTime
    serverTimeError.value = ''
  } catch {
    serverTimeError.value = '服务器时间：获取失败'
  }
}

function startServerTimeTicker() {
  stopServerTimeTicker()
  serverTimeTimerId = window.setInterval(() => {
    if (serverTimeBaseMs.value === null || serverTimeFetchedAtMs.value === null) return
    displayedServerTimeMs.value = serverTimeBaseMs.value + (Date.now() - serverTimeFetchedAtMs.value)
  }, 1000)
}

function stopServerTimeTicker() {
  if (serverTimeTimerId === null) return
  window.clearInterval(serverTimeTimerId)
  serverTimeTimerId = null
}

function syncSelectedTeamFilter() {
  const options = teamOptions.value
  if (!options.length) {
    selectedTeamFilter.value = ALL_TEAMS_VALUE
    return
  }

  const currentStillVisible = options.some((option) => option.id === selectedTeamFilter.value)
  if (currentStillVisible) return

  selectedTeamFilter.value = ALL_TEAMS_VALUE
}

function handleTaskAction(action: DashboardTaskAction) {
  if (action === 'focus-sync') {
    syncPanelRef.value?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    return
  }

  if (action === 'monitor') {
    void router.push({ name: 'monitor-dashboard' })
    return
  }

  if (action === 'assignments') {
    void router.push({ name: 'assignments' })
    return
  }

  void router.push({
    name: 'training-reports',
    query: {
      dateFrom: dashboardDate,
      dateTo: dashboardDate,
    },
  })
}

function handleQuickAction(route: RouteLocationRaw) {
  void router.push(route)
}

function handleCoachMemoInput(event: Event) {
  coachMemo.value = (event.target as HTMLTextAreaElement).value
  scheduleCoachMemoSave()
}

async function loadCoachMemo() {
  coachMemoError.value = ''
  try {
    const result = await fetchDashboardMemo()
    coachMemo.value = result.content
    coachMemoSavedAt.value = result.updated_at ? formatStoredSaveTime(result.updated_at) : ''
  } catch {
    coachMemoError.value = '加载失败，请稍后重试'
  }
}

function scheduleCoachMemoSave() {
  coachMemoError.value = ''
  coachMemoSaving.value = true
  if (coachMemoSaveTimerId !== null) {
    window.clearTimeout(coachMemoSaveTimerId)
  }
  coachMemoSaveTimerId = window.setTimeout(() => {
    void saveCoachMemoNow()
  }, 500)
}

async function saveCoachMemoNow() {
  if (coachMemoSaveTimerId !== null) {
    window.clearTimeout(coachMemoSaveTimerId)
    coachMemoSaveTimerId = null
  }

  const requestId = coachMemoSaveRequestId + 1
  coachMemoSaveRequestId = requestId
  coachMemoSaving.value = true

  try {
    const result = await updateDashboardMemo(coachMemo.value)
    if (requestId !== coachMemoSaveRequestId) return
    coachMemoSavedAt.value = result.updated_at ? formatStoredSaveTime(result.updated_at) : formatRefreshTime(new Date())
    coachMemoError.value = ''
  } catch {
    if (requestId === coachMemoSaveRequestId) {
      coachMemoError.value = '保存失败，请检查服务器连接'
    }
  } finally {
    if (requestId === coachMemoSaveRequestId) {
      coachMemoSaving.value = false
    }
  }
}

async function retrySyncIssue(issueId: number) {
  retryingIssueId.value = issueId
  try {
    await retryTrainingSyncIssue(issueId)
    syncNotice.value = '同步异常已重试，首页数据已刷新。'
    syncNoticeTone.value = 'success'
    await Promise.allSettled([
      loadSyncIssues(),
      loadMonitoringData({ refreshTeams: selectedTeamId.value === null }),
    ])
  } catch {
    syncNotice.value = '手动重试失败，请回到训练端所在设备继续处理。'
    syncNoticeTone.value = 'warning'
  } finally {
    retryingIssueId.value = null
  }
}

function countByStatus(athletes: MonitoringAthleteCard[], status: string) {
  return athletes.filter((athlete) => athlete.session_status === status).length
}

function formatDashboardDate(value: string) {
  if (!value) return '今天'
  const [year, month, day] = value.split('-')
  if (!year || !month || !day) return value
  return `${year} 年 ${month} 月 ${day} 日`
}

function formatRefreshTime(value: Date) {
  return value.toLocaleTimeString('zh-CN', { hour12: false })
}

function formatStoredSaveTime(value: string) {
  const parsedTime = new Date(value)
  if (Number.isNaN(parsedTime.getTime())) return ''
  return formatRefreshTime(parsedTime)
}

function formatServerDateTime(timestampMs: number, utcOffsetMinutes: number) {
  const serverDate = new Date(timestampMs + utcOffsetMinutes * 60 * 1000)
  const year = serverDate.getUTCFullYear()
  const month = padDatePart(serverDate.getUTCMonth() + 1)
  const day = padDatePart(serverDate.getUTCDate())
  const hours = padDatePart(serverDate.getUTCHours())
  const minutes = padDatePart(serverDate.getUTCMinutes())
  const seconds = padDatePart(serverDate.getUTCSeconds())
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`
}

function padDatePart(value: number) {
  return String(value).padStart(2, '0')
}

function formatUtcOffset(offsetMinutes: number) {
  const sign = offsetMinutes >= 0 ? '+' : '-'
  const absoluteMinutes = Math.abs(offsetMinutes)
  const hours = padDatePart(Math.floor(absoluteMinutes / 60))
  const minutes = padDatePart(absoluteMinutes % 60)
  return `UTC${sign}${hours}:${minutes}`
}
</script>

<template>
  <AppShell>
    <template #header-actions>
      <div class="dashboard-toolbar">
        <span class="toolbar-pill">日期：{{ dashboardDateLabel }}</span>
        <label class="toolbar-select">
          <span>项目</span>
          <select
            v-model="selectedSportFilter"
            class="toolbar-select-input"
            :disabled="isSportFilterLocked"
            @change="handleSportFilterChange"
          >
            <option v-for="option in sportOptions" :key="option.id" :value="option.id">
              {{ option.name }}
            </option>
          </select>
        </label>
        <label v-if="showTeamFilter" class="toolbar-select">
          <span>队伍</span>
          <select v-model="selectedTeamFilter" class="toolbar-select-input" @change="handleTeamFilterChange">
            <option v-for="option in teamOptions" :key="option.id" :value="option.id">
              {{ option.name }}
            </option>
          </select>
        </label>
        <span v-else class="toolbar-pill">队伍：{{ selectedTeamLabel }}</span>
        <span class="toolbar-pill toolbar-pill--time">{{ serverTimeLabel }}</span>
        <span class="toolbar-pill toolbar-pill--muted">{{ refreshStatusLabel }}</span>
      </div>
    </template>

    <div class="dashboard-workbench">
      <section class="workbench-main">
        <section class="panel overview-panel">
          <div class="dashboard-panel-head">
            <div>
              <p class="dashboard-section-label">今日训练概况</p>
              <h3>今日训练状态</h3>
            </div>
            <p class="dashboard-panel-note">当前范围：{{ selectedSportLabel }} / {{ selectedTeamLabel }}</p>
          </div>

          <p v-if="monitoringError" class="dashboard-panel-alert dashboard-panel-alert--error">{{ monitoringError }}</p>

          <div class="dashboard-summary-grid" :class="{ 'dashboard-summary-grid--muted': loading }">
            <article
              v-for="metric in summaryMetrics"
              :key="metric.key"
              class="dashboard-summary-card"
              :class="`dashboard-summary-card--${metric.tone}`"
            >
              <span>{{ metric.label }}</span>
              <strong>{{ metric.value }}</strong>
              <p>{{ metric.hint }}</p>
            </article>
          </div>
        </section>

        <section class="panel tasks-panel">
          <div class="dashboard-panel-head">
            <div>
              <p class="dashboard-section-label">现在要处理</p>
              <h3>待处理事项</h3>
            </div>
          </div>

          <div v-if="taskItems.length" class="dashboard-task-list">
            <article
              v-for="task in taskItems"
              :key="task.key"
              class="dashboard-task-card"
              :class="`dashboard-task-card--${task.tone}`"
            >
              <div class="dashboard-task-count">
                <strong>{{ task.count }}</strong>
                <span>{{ task.label }}</span>
              </div>
              <div class="dashboard-task-copy">
                <p>{{ task.description }}</p>
              </div>
              <button class="secondary-btn dashboard-task-btn" type="button" @click="handleTaskAction(task.action)">
                {{ task.actionLabel }}
              </button>
            </article>
          </div>

          <article v-else-if="calmState" class="dashboard-task-empty">
            <div>
              <strong>{{ calmState.title }}</strong>
              <p>{{ calmState.description }}</p>
            </div>
            <button class="primary-btn" type="button" @click="handleTaskAction(calmState.action)">
              {{ calmState.actionLabel }}
            </button>
          </article>
        </section>

        <section class="panel memo-panel">
          <div class="dashboard-panel-head">
            <div>
              <p class="dashboard-section-label">教练白板</p>
              <h3>近期重点和训练提醒</h3>
            </div>
            <span class="dashboard-panel-note">{{ coachMemoStatusLabel }}</span>
          </div>

          <textarea
            :value="coachMemo"
            class="dashboard-memo-input"
            rows="9"
            maxlength="1200"
            placeholder="例如：重点关注张三深蹲膝内扣；周三前复核一队核心力量；本周卧推主项保守加重。"
            aria-label="教练白板备忘"
            @input="handleCoachMemoInput"
          ></textarea>
        </section>
      </section>

      <aside class="workbench-side">
        <section class="panel quick-panel">
          <div class="dashboard-panel-head">
            <div>
              <p class="dashboard-section-label">高频入口</p>
              <h3>常用入口</h3>
            </div>
          </div>

          <div class="dashboard-quick-grid">
            <button
              v-for="action in quickActions"
              :key="action.key"
              class="dashboard-quick-card"
              :class="{ 'dashboard-quick-card--primary': action.tone === 'primary' }"
              type="button"
              @click="handleQuickAction(action.route)"
            >
              <strong>{{ action.label }}</strong>
              <span>{{ action.description }}</span>
            </button>
          </div>
        </section>

        <section ref="syncPanelRef" class="panel sync-panel">
          <div class="dashboard-panel-head">
            <div>
              <p class="dashboard-section-label">异常明细</p>
              <h3>同步异常待处理</h3>
            </div>
            <span class="dashboard-panel-note">当前显示 {{ filteredSyncIssues.length }} 条</span>
          </div>

          <p v-if="syncNotice" class="dashboard-panel-alert" :class="`dashboard-panel-alert--${syncNoticeTone}`">{{ syncNotice }}</p>
          <p v-if="syncError" class="dashboard-panel-alert dashboard-panel-alert--warning">{{ syncError }}</p>

          <div v-if="syncPreviewIssues.length" class="dashboard-sync-list">
            <article v-for="issue in syncPreviewIssues" :key="issue.id" class="dashboard-sync-card">
              <div class="dashboard-sync-copy">
                <strong>{{ issue.athlete_name || `运动员 ${issue.athlete_id}` }}</strong>
                <span class="dashboard-sync-meta">{{ issue.session_date }} · {{ getTrainingSyncIssueLabel(issue.summary) }}</span>
                <span class="dashboard-sync-tag" :class="{ conflict: isTrainingSyncConflictSummary(issue.summary) }">
                  {{ getTrainingSyncIssueLabel(issue.summary) }}
                </span>
                <p>{{ issue.summary }}</p>
                <p v-if="issue.last_error" class="dashboard-sync-error">最近错误：{{ issue.last_error }}</p>
              </div>
              <button
                class="secondary-btn"
                type="button"
                :disabled="retryingIssueId === issue.id"
                @click="retrySyncIssue(issue.id)"
              >
                {{ retryingIssueId === issue.id ? '重试中...' : '手动重试' }}
              </button>
            </article>
          </div>

          <div v-else class="dashboard-empty-card">
            <strong>当前没有待处理的同步异常</strong>
            <p>训练端长时间未恢复的同步问题会显示在这里。</p>
          </div>

          <button
            v-if="hasSyncOverflow"
            class="ghost-btn slim link-btn"
            type="button"
            @click="handleTaskAction('reports')"
          >
            查看全部训练数据 / 异常
          </button>
        </section>

        <section v-if="systemActions.length" class="panel admin-panel">
          <div class="dashboard-panel-head">
            <div>
              <p class="dashboard-section-label">系统维护</p>
              <h3>管理员常用入口</h3>
            </div>
          </div>

          <div class="dashboard-admin-actions">
            <button
              v-for="action in systemActions"
              :key="action.key"
              class="dashboard-admin-action"
              type="button"
              @click="handleQuickAction(action.route)"
            >
              <strong>{{ action.label }}</strong>
              <span>{{ action.description }}</span>
            </button>
          </div>
        </section>
      </aside>
    </div>
  </AppShell>
</template>

<style>
.dashboard-workbench {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(320px, 0.95fr);
  gap: 18px;
  align-items: start;
}

.workbench-main,
.workbench-side {
  display: grid;
  gap: 18px;
}

.dashboard-toolbar {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
  min-width: 0;
}

.toolbar-pill,
.toolbar-select {
  min-height: 42px;
  border-radius: 999px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.88);
  padding: 0 14px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text);
  font-size: 13px;
  white-space: nowrap;
}

.toolbar-pill--muted {
  color: var(--muted);
}

.toolbar-select {
  padding-right: 8px;
}

.toolbar-select span {
  color: var(--muted);
}

.toolbar-select-input {
  border: none;
  background: transparent;
  color: var(--text);
  font: inherit;
  min-width: 128px;
  outline: none;
}

.dashboard-workbench .overview-panel,
.dashboard-workbench .tasks-panel,
.dashboard-workbench .memo-panel,
.dashboard-workbench .quick-panel,
.dashboard-workbench .sync-panel,
.dashboard-workbench .admin-panel {
  display: grid;
  gap: 16px;
}

.dashboard-panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.dashboard-panel-head h3,
.dashboard-panel-head p,
.dashboard-summary-card span,
.dashboard-summary-card p,
.dashboard-task-count span,
.dashboard-task-copy p,
.dashboard-empty-card p,
.dashboard-sync-copy p,
.dashboard-sync-copy span,
.dashboard-admin-action span {
  margin: 0;
}

.dashboard-section-label {
  margin: 0 0 6px;
  color: var(--muted);
  font-size: 13px;
}

.dashboard-panel-note {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

.dashboard-panel-alert {
  margin: 0;
  padding: 12px 14px;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 600;
}

.dashboard-panel-alert--success {
  background: #dcfce7;
  color: #166534;
}

.dashboard-panel-alert--warning {
  background: #fef3c7;
  color: #92400e;
}

.dashboard-panel-alert--error {
  background: #fee2e2;
  color: #b91c1c;
}

.dashboard-summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.dashboard-summary-grid--muted {
  opacity: 0.72;
}

.dashboard-summary-card {
  min-height: 114px;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: white;
  padding: 16px;
  display: grid;
  gap: 6px;
}

.dashboard-summary-card span,
.dashboard-summary-card p {
  color: var(--muted);
  font-size: 13px;
}

.dashboard-summary-card strong {
  font-size: 2rem;
  line-height: 1;
}

.dashboard-summary-card--progress {
  border-color: rgba(37, 99, 235, 0.24);
}

.dashboard-summary-card--success {
  border-color: rgba(22, 101, 52, 0.24);
}

.dashboard-summary-card--warning {
  border-color: rgba(194, 65, 12, 0.26);
}

.dashboard-summary-card--danger {
  border-color: rgba(185, 28, 28, 0.26);
}

.dashboard-task-list {
  display: grid;
  gap: 12px;
}

.dashboard-task-card {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr) auto;
  align-items: center;
  gap: 16px;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid var(--line);
  background: var(--panel-soft);
}

.dashboard-task-card--danger {
  border-color: rgba(185, 28, 28, 0.22);
}

.dashboard-task-card--warning {
  border-color: rgba(217, 119, 6, 0.24);
}

.dashboard-task-card--progress {
  border-color: rgba(37, 99, 235, 0.22);
}

.dashboard-task-count {
  display: grid;
  gap: 4px;
}

.dashboard-task-count strong {
  font-size: 2rem;
  line-height: 1;
}

.dashboard-task-count span {
  font-weight: 700;
}

.dashboard-task-copy p {
  color: var(--muted);
  line-height: 1.6;
}

.dashboard-task-btn {
  min-width: 128px;
}

.dashboard-task-empty,
.dashboard-empty-card {
  border-radius: 18px;
  border: 1px dashed rgba(15, 118, 110, 0.28);
  background: rgba(15, 118, 110, 0.06);
  padding: 18px;
  display: grid;
  gap: 12px;
}

.dashboard-task-empty strong,
.dashboard-empty-card strong,
.dashboard-sync-copy strong,
.dashboard-admin-action strong,
.dashboard-quick-card strong {
  font-size: 16px;
}

.dashboard-task-empty p,
.dashboard-empty-card p {
  margin: 6px 0 0;
  color: var(--muted);
  line-height: 1.6;
}

.dashboard-memo-input {
  width: 100%;
  min-height: 220px;
  resize: vertical;
  border: 1px solid rgba(15, 118, 110, 0.18);
  border-radius: 16px;
  background:
    linear-gradient(transparent 31px, rgba(15, 118, 110, 0.08) 32px),
    #fffdf7;
  background-size: 100% 32px;
  padding: 14px 16px;
  color: var(--text);
  line-height: 32px;
  outline: none;
  box-sizing: border-box;
}

.dashboard-memo-input::placeholder {
  color: rgba(100, 116, 139, 0.78);
}

.dashboard-memo-input:focus {
  border-color: rgba(15, 118, 110, 0.42);
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.12);
}

.dashboard-quick-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.dashboard-quick-card,
.dashboard-admin-action {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: var(--panel-soft);
  padding: 16px;
  display: grid;
  gap: 8px;
  text-align: left;
}

.dashboard-quick-card--primary {
  background: linear-gradient(135deg, rgba(15, 118, 110, 0.12), rgba(15, 118, 110, 0.05));
  border-color: rgba(15, 118, 110, 0.24);
}

.dashboard-quick-card span,
.dashboard-admin-action span {
  color: var(--muted);
  line-height: 1.5;
}

.dashboard-sync-list,
.dashboard-admin-actions {
  display: grid;
  gap: 12px;
}

.dashboard-sync-card {
  display: grid;
  gap: 14px;
  padding: 16px;
  border-radius: 18px;
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.22);
}

.dashboard-sync-copy {
  display: grid;
  gap: 6px;
}

.dashboard-sync-meta {
  color: var(--muted);
  font-size: 13px;
}

.dashboard-sync-tag {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(245, 158, 11, 0.14);
  color: #92400e;
  font-size: 12px;
  font-weight: 700;
}

.dashboard-sync-tag.conflict {
  background: rgba(220, 38, 38, 0.12);
  color: #b91c1c;
}

.dashboard-sync-copy p {
  color: var(--muted);
  line-height: 1.6;
}

.dashboard-sync-error {
  color: #92400e;
}

.link-btn {
  justify-self: start;
}

@media (max-width: 1280px) {
  .dashboard-workbench {
    grid-template-columns: 1fr;
  }

  .dashboard-quick-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {
  .dashboard-summary-grid,
  .dashboard-quick-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .dashboard-task-card {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .dashboard-toolbar {
    justify-content: flex-start;
  }

  .dashboard-summary-grid,
  .dashboard-quick-grid {
    grid-template-columns: 1fr;
  }
}
</style>
