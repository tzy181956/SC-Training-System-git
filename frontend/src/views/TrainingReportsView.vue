<script setup lang="ts">
import * as echarts from 'echarts'
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import { fetchAthletes, fetchSports, fetchTeams } from '@/api/athletes'
import { fetchAllExerciseListItems } from '@/api/exercises'
import { retryTrainingSyncIssue } from '@/api/sessions'
import { fetchTrainingReport, type TrainingReportResponse } from '@/api/trainingReports'
import StatCard from '@/components/common/StatCard.vue'
import AppShell from '@/components/layout/AppShell.vue'
import TrainingSessionCard from '@/components/report/TrainingSessionCard.vue'
import { getTrainingSyncIssueLabel, isTrainingSyncConflictSummary } from '@/constants/trainingSync'
import { useAuthStore } from '@/stores/auth'
import type { ExerciseListItem } from '@/types/exerciseLibrary'
import { todayString } from '@/utils/date'
import {
  filterTeamsBySport,
  isSportScoped,
  resolveInitialSportFilterValue,
  retainVisibleTeamId,
} from '@/utils/projectTeamScope'

const route = useRoute()
const authStore = useAuthStore()
const athletes = ref<any[]>([])
const sports = ref<any[]>([])
const teams = ref<any[]>([])
const exerciseOptions = ref<ExerciseListItem[]>([])
const loading = ref(false)
const report = ref<TrainingReportResponse | null>(null)
const reportNotice = ref('')
const reportNoticeTone = ref<'success' | 'warning' | 'error'>('success')
const retryingIssueId = ref<number | null>(null)
const mainLiftChartRef = ref<HTMLDivElement | null>(null)
const completionChartRef = ref<HTMLDivElement | null>(null)
const trackedExercisePickerOpen = ref(false)
const trackedExerciseSearch = ref('')
const selectedTrackedExerciseNames = ref<string[]>([])
const exerciseOptionLoadError = ref('')
let mainLiftChart: echarts.ECharts | null = null
let completionChart: echarts.ECharts | null = null
const TRACKED_EXERCISE_STORAGE_KEY = 'training-report-tracked-exercise-names-v1'

const filters = reactive({
  sportId: parseNumberQuery(route.query.sportId) || resolveInitialSportFilterValue(authStore.currentUser?.sport_id),
  teamId: parseNumberQuery(route.query.teamId),
  athleteId: parseNumberQuery(route.query.athleteId),
  dateFrom: parseStringQuery(route.query.dateFrom) || getDateBefore(29),
  dateTo: parseStringQuery(route.query.dateTo) || todayString(),
  onlyIncomplete: false,
  onlyMainLift: false,
})

const isSportFilterLocked = computed(() => isSportScoped(authStore.currentUser?.sport_id))
const visibleTeams = computed(() => {
  const athleteTeamIds = new Set(
    athletes.value
      .filter((athlete) => !filters.sportId || athlete.sport_id === filters.sportId)
      .map((athlete) => athlete.team_id)
      .filter((teamId): teamId is number => typeof teamId === 'number' && teamId > 0),
  )
  return filterTeamsBySport(teams.value, filters.sportId).filter((team) => athleteTeamIds.has(team.id))
})

const availableAthletes = computed(() => {
  return athletes.value.filter((athlete) => {
    if (filters.sportId && athlete.sport_id !== filters.sportId) return false
    if (filters.teamId && athlete.team_id !== filters.teamId) return false
    return true
  })
})

const reportSessions = computed(() => report.value?.sessions.filter((session) => session.status !== 'voided') || [])

const reportSetRecords = computed(() => reportSessions.value.flatMap((session) => (
  session.items.flatMap((item) => item.records || [])
)))

const averageRir = computed(() => {
  const rirValues = reportSetRecords.value
    .map((record) => Number(record.actual_rir))
    .filter((value) => Number.isFinite(value))
  if (!rirValues.length) return null
  return rirValues.reduce((sum, value) => sum + value, 0) / rirValues.length
})

const partialSessionCount = computed(() => reportSessions.value.filter((session) => session.status === 'partial_complete').length)
const absentSessionCount = computed(() => reportSessions.value.filter((session) => session.status === 'absent').length)
const attentionCount = computed(() => (report.value?.flags.length || 0) + (report.value?.sync_issues.length || 0))

const completionQualityHint = computed(() => {
  if (!report.value) return '当前暂无训练记录'
  const parts = [`完成 ${report.value.summary.completed_sessions}/${report.value.summary.total_sessions} 节`]
  if (partialSessionCount.value) parts.push(`部分完成 ${partialSessionCount.value} 节`)
  if (absentSessionCount.value) parts.push(`缺席 ${absentSessionCount.value} 节`)
  return parts.join('，')
})

const sessionTrendPoints = computed(() => reportSessions.value
  .map((session) => {
    const records = session.items.flatMap((item) => item.records || [])
    const rirValues = records
      .map((record) => Number(record.actual_rir))
      .filter((value) => Number.isFinite(value))
    return {
      session_date: session.session_date,
      template_name: session.template_name,
      volume: records.reduce((sum, record) => sum + calculateSetVolume(record), 0),
      average_rir: rirValues.length ? rirValues.reduce((sum, value) => sum + value, 0) / rirValues.length : null,
    }
  })
  .filter((point) => point.volume > 0 || point.average_rir !== null)
  .sort((a, b) => a.session_date.localeCompare(b.session_date)))

const trackedExerciseSummaries = computed(() => {
  const summaries = new Map<string, {
    exercise_name: string
    latest_date: string
    latest_weight: number | null
    latest_reps: number | null
    latest_rir: number | null
    latest_sort_key: string
    is_main_lift: boolean
    template_name: string
  }>()

  for (const session of reportSessions.value) {
    for (const item of session.items) {
      const latestRecord = [...(item.records || [])].sort((a, b) => {
        const timeCompare = String(b.completed_at || '').localeCompare(String(a.completed_at || ''))
        if (timeCompare !== 0) return timeCompare
        return Number(b.set_number || 0) - Number(a.set_number || 0)
      })[0]
      if (!latestRecord) continue

      const sortKey = `${session.session_date} ${latestRecord.completed_at || ''} ${String(latestRecord.set_number).padStart(3, '0')}`
      const existing = summaries.get(item.exercise_name)
      if (existing && existing.latest_sort_key >= sortKey) {
        existing.is_main_lift = existing.is_main_lift || item.is_main_lift
        continue
      }

      summaries.set(item.exercise_name, {
        exercise_name: item.exercise_name,
        latest_date: session.session_date,
        latest_weight: normalizeNumber(latestRecord.final_weight ?? latestRecord.actual_weight),
        latest_reps: normalizeNumber(latestRecord.actual_reps),
        latest_rir: normalizeNumber(latestRecord.actual_rir),
        latest_sort_key: sortKey,
        is_main_lift: item.is_main_lift,
        template_name: session.template_name,
      })
    }
  }

  return [...summaries.values()].sort((a, b) => {
    if (a.is_main_lift !== b.is_main_lift) return a.is_main_lift ? -1 : 1
    return b.latest_sort_key.localeCompare(a.latest_sort_key)
  })
})

const displayedTrackedExerciseSummaries = computed(() => {
  const selectedSet = new Set(selectedTrackedExerciseNames.value)
  return trackedExerciseSummaries.value.filter((item) => selectedSet.has(item.exercise_name))
})

const selectedTrackedExerciseRecordMissingCount = computed(() => (
  Math.max(selectedTrackedExerciseNames.value.length - displayedTrackedExerciseSummaries.value.length, 0)
))

const filteredTrackedExerciseOptions = computed(() => {
  const keyword = trackedExerciseSearch.value.trim().toLowerCase()
  const selected = new Set(selectedTrackedExerciseNames.value)
  return exerciseOptions.value
    .filter((exercise) => {
      if (!keyword) return true
      return [
        exercise.name,
        exercise.name_en,
        exercise.alias,
        exercise.level1_category,
        exercise.level2_category,
        exercise.category_path,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(keyword))
    })
    .sort((a, b) => {
      const selectedA = selected.has(a.name)
      const selectedB = selected.has(b.name)
      if (selectedA !== selectedB) return selectedA ? -1 : 1
      return a.name.localeCompare(b.name, 'zh-Hans-CN')
    })
    .slice(0, 40)
})

const latestSessionBrief = computed(() => {
  const session = [...reportSessions.value].sort((a, b) => b.session_date.localeCompare(a.session_date))[0]
  if (!session) return null
  const records = session.items.flatMap((item) => item.records || [])
  const volume = records.reduce((sum, record) => sum + calculateSetVolume(record), 0)
  const mainItems = session.items.filter((item) => item.is_main_lift)
  return {
    date: session.session_date,
    template: session.template_name,
    volume,
    mainLiftText: mainItems.length ? mainItems.map((item) => item.exercise_name).join('、') : '未标记主项',
    completionText: `${session.completed_items}/${session.total_items} 个动作，${session.completed_sets}/${session.total_sets} 组`,
  }
})

async function hydrate() {
  loadStoredTrackedExercises()
  void loadExerciseOptions()

  const [athleteData, sportData, teamData] = await Promise.all([
    fetchAthletes(),
    fetchSports(),
    fetchTeams(),
  ])
  athletes.value = athleteData
  sports.value = sportData
  teams.value = teamData

  if (isSportFilterLocked.value) {
    filters.sportId = resolveInitialSportFilterValue(authStore.currentUser?.sport_id)
  } else if (filters.sportId && !sports.value.some((sport) => sport.id === filters.sportId)) {
    filters.sportId = 0
  }
  filters.teamId = retainVisibleTeamId(filters.teamId, visibleTeams.value)

  if (filters.athleteId) {
    const matchedAthlete = athletes.value.find((athlete) => athlete.id === filters.athleteId)
    if (matchedAthlete?.sport_id && !filters.sportId) {
      filters.sportId = matchedAthlete.sport_id
      filters.teamId = retainVisibleTeamId(filters.teamId, visibleTeams.value)
    }
    if (matchedAthlete?.team_id && !filters.teamId) {
      filters.teamId = matchedAthlete.team_id
    }
  }

  syncAthleteSelection()
  if (!filters.athleteId && availableAthletes.value[0]) {
    filters.athleteId = availableAthletes.value[0].id
  }
  if (filters.athleteId) {
    await loadReport()
  }
}

async function loadExerciseOptions() {
  exerciseOptionLoadError.value = ''
  try {
    exerciseOptions.value = await fetchAllExerciseListItems(100)
  } catch {
    exerciseOptions.value = []
    exerciseOptionLoadError.value = '动作库加载失败，请刷新页面后再选择关注动作。'
  }
}

async function loadReport() {
  if (!filters.athleteId) return
  loading.value = true
  try {
    report.value = await fetchTrainingReport({
      athlete_id: filters.athleteId,
      date_from: filters.dateFrom,
      date_to: filters.dateTo,
    })
    await nextTick()
    renderCharts()
  } finally {
    loading.value = false
  }
}

async function retrySyncIssue(issueId: number) {
  retryingIssueId.value = issueId
  try {
    await retryTrainingSyncIssue(issueId)
    reportNotice.value = '同步异常已重试，待处理标记已刷新。'
    reportNoticeTone.value = 'success'
    await loadReport()
  } catch {
    reportNotice.value = '手动重试失败，请回到训练模式所在设备继续处理。'
    reportNoticeTone.value = 'warning'
  } finally {
    retryingIssueId.value = null
  }
}

function showNotice(payload: { message: string; tone: 'success' | 'warning' | 'error' }) {
  reportNotice.value = payload.message
  reportNoticeTone.value = payload.tone
}

function syncAthleteSelection() {
  if (!availableAthletes.value.length) {
    filters.athleteId = 0
    return
  }

  const athleteStillVisible = availableAthletes.value.some((athlete) => athlete.id === filters.athleteId)
  if (athleteStillVisible) return

  filters.athleteId = availableAthletes.value[0].id
}

function toggleTrackedExercise(name: string) {
  const selected = new Set(selectedTrackedExerciseNames.value)
  if (selected.has(name)) {
    selected.delete(name)
  } else {
    selected.add(name)
  }
  selectedTrackedExerciseNames.value = [...selected]
}

function loadStoredTrackedExercises() {
  try {
    const raw = window.localStorage.getItem(TRACKED_EXERCISE_STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    selectedTrackedExerciseNames.value = Array.isArray(parsed)
      ? parsed.map((item) => String(item).trim()).filter(Boolean)
      : []
  } catch {
    selectedTrackedExerciseNames.value = []
  }
}

function persistTrackedExercises() {
  try {
    window.localStorage.setItem(TRACKED_EXERCISE_STORAGE_KEY, JSON.stringify(selectedTrackedExerciseNames.value))
  } catch {
    // 本地存储不可用时不阻断训练数据查看。
  }
}

function normalizeNumber(value: number | string | null | undefined) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function calculateSetVolume(record: { final_weight?: number | null; actual_weight?: number | null; actual_reps?: number | null }) {
  const weight = Number(record.final_weight ?? record.actual_weight ?? 0)
  const reps = Number(record.actual_reps ?? 0)
  if (!Number.isFinite(weight) || !Number.isFinite(reps)) return 0
  return Math.max(weight, 0) * Math.max(reps, 0)
}

function formatVolume(value: number) {
  if (!Number.isFinite(value) || value <= 0) return '暂无'
  if (value >= 1000) return `${(value / 1000).toFixed(value >= 10000 ? 1 : 2)} 吨`
  return `${Math.round(value)} kg`
}

function formatRir(value: number | null) {
  if (value === null || !Number.isFinite(value)) return '暂无'
  return value.toFixed(1)
}

function formatWeight(value: number | null) {
  if (value === null || !Number.isFinite(value)) return '暂无重量'
  return `${Number.isInteger(value) ? value.toFixed(0) : value.toFixed(1)} kg`
}

function renderCharts() {
  if (mainLiftChartRef.value && report.value) {
    mainLiftChart ||= echarts.init(mainLiftChartRef.value)
    mainLiftChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      grid: { left: 48, right: 24, top: 42, bottom: 24 },
      xAxis: { type: 'category' },
      yAxis: { type: 'value', name: '重量（千克）' },
      series: (report.value.trend.main_lift_series || []).map((item: any) => ({
        name: item.exercise_name,
        type: 'line',
        smooth: true,
        data: item.points.map((point: any) => [point.session_date, point.value]),
      })),
    })
  }

  if (completionChartRef.value && report.value) {
    completionChart ||= echarts.init(completionChartRef.value)
    const points = sessionTrendPoints.value
    completionChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { top: 0 },
      grid: { left: 56, right: 48, top: 42, bottom: 24 },
      xAxis: { type: 'category', data: points.map((item) => item.session_date) },
      yAxis: [
        { type: 'value', name: '训练量（kg）' },
        { type: 'value', name: 'RIR', min: 0, max: 10 },
      ],
      series: [
        {
          name: '训练量',
          type: 'bar',
          data: points.map((item) => Math.round(item.volume)),
          itemStyle: { color: '#0f766e' },
        },
        {
          name: '平均 RIR',
          type: 'line',
          smooth: true,
          yAxisIndex: 1,
          data: points.map((item) => item.average_rir === null ? null : Number(item.average_rir.toFixed(1))),
          itemStyle: { color: '#f59e0b' },
        },
      ],
    })
  }
}

watch(
  () => filters.sportId,
  () => {
    if (isSportFilterLocked.value) {
      filters.sportId = resolveInitialSportFilterValue(authStore.currentUser?.sport_id)
    }
    filters.teamId = retainVisibleTeamId(filters.teamId, visibleTeams.value)
    syncAthleteSelection()
  },
)

watch(
  () => filters.teamId,
  () => {
    syncAthleteSelection()
  },
)

watch(
  () => [filters.athleteId, filters.dateFrom, filters.dateTo],
  () => {
    if (filters.athleteId) {
      loadReport()
      return
    }
    report.value = null
  },
)

watch(selectedTrackedExerciseNames, persistTrackedExercises, { deep: true })

onMounted(hydrate)

function getDateBefore(days: number) {
  const current = new Date()
  current.setDate(current.getDate() - days)
  const year = current.getFullYear()
  const month = String(current.getMonth() + 1).padStart(2, '0')
  const day = String(current.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function parseNumberQuery(value: unknown) {
  if (typeof value !== 'string') return 0
  const parsed = Number(value)
  return Number.isNaN(parsed) ? 0 : parsed
}

function parseStringQuery(value: unknown) {
  return typeof value === 'string' ? value : ''
}
</script>

<template>
  <AppShell>
    <div class="report-layout">
      <aside class="panel filter-panel">
        <div>
          <p class="eyebrow">筛选条件</p>
          <h3>训练数据</h3>
        </div>

        <label class="field">
          <span>项目</span>
          <select v-model.number="filters.sportId" class="text-input" :disabled="isSportFilterLocked">
            <option :value="0">全部项目</option>
            <option v-for="sport in sports" :key="sport.id" :value="sport.id">
              {{ sport.name }}
            </option>
          </select>
        </label>

        <label class="field">
          <span>队伍</span>
          <select v-model.number="filters.teamId" class="text-input">
            <option :value="0">全部队伍</option>
            <option v-for="team in visibleTeams" :key="team.id" :value="team.id">
              {{ team.name }}
            </option>
          </select>
        </label>

        <label class="field">
          <span>运动员</span>
          <select v-model.number="filters.athleteId" class="text-input">
            <option v-for="athlete in availableAthletes" :key="athlete.id" :value="athlete.id">
              {{ athlete.full_name }}
            </option>
          </select>
        </label>

        <label class="field">
          <span>开始日期</span>
          <input v-model="filters.dateFrom" type="date" class="text-input" />
        </label>

        <label class="field">
          <span>结束日期</span>
          <input v-model="filters.dateTo" type="date" class="text-input" />
        </label>

        <label class="checkbox-row">
          <input v-model="filters.onlyIncomplete" type="checkbox" />
          <span>仅看未完成训练</span>
        </label>

        <label class="checkbox-row">
          <input v-model="filters.onlyMainLift" type="checkbox" />
          <span>仅看主项动作</span>
        </label>

        <button class="primary-btn" @click="loadReport">刷新数据</button>
      </aside>

      <section class="report-main">
        <template v-if="report">
          <div class="summary-grid">
            <article class="tracked-exercise-panel" @click="trackedExercisePickerOpen = true">
              <div class="tracked-exercise-head">
                <div>
                  <p class="eyebrow">重点动作</p>
                  <h3>最近一次训练重量</h3>
                </div>
                <button class="ghost-btn tracked-picker-btn" type="button" @click.stop="trackedExercisePickerOpen = !trackedExercisePickerOpen">
                  {{ trackedExercisePickerOpen ? '收起选择' : '选择动作' }}
                </button>
              </div>

              <div v-if="displayedTrackedExerciseSummaries.length" class="tracked-exercise-grid">
                <div v-for="item in displayedTrackedExerciseSummaries" :key="item.exercise_name" class="tracked-exercise-card">
                  <div>
                    <strong>{{ item.exercise_name }}</strong>
                    <span v-if="item.is_main_lift" class="main-lift-tag">主项</span>
                  </div>
                  <p>{{ formatWeight(item.latest_weight) }}</p>
                  <small>{{ item.latest_date }} · {{ item.latest_reps ?? '暂无' }} 次 · RIR {{ formatRir(item.latest_rir) }}</small>
                </div>
              </div>
              <p v-else-if="selectedTrackedExerciseNames.length" class="tracked-empty">
                已选择 {{ selectedTrackedExerciseNames.length }} 个关注动作，当前运动员在筛选时间内暂无这些动作的训练记录。
              </p>
              <p v-else class="tracked-empty">请选择教练长期关注的动作，例如深蹲、硬拉、卧推。</p>
              <p v-if="selectedTrackedExerciseRecordMissingCount" class="tracked-empty">
                另有 {{ selectedTrackedExerciseRecordMissingCount }} 个已选动作当前没有记录，已自动隐藏。
              </p>

              <div v-if="trackedExercisePickerOpen" class="tracked-picker" @click.stop>
                <p>选择要放在卡片里的动作，可多选。选择会在所有运动员页面通用。</p>
                <input
                  v-model="trackedExerciseSearch"
                  class="text-input tracked-search-input"
                  type="search"
                  placeholder="搜索动作，例如深蹲、硬拉、卧推"
                />
                <div class="tracked-picker-list">
                  <label v-for="item in filteredTrackedExerciseOptions" :key="item.id" class="tracked-picker-option">
                    <input
                      type="checkbox"
                      :checked="selectedTrackedExerciseNames.includes(item.name)"
                      @change="toggleTrackedExercise(item.name)"
                    />
                    <span>{{ item.name }}</span>
                    <em>{{ item.category_path || item.level2_category || item.level1_category || '未分类' }}</em>
                  </label>
                </div>
                <p v-if="exerciseOptionLoadError" class="tracked-empty tracked-empty--error">{{ exerciseOptionLoadError }}</p>
                <p v-if="!filteredTrackedExerciseOptions.length" class="tracked-empty">没有匹配动作，请换一个关键词。</p>
              </div>
            </article>
            <StatCard label="平均 RIR" :value="formatRir(averageRir)" hint="越低代表接近力竭，需结合动作表现判断" />
            <StatCard
              label="完成质量"
              :value="`${report.summary.completion_rate}%`"
              :hint="completionQualityHint"
            />
            <StatCard
              label="需要关注"
              :value="attentionCount"
              :hint="attentionCount ? '包含训练异常和同步异常' : '当前筛选范围内暂无异常'"
            />
          </div>

          <p v-if="report.summary.voided_sessions" class="report-note">
            已作废训练课 {{ report.summary.voided_sessions }} 节，默认不计入上方课次、组数、完成率和趋势统计。
          </p>

          <p v-if="reportNotice" class="report-notice" :class="reportNoticeTone">{{ reportNotice }}</p>

          <section class="panel focus-panel">
            <div class="panel-head">
              <div>
                <p class="eyebrow">教练判断</p>
                <h3>需要关注</h3>
              </div>
              <span v-if="latestSessionBrief" class="latest-session-pill">最近训练：{{ latestSessionBrief.date }}</span>
            </div>

            <div v-if="report.flags.length || latestSessionBrief" class="focus-grid">
              <article v-if="latestSessionBrief" class="focus-card focus-card--neutral">
                <p>最近一课</p>
                <strong>{{ latestSessionBrief.template }}</strong>
                <span>{{ latestSessionBrief.completionText }}</span>
                <span>训练量 {{ formatVolume(latestSessionBrief.volume) }}，主项：{{ latestSessionBrief.mainLiftText }}</span>
              </article>
              <article v-for="(flag, index) in report.flags" :key="index" class="focus-card focus-card--warning">
                <p>{{ flag.level }}</p>
                <strong>{{ flag.title }}</strong>
                <span>{{ flag.description }}</span>
              </article>
            </div>
            <div v-else class="empty-state empty-state--compact">当前时间范围内暂无训练异常。</div>
          </section>

          <section class="panel sync-issue-panel">
            <div class="panel-head">
              <div>
                <p class="eyebrow">同步</p>
                <h3>同步异常待处理</h3>
              </div>
            </div>
            <div v-if="report.sync_issues?.length" class="sync-issue-list">
              <article v-for="issue in report.sync_issues" :key="issue.id" class="sync-issue-card">
                <div class="sync-issue-copy">
                  <strong>{{ issue.session_date }} {{ getTrainingSyncIssueLabel(issue.summary) }}</strong>
                  <p class="sync-issue-tag" :class="{ conflict: isTrainingSyncConflictSummary(issue.summary) }">
                    {{ getTrainingSyncIssueLabel(issue.summary) }}
                  </p>
                  <p>{{ issue.summary }}</p>
                  <p v-if="issue.last_error" class="sync-issue-error">最近错误：{{ issue.last_error }}</p>
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
            <div v-else class="empty-state">当前筛选范围内没有待处理的同步异常。</div>
          </section>

          <div class="two-col-panels">
            <section class="panel">
              <div class="panel-head">
                <div>
                  <p class="eyebrow">趋势</p>
                  <h3>主项最终重量趋势</h3>
                </div>
              </div>
              <div v-if="report.trend.main_lift_series.length" ref="mainLiftChartRef" class="chart"></div>
              <div v-else class="empty-state">当前时间范围内暂无主项趋势数据。可以先在模板中标记主项，或积累至少 2 次主项训练记录。</div>
            </section>

            <section class="panel">
              <div class="panel-head">
                <div>
                  <p class="eyebrow">趋势</p>
                  <h3>训练量与 RIR 趋势</h3>
                </div>
              </div>
              <div v-if="sessionTrendPoints.length" ref="completionChartRef" class="chart"></div>
              <div v-else class="empty-state">当前时间范围内暂无可计算训练量或 RIR 的组记录。</div>
            </section>
          </div>

          <section class="panel session-panel">
            <div class="panel-head">
              <div>
                <p class="eyebrow">明细</p>
                <h3>训练课次记录</h3>
              </div>
            </div>

            <div v-if="report.sessions.length" class="session-list">
              <TrainingSessionCard
                v-for="session in report.sessions"
                :key="session.id"
                :session="session"
                :only-incomplete="filters.onlyIncomplete"
                :only-main-lift="filters.onlyMainLift"
                @changed="loadReport"
                @notify="showNotice"
              />
            </div>
            <div v-else class="empty-state">当前时间范围内暂无训练记录。</div>
          </section>
        </template>

        <section v-else class="panel empty-panel">
          <h3>请选择运动员查看训练数据</h3>
          <p>{{ loading ? '正在加载训练数据，请稍候。' : '左侧选择运动员和时间范围后，即可查看训练执行情况、趋势和异常提醒。' }}</p>
        </section>
      </section>
    </div>
  </AppShell>
</template>

<style scoped>
.report-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 18px;
  min-width: 0;
}

.filter-panel,
.report-main,
.session-list {
  display: grid;
  gap: 14px;
  align-content: start;
}

.report-main {
  min-width: 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: minmax(420px, 1.6fr) repeat(3, minmax(0, 1fr));
  gap: 16px;
  align-items: stretch;
}

.tracked-exercise-panel {
  position: relative;
  display: grid;
  gap: 12px;
  min-height: 166px;
  padding: 18px;
  border-radius: var(--radius);
  background: linear-gradient(135deg, rgba(236, 254, 255, 0.92), rgba(255, 255, 255, 0.96));
  border: 1px solid rgba(15, 118, 110, 0.16);
  box-shadow: var(--shadow);
  cursor: pointer;
}

.tracked-exercise-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.tracked-exercise-head h3,
.tracked-exercise-head p {
  margin: 0;
}

.tracked-picker-btn {
  flex-shrink: 0;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 13px;
}

.tracked-exercise-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.tracked-exercise-card {
  display: grid;
  gap: 5px;
  min-width: 0;
  padding: 12px;
  border-radius: 16px;
  background: white;
  border: 1px solid rgba(15, 23, 42, 0.06);
}

.tracked-exercise-card div {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.tracked-exercise-card strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}

.tracked-exercise-card p {
  margin: 0;
  color: var(--text);
  font-size: 24px;
  font-weight: 800;
}

.tracked-exercise-card small,
.tracked-empty,
.tracked-picker p {
  margin: 0;
  color: var(--text-soft);
  font-size: 12px;
}

.tracked-empty--error {
  color: #b91c1c;
  font-weight: 700;
}

.main-lift-tag {
  flex-shrink: 0;
  padding: 3px 7px;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.1);
  color: #0f766e;
  font-size: 11px;
  font-weight: 800;
}

.tracked-picker {
  display: grid;
  gap: 8px;
  padding: 12px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(15, 118, 110, 0.16);
}

.tracked-picker-list {
  display: grid;
  gap: 8px;
  max-height: 260px;
  overflow-y: auto;
  padding-right: 4px;
}

.tracked-picker-option {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 8px;
  align-items: center;
  min-height: 34px;
  color: var(--text);
  font-size: 13px;
  font-weight: 700;
}

.tracked-picker-option span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tracked-picker-option em {
  color: var(--text-soft);
  font-style: normal;
}

.report-notice {
  margin: 0;
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 14px;
  font-weight: 600;
}

.report-note {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
  font-weight: 700;
}

.report-notice.success {
  background: #dcfce7;
  color: #166534;
}

.report-notice.warning {
  background: #fef3c7;
  color: #92400e;
}

.report-notice.error {
  background: #fee2e2;
  color: #b91c1c;
}

.two-col-panels {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.sync-issue-list {
  display: grid;
  gap: 12px;
}

.sync-issue-card {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  border-radius: 16px;
  border: 1px solid rgba(245, 158, 11, 0.28);
  background: rgba(245, 158, 11, 0.1);
}

.sync-issue-copy {
  display: grid;
  gap: 6px;
}

.sync-issue-tag {
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

.sync-issue-tag.conflict {
  background: rgba(220, 38, 38, 0.12);
  color: #b91c1c;
}

.sync-issue-copy strong,
.sync-issue-copy p,
.sync-issue-error {
  margin: 0;
}

.sync-issue-error {
  color: #92400e;
  font-size: 13px;
}

.focus-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.focus-card {
  display: grid;
  gap: 6px;
  min-height: 116px;
  padding: 16px;
  border-radius: 18px;
}

.focus-card p,
.focus-card strong,
.focus-card span {
  margin: 0;
}

.focus-card p {
  color: var(--text-soft);
  font-size: 13px;
  font-weight: 700;
}

.focus-card span {
  color: var(--text-soft);
  font-size: 13px;
  line-height: 1.45;
}

.focus-card--neutral {
  background: rgba(236, 254, 255, 0.72);
  border: 1px solid rgba(15, 118, 110, 0.16);
}

.focus-card--warning {
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.24);
}

.latest-session-pill {
  display: inline-flex;
  align-items: center;
  min-height: 32px;
  padding: 0 12px;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.1);
  color: #0f766e;
  font-size: 13px;
  font-weight: 700;
}

.panel-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.eyebrow,
.field span,
.empty-state {
  margin: 0;
  color: var(--text-soft);
  font-size: 14px;
}

.field {
  display: grid;
  gap: 8px;
}

.checkbox-row {
  display: flex;
  gap: 10px;
  align-items: center;
  min-height: var(--touch);
}

.chart {
  width: 100%;
  height: 300px;
}

.empty-panel,
.empty-state {
  padding: 20px;
}

.empty-state--compact {
  padding: 12px 0 0;
}

@media (max-width: 1280px) {
  .report-layout,
  .summary-grid,
  .two-col-panels,
  .focus-grid {
    grid-template-columns: 1fr;
  }

  .tracked-exercise-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
