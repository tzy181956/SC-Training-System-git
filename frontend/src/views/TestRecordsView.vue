<script setup lang="ts">
import axios from 'axios'
import * as echarts from 'echarts'
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'

import { fetchAthletes, fetchSports, fetchTeams, type SportRead, type TeamRead } from '@/api/athletes'
import {
  calculateTestScores,
  createTestMetricDefinition,
  createTestRecord,
  createScoreProfile,
  createTestTypeDefinition,
  deleteFilteredTestRecords,
  deleteScoreProfile,
  deleteTestMetricDefinition,
  deleteTestTypeDefinition,
  downloadTestRecordTemplate,
  exportTestRecordLibrary,
  fetchAllTestRecords,
  fetchScoreProfiles,
  fetchTestDefinitions,
  fetchTestRecords,
  importTestRecords,
  updateScoreProfile,
  updateTestMetricDefinition,
  updateTestTypeDefinition,
  type ScoreCalculationResponse,
  type ScoreDimensionWrite,
  type ScoreProfileRead,
  type TestRecordLibraryItem,
  type TestRecordLibraryResponse,
  type TestMetricDefinitionRead,
  type TestTypeDefinitionRead,
} from '@/api/testRecords'
import AppShell from '@/components/layout/AppShell.vue'
import { useAuthStore } from '@/stores/auth'
import { todayString } from '@/utils/date'
import { confirmDangerousAction } from '@/utils/dangerousAction'
import { getTestMetricDirectionMeta } from '@/utils/testMetricDirection'

type Athlete = {
  id: number
  full_name: string
  sport_id?: number | null
  team_id?: number | null
  weight?: number | null
  sport?: { id?: number | null; name?: string | null } | null
  team?: { id?: number | null; sport_id?: number | null; name?: string | null } | null
}

type TestRecord = {
  id: number
  athlete_id: number
  test_date: string
  test_type: string
  metric_name: string
  result_value: number
  result_text?: string | null
  unit: string
  notes?: string | null
  athlete?: Athlete | null
}

type MetricRangePoint = {
  test_date: string
  average_value: number
  min_value: number
  max_value: number
}

type ManagedMetricDefinition = TestMetricDefinitionRead & {
  test_type_name: string
  sport_id?: number | null
  sport_name?: string | null
  is_system: boolean
}

const authStore = useAuthStore()
const athletes = ref<Athlete[]>([])
const sports = ref<SportRead[]>([])
const teams = ref<TeamRead[]>([])
const records = ref<TestRecord[]>([])
const definitions = ref<TestTypeDefinitionRead[]>([])
const chartRef = ref<HTMLDivElement | null>(null)
const importInputRef = ref<HTMLInputElement | null>(null)
const libraryTableRef = ref<HTMLElement | null>(null)
const loading = ref(false)
const importBusy = ref(false)
const exportBusy = ref(false)
const templateBusy = ref(false)
const actionMessage = ref('')
const libraryLoading = ref(false)
const libraryLoadingMore = ref(false)
const libraryError = ref('')

const DEFAULT_LIBRARY_PAGE_SIZE = 50
const LIBRARY_SCROLL_THRESHOLD = 120

const typeManagerOpen = ref(false)
const metricManagerOpen = ref(false)
const typeSubmitting = ref(false)
const metricSubmitting = ref(false)
const deletingTypeId = ref<number | null>(null)
const deletingMetricId = ref<number | null>(null)
const editingTypeId = ref<number | null>(null)
const editingMetricId = ref<number | null>(null)
const typeManagerError = ref('')
const metricManagerError = ref('')
const scoreProfileManagerOpen = ref(false)
const scoreSubmitting = ref(false)
const scoreProfileError = ref('')
const editingScoreProfileId = ref<number | null>(null)
const scoreProfiles = ref<ScoreProfileRead[]>([])
const scoreCalculation = ref<ScoreCalculationResponse | null>(null)
const scoreCalculationLoading = ref(false)
const selectedScoreAthleteId = ref<number>(0)
const scoreRadarRef = ref<HTMLDivElement | null>(null)
let scoreRadarChart: echarts.ECharts | null = null
let scoreAutoCalculateTimer: number | null = null

let chart: echarts.ECharts | null = null

const ratioMetrics = new Set(['卧推', '卧拉', '深蹲', '挺举'])

const trendFilters = reactive({
  sportId: 0,
  teamId: 0,
  athleteId: 0,
  testType: '',
  metricName: '',
  dateFrom: '',
  dateTo: '',
})

const entryForm = reactive({
  testDate: todayString(),
  resultValue: 0,
  resultText: '',
  unit: '',
  notes: '',
})

const libraryFilters = reactive({
  athleteKeyword: '',
  metricKeyword: '',
  testType: '',
})

const libraryState = reactive<TestRecordLibraryResponse>({
  items: [],
  total: 0,
  page: 1,
  page_size: DEFAULT_LIBRARY_PAGE_SIZE,
  total_pages: 0,
})

const entryPanelOpen = ref(false)

const typeForm = reactive({
  name: '',
  sport_id: null as number | null,
  notes: '',
})

const metricForm = reactive({
  test_type_id: null as number | null,
  name: '',
  default_unit: '',
  is_lower_better: false,
  notes: '',
})
const scoreFilters = reactive({
  scoreProfileId: 0,
  teamId: 0,
  dateFrom: '',
  dateTo: '',
  baselineMode: 'current_batch' as 'current_batch' | 'historical_pool',
})
const scoreProfileForm = reactive<{
  name: string
  notes: string
  is_active: boolean
  dimensions: ScoreDimensionWrite[]
}>({
  name: '',
  notes: '',
  is_active: true,
  dimensions: [],
})

const selectedAthlete = computed(() => athletes.value.find((item) => item.id === trendFilters.athleteId) || null)

const selectedTypeDefinition = computed(() => definitions.value.find((item) => item.name === trendFilters.testType) || null)

const trendSportOptions = computed(() => collectTrendSportOptions())

const trendTeamOptions = computed(() => collectTrendTeamOptions(trendFilters.sportId))

const availableTrendAthletes = computed(() => collectTrendAthletes(trendFilters.sportId, trendFilters.teamId))

const metricDefinitions = computed<ManagedMetricDefinition[]>(() =>
  definitions.value.flatMap((definition) =>
    definition.metrics.map((metric) => ({
      ...metric,
      test_type_name: definition.name,
      sport_id: definition.sport_id,
      sport_name: definition.sport_name,
      is_system: definition.is_system,
    })),
  ),
)

const scoreMetricOptions = computed(() =>
  metricDefinitions.value
    .map((definition) => ({
      id: definition.id,
      label: `${definition.test_type_name || '未分类测试类型'} / ${definition.name || `测试项目 #${definition.id}`}`,
    }))
    .sort((left, right) => left.label.localeCompare(right.label, 'zh-CN')),
)

const editableTypeDefinitions = computed(() =>
  authStore.isAdmin ? definitions.value : definitions.value.filter((definition) => !definition.is_system),
)

const availableMetricDefinitions = computed(() => selectedTypeDefinition.value?.metrics || [])

const selectedMetricDefinition = computed(
  () =>
    metricDefinitions.value.find(
      (item) => item.test_type_name === trendFilters.testType && item.name === trendFilters.metricName,
    ) || null,
)

const selectedMetricDirectionMeta = computed(() => getTestMetricDirectionMeta(selectedMetricDefinition.value))
const selectedScoreProfile = computed(() => scoreProfiles.value.find((item) => item.id === scoreFilters.scoreProfileId) || null)
const selectedScoreAthlete = computed(
  () => scoreCalculation.value?.ranking.find((item) => item.athlete_id === selectedScoreAthleteId.value) || null,
)
const scoreTeamDateRange = computed(() => {
  const dates = records.value
    .filter((record) => {
      if (!scoreFilters.teamId) return false
      return resolveAthleteTeamId(resolveRecordAthlete(record)) === scoreFilters.teamId
    })
    .map((record) => record.test_date)
    .filter(Boolean)
    .sort((left, right) => left.localeCompare(right))

  if (!dates.length) return null
  return {
    from: dates[0],
    to: dates[dates.length - 1],
  }
})

const chartMetricUnit = computed(
  () => selectedMetricDefinition.value?.default_unit || filteredTrendRecords.value[0]?.unit || '',
)

const athleteLookup = computed(() => new Map(athletes.value.map((item) => [item.id, item])))

const filteredTrendRecords = computed(() =>
  records.value
    .filter((item) => {
      if (!recordMatchesTrendScope(item)) return false
      if (trendFilters.athleteId && item.athlete_id !== trendFilters.athleteId) return false
      if (trendFilters.testType && item.test_type !== trendFilters.testType) return false
      if (trendFilters.metricName && item.metric_name !== trendFilters.metricName) return false
      return true
    })
    .slice()
    .sort((left, right) => {
      const dateCompare = left.test_date.localeCompare(right.test_date)
      if (dateCompare !== 0) return dateCompare
      return left.id - right.id
    }),
)

const filteredTrendResultCards = computed(() =>
  filteredTrendRecords.value
    .slice()
    .sort((left, right) => {
      const dateCompare = right.test_date.localeCompare(left.test_date)
      if (dateCompare !== 0) return dateCompare
      return right.id - left.id
    }),
)

const teamRangeMetricRecords = computed<MetricRangePoint[]>(() => {
  if (!trendFilters.testType || !trendFilters.metricName) return []

  const grouped = records.value
    .filter((item) => {
      if (!recordMatchesTrendScope(item, { includeAthlete: false })) return false
      if (item.test_type !== trendFilters.testType) return false
      if (item.metric_name !== trendFilters.metricName) return false
      return true
    })
    .reduce(
      (accumulator: Map<string, { total: number; count: number; min: number; max: number }>, item) => {
        const value = Number(item.result_value || 0)
        const entry = accumulator.get(item.test_date) || { total: 0, count: 0, min: value, max: value }
        entry.total += value
        entry.count += 1
        entry.min = Math.min(entry.min, value)
        entry.max = Math.max(entry.max, value)
        accumulator.set(item.test_date, entry)
        return accumulator
      },
      new Map<string, { total: number; count: number; min: number; max: number }>(),
    )

  return Array.from(grouped.entries())
    .map(([testDate, entry]) => ({
      test_date: testDate,
      average_value: Number((entry.total / entry.count).toFixed(2)),
      min_value: Number(entry.min.toFixed(2)),
      max_value: Number(entry.max.toFixed(2)),
    }))
    .sort((left, right) => left.test_date.localeCompare(right.test_date))
})

const chartDates = computed<string[]>(() =>
  Array.from(
    new Set([
      ...filteredTrendRecords.value.map((item) => item.test_date),
      ...teamRangeMetricRecords.value.map((item) => item.test_date),
    ]),
  ).sort((left, right) => left.localeCompare(right)),
)

const chartTitle = computed(() => {
  const athleteName = selectedAthlete.value?.full_name || '当前运动员'
  return `${athleteName} - ${trendFilters.metricName || '测试项目'} 趋势`
})

const hasLibraryFilters = computed(
  () => Boolean(libraryFilters.athleteKeyword.trim() || libraryFilters.metricKeyword.trim() || libraryFilters.testType),
)

const libraryItems = computed(() => libraryState.items)
const libraryTotal = computed(() => libraryState.total)
const libraryPage = computed(() => libraryState.page)
const libraryPageSize = computed(() => libraryState.page_size)
const libraryTotalPages = computed(() => libraryState.total_pages)
const libraryHasMore = computed(() => libraryPage.value < libraryTotalPages.value)

const libraryAthleteOptions = computed(() =>
  Array.from(new Set(records.value.map((record) => record.athlete?.full_name || '').filter(Boolean))).sort((left, right) =>
    left.localeCompare(right, 'zh-CN'),
  ),
)

const libraryMetricOptions = computed(() =>
  Array.from(
    new Set([
      ...metricDefinitions.value.map((definition) => definition.name),
      ...records.value.map((record) => record.metric_name),
    ].filter(Boolean)),
  ).sort((left, right) => left.localeCompare(right, 'zh-CN')),
)

const libraryTestTypeOptions = computed(() =>
  Array.from(
    new Set([
      ...definitions.value.map((definition) => definition.name),
      ...records.value.map((record) => record.test_type),
    ].filter(Boolean)),
  ).sort((left, right) => left.localeCompare(right, 'zh-CN')),
)

const canSubmitType = computed(() => Boolean(typeForm.name.trim()))
const canSubmitMetric = computed(() => metricForm.test_type_id !== null && Boolean(metricForm.name.trim()))
const canSubmitEntryRecord = computed(
  () =>
    Boolean(
      trendFilters.athleteId &&
      trendFilters.testType.trim() &&
      trendFilters.metricName.trim() &&
      entryActiveUnit.value.trim(),
    ),
)

const entryActiveUnit = computed(() => entryForm.unit || selectedMetricDefinition.value?.default_unit || '')
const scoreProfileValidationErrors = computed(() => {
  const errors: string[] = []
  const trimmedName = scoreProfileForm.name.trim()
  if (!trimmedName) errors.push('请输入模板名称。')
  if (!scoreProfileForm.dimensions.length) errors.push('至少需要保留 1 个能力维度。')

  const dimensionNames = new Set<string>()
  scoreProfileForm.dimensions.forEach((dimension, dimensionIndex) => {
    const dimensionLabel = `能力维度 ${dimensionIndex + 1}`
    const trimmedDimensionName = dimension.name.trim()
    if (!trimmedDimensionName) {
      errors.push(`${dimensionLabel} 未填写维度名称。`)
    } else if (dimensionNames.has(trimmedDimensionName)) {
      errors.push(`能力维度名称“${trimmedDimensionName}”重复，请修改。`)
    } else {
      dimensionNames.add(trimmedDimensionName)
    }

    if (!dimension.metrics.length) {
      errors.push(`${dimensionLabel} 至少需要 1 个测试项目。`)
      return
    }

    const metricIds = new Set<number>()
    dimension.metrics.forEach((metric, metricIndex) => {
      const metricLabel = `${dimensionLabel} 的测试项目 ${metricIndex + 1}`
      if (!metric.test_metric_definition_id) {
        errors.push(`${metricLabel} 还未选择测试项目。`)
        return
      }
      if (metricIds.has(metric.test_metric_definition_id)) {
        errors.push(`${dimensionLabel} 中存在重复测试项目，请调整。`)
        return
      }
      metricIds.add(metric.test_metric_definition_id)
    })
  })

  return Array.from(new Set(errors))
})
const canSubmitScoreProfile = computed(
  () => scoreProfileValidationErrors.value.length === 0,
)

async function hydrate() {
  loading.value = true
  try {
    const [athleteData, sportData, teamData, recordData, catalog, scoreProfileData] = await Promise.all([
      fetchAthletes(),
      fetchSports(),
      fetchTeams(),
      fetchAllTestRecords(),
      fetchTestDefinitions(),
      fetchScoreProfiles(),
    ])
    athletes.value = athleteData
    sports.value = sportData
    teams.value = teamData
    records.value = recordData
    definitions.value = catalog.types || []
    scoreProfiles.value = scoreProfileData
    syncTrendFilterSelection({
      preferredAthleteId: trendFilters.athleteId,
      preferredTypeName: trendFilters.testType,
      preferredMetricName: trendFilters.metricName,
    })
    syncScoreSelection()
  } finally {
    loading.value = false
    await nextTick()
    renderChart()
    renderScoreCharts()
  }
}

function buildLibraryQuery(page = 1) {
  return {
    athlete_keyword: libraryFilters.athleteKeyword.trim() || undefined,
    metric_keyword: libraryFilters.metricKeyword.trim() || undefined,
    test_type: libraryFilters.testType || undefined,
    page,
    page_size: DEFAULT_LIBRARY_PAGE_SIZE,
  }
}

async function loadLibraryPage(page = 1, options?: { append?: boolean }) {
  const append = Boolean(options?.append && page > 1)
  if (append) libraryLoadingMore.value = true
  else libraryLoading.value = true
  libraryError.value = ''

  try {
    const response = await fetchTestRecords(buildLibraryQuery(page))
    libraryState.total = response.total
    libraryState.page = response.page
    libraryState.page_size = response.page_size
    libraryState.total_pages = response.total_pages
    libraryState.items = append ? [...libraryState.items, ...response.items] : response.items
  } catch (error) {
    libraryError.value = extractErrorMessage(error, '测试数据总库加载失败，请稍后重试。')
  } finally {
    libraryLoading.value = false
    libraryLoadingMore.value = false
  }
}

async function resetAndLoadLibrary() {
  libraryState.items = []
  libraryState.total = 0
  libraryState.page = 1
  libraryState.page_size = DEFAULT_LIBRARY_PAGE_SIZE
  libraryState.total_pages = 0
  await loadLibraryPage(1)
}

async function loadMoreLibraryRecords() {
  if (libraryLoading.value || libraryLoadingMore.value || !libraryHasMore.value) return
  await loadLibraryPage(libraryPage.value + 1, { append: true })
}

async function handleLibraryScroll() {
  const element = libraryTableRef.value
  if (!element) return
  const distanceToBottom = element.scrollHeight - element.scrollTop - element.clientHeight
  if (distanceToBottom > LIBRARY_SCROLL_THRESHOLD) return
  await loadMoreLibraryRecords()
}

async function refreshDefinitions(options?: {
  preferredTypeName?: string
  preferredMetricName?: string
}) {
  const [catalog, profileData] = await Promise.all([fetchTestDefinitions(), fetchScoreProfiles()])
  definitions.value = catalog.types || []
  scoreProfiles.value = profileData
  syncTrendFilterSelection({
    preferredAthleteId: trendFilters.athleteId,
    preferredTypeName: options?.preferredTypeName ?? trendFilters.testType,
    preferredMetricName: options?.preferredMetricName ?? trendFilters.metricName,
  })
  syncScoreSelection()
  await nextTick()
  renderChart()
  renderScoreCharts()
}

function syncTrendFilterSelection(options?: {
  preferredSportId?: number
  preferredTeamId?: number
  preferredAthleteId?: number
  preferredTypeName?: string
  preferredMetricName?: string
}) {
  const preferredSportId = options?.preferredSportId ?? trendFilters.sportId
  const resolvedSports = collectTrendSportOptions()
  trendFilters.sportId = preferredSportId && resolvedSports.some((item) => item.id === preferredSportId) ? preferredSportId : 0

  const preferredTeamId = options?.preferredTeamId ?? trendFilters.teamId
  const resolvedTeams = collectTrendTeamOptions(trendFilters.sportId)
  trendFilters.teamId = preferredTeamId && resolvedTeams.some((item) => item.id === preferredTeamId) ? preferredTeamId : 0

  const preferredAthleteId = options?.preferredAthleteId ?? 0
  const resolvedAthletes = collectTrendAthletes(trendFilters.sportId, trendFilters.teamId)
  if (preferredAthleteId && resolvedAthletes.some((item) => item.id === preferredAthleteId)) {
    trendFilters.athleteId = preferredAthleteId
  } else {
    trendFilters.athleteId = resolvedAthletes[0]?.id ?? 0
  }

  const defaultType =
    definitions.value.find((item) => item.metrics.length > 0) ||
    definitions.value[0] ||
    null
  const resolvedType =
    definitions.value.find((item) => item.name === options?.preferredTypeName) || defaultType

  trendFilters.testType = resolvedType?.name || ''

  const resolvedMetric =
    resolvedType?.metrics.find((item) => item.name === options?.preferredMetricName) ||
    resolvedType?.metrics[0] ||
    null

  trendFilters.metricName = resolvedMetric?.name || ''
  syncEntryFormContext({ resetValues: false, resetUnit: true })
}

function syncScoreSelection() {
  if (scoreFilters.teamId && teams.value.some((item) => item.id === scoreFilters.teamId)) {
    // keep
  } else {
    scoreFilters.teamId = teams.value[0]?.id || 0
  }

  if (scoreFilters.scoreProfileId && scoreProfiles.value.some((item) => item.id === scoreFilters.scoreProfileId)) {
    // keep
  } else {
    scoreFilters.scoreProfileId = scoreProfiles.value[0]?.id || 0
  }
}

function openScoreProfileManager() {
  scoreProfileError.value = ''
  scoreProfileManagerOpen.value = true
  if (!editingScoreProfileId.value) resetScoreProfileForm()
}

function closeScoreProfileManager() {
  scoreProfileManagerOpen.value = false
  scoreProfileError.value = ''
  resetScoreProfileForm()
}

function resetScoreProfileForm() {
  editingScoreProfileId.value = null
  scoreProfileForm.name = ''
  scoreProfileForm.notes = ''
  scoreProfileForm.is_active = true
  scoreProfileForm.dimensions = [buildEmptyScoreDimension()]
}

function buildEmptyScoreDimension(): ScoreDimensionWrite {
  return {
    id: null,
    name: '',
    sort_order: scoreProfileForm.dimensions.length + 1,
    weight: 1,
    metrics: [],
  }
}

function buildEmptyScoreMetric(sortOrder: number) {
  return {
    id: null,
    test_metric_definition_id: 0,
    weight: 1,
    sort_order: sortOrder,
  }
}

function startEditScoreProfile(profile: ScoreProfileRead) {
  editingScoreProfileId.value = profile.id
  scoreProfileForm.name = profile.name
  scoreProfileForm.notes = profile.notes || ''
  scoreProfileForm.is_active = profile.is_active
  scoreProfileForm.dimensions = profile.dimensions.map((dimension, dimensionIndex) => ({
    id: dimension.id,
    name: dimension.name,
    sort_order: dimension.sort_order || dimensionIndex + 1,
    weight: dimension.weight,
    metrics: dimension.metrics.map((metric, metricIndex) => ({
      id: metric.id,
      test_metric_definition_id: metric.test_metric_definition_id,
      weight: metric.weight,
      sort_order: metric.sort_order || metricIndex + 1,
    })),
  }))
  openScoreProfileManager()
}

function addScoreDimension() {
  scoreProfileForm.dimensions.push(buildEmptyScoreDimension())
}

function removeScoreDimension(index: number) {
  scoreProfileForm.dimensions.splice(index, 1)
  if (!scoreProfileForm.dimensions.length) scoreProfileForm.dimensions.push(buildEmptyScoreDimension())
}

function addScoreMetric(dimensionIndex: number) {
  const metrics = scoreProfileForm.dimensions[dimensionIndex].metrics
  metrics.push(buildEmptyScoreMetric(metrics.length + 1))
}

function removeScoreMetric(dimensionIndex: number, metricIndex: number) {
  scoreProfileForm.dimensions[dimensionIndex].metrics.splice(metricIndex, 1)
}

function normalizeDimensionWeights(metrics: Array<{ weight: number }>) {
  const total = metrics.reduce((sum, item) => sum + Number(item.weight || 0), 0)
  if (!total) return
  metrics.forEach((item) => {
    item.weight = Number((Number(item.weight || 0) / total).toFixed(4))
  })
}

function equalizeDimensionWeights(metrics: Array<{ weight: number }>) {
  if (!metrics.length) return
  const nextWeight = Number((1 / metrics.length).toFixed(4))
  metrics.forEach((item) => {
    item.weight = nextWeight
  })
}

async function submitScoreProfile() {
  if (!canSubmitScoreProfile.value) {
    scoreProfileError.value = '请完善评分模板名称、能力维度和测试项目。'
    return
  }
  scoreSubmitting.value = true
  scoreProfileError.value = ''
  try {
    const payload = {
      name: scoreProfileForm.name.trim(),
      notes: scoreProfileForm.notes.trim() || null,
      is_active: scoreProfileForm.is_active,
      dimensions: scoreProfileForm.dimensions.map((dimension, dimensionIndex) => ({
        id: dimension.id || undefined,
        name: dimension.name.trim(),
        sort_order: dimensionIndex + 1,
        weight: dimension.weight || 1,
        metrics: dimension.metrics
          .filter((metric) => metric.test_metric_definition_id)
          .map((metric, metricIndex) => ({
            id: metric.id || undefined,
            test_metric_definition_id: metric.test_metric_definition_id,
            weight: metric.weight || 1,
            sort_order: metricIndex + 1,
          })),
      })),
    }
    if (editingScoreProfileId.value) {
      await updateScoreProfile(editingScoreProfileId.value, payload)
    } else {
      await createScoreProfile(payload)
    }
    await refreshDefinitions()
    closeScoreProfileManager()
  } catch (error) {
    scoreProfileError.value = extractErrorMessage(error, '保存评分模板失败，请稍后重试。')
  } finally {
    scoreSubmitting.value = false
  }
}

async function removeScoreProfile(profile: ScoreProfileRead) {
  const confirmed = confirmDangerousAction({
    title: '删除评分模板',
    impactLines: [
      `模板名称：${profile.name}`,
      `能力维度数：${profile.dimensions.length}`,
      '删除后该模板配置将不可直接恢复。',
    ],
  })
  if (!confirmed) return
  try {
    await deleteScoreProfile(profile.id, { confirmed: true, actor_name: '管理模式' })
    await refreshDefinitions()
  } catch (error) {
    scoreProfileError.value = extractErrorMessage(error, '删除评分模板失败，请稍后重试。')
  }
}

async function calculateScores() {
  if (!scoreFilters.scoreProfileId || !scoreFilters.teamId) {
    actionMessage.value = '请先选择评分模板和队伍。'
    return
  }
  const resolvedDateFrom = scoreFilters.dateFrom || scoreTeamDateRange.value?.from || ''
  const resolvedDateTo = scoreFilters.dateTo || scoreTeamDateRange.value?.to || ''
  if (!resolvedDateFrom || !resolvedDateTo) {
    actionMessage.value = '当前队伍没有可用于评分的测试日期数据。'
    return
  }
  scoreCalculationLoading.value = true
  try {
    scoreCalculation.value = await calculateTestScores({
      score_profile_id: scoreFilters.scoreProfileId,
      team_id: scoreFilters.teamId,
      date_from: resolvedDateFrom,
      date_to: resolvedDateTo,
      baseline_mode: scoreFilters.baselineMode,
    })
    selectedScoreAthleteId.value = scoreCalculation.value.ranking[0]?.athlete_id || 0
    await nextTick()
    renderScoreCharts()
  } catch (error) {
    actionMessage.value = extractErrorMessage(error, '测试评分计算失败，请稍后重试。')
  } finally {
    scoreCalculationLoading.value = false
  }
}

function queueAutoCalculateScores() {
  if (scoreAutoCalculateTimer !== null) {
    window.clearTimeout(scoreAutoCalculateTimer)
  }

  if (!scoreFilters.scoreProfileId || !scoreFilters.teamId) {
    scoreCalculation.value = null
    return
  }

  scoreAutoCalculateTimer = window.setTimeout(() => {
    scoreAutoCalculateTimer = null
    void calculateScores()
  }, 250)
}

function buildScoreRadarRange() {
  const allScores = [
    ...(scoreCalculation.value?.ranking.flatMap((athlete) =>
      athlete.dimension_scores
        .map((dimension) => dimension.score)
        .filter((score): score is number => typeof score === 'number'),
    ) || []),
    ...(scoreCalculation.value?.team_average_dimensions
      .map((dimension) => dimension.score)
      .filter((score): score is number => typeof score === 'number') || []),
  ]
  const minValue = Math.min(...allScores, 40)
  const maxValue = Math.max(...allScores, 60)
  const padding = Math.max((maxValue - minValue) * 0.1, 5)
  const indicatorMin = Math.floor(minValue - padding)
  const indicatorMax = Math.ceil(maxValue + padding)
  return { min: indicatorMin, max: indicatorMax }
}

function buildRadarIndicators(source: Array<{ dimension_name: string; score?: number | null }>) {
  const range = buildScoreRadarRange()
  return {
    min: range.min,
    max: range.max,
    indicator: source.map((item) => ({ name: item.dimension_name, min: range.min, max: range.max })),
  }
}

function renderScoreCharts() {
  if (selectedScoreAthlete.value && scoreRadarRef.value) {
    const athleteDimensions = selectedScoreAthlete.value.dimension_scores.map((item) => ({
      dimension_name: item.dimension_name,
      score: item.score,
    }))
    const teamDimensionMap = new Map(
      (scoreCalculation.value?.team_average_dimensions || []).map((item) => [item.dimension_name, item.score]),
    )
    const radar = buildRadarIndicators(athleteDimensions)
    scoreRadarChart ||= echarts.init(scoreRadarRef.value)
    scoreRadarChart.setOption({
      tooltip: { trigger: 'item' },
      legend: {
        bottom: 0,
        data: [selectedScoreAthlete.value.athlete_name, '团队平均'],
      },
      radar: {
        indicator: radar.indicator,
        radius: '60%',
        center: ['50%', '48%'],
        scale: true,
      },
      series: [
        {
          type: 'radar',
          data: [
            {
              value: athleteDimensions.map((item) => Number(item.score ?? radar.min)),
              name: selectedScoreAthlete.value.athlete_name,
              areaStyle: { color: 'rgba(15,118,110,0.18)' },
              lineStyle: { color: '#0f766e' },
              itemStyle: { color: '#0f766e' },
            },
            {
              value: athleteDimensions.map((item) => Number(teamDimensionMap.get(item.dimension_name) ?? radar.min)),
              name: '团队平均',
              areaStyle: { color: 'rgba(245,158,11,0.12)' },
              lineStyle: { color: '#f59e0b' },
              itemStyle: { color: '#f59e0b' },
            },
          ],
        },
      ],
    })
  } else if (scoreRadarChart) {
    scoreRadarChart.clear()
  }
}

function syncEntryFormContext(options?: { resetValues?: boolean; resetUnit?: boolean }) {
  if (options?.resetValues) {
    entryForm.testDate = todayString()
    entryForm.resultValue = 0
    entryForm.resultText = ''
    entryForm.notes = ''
  }
  if (options?.resetUnit) {
    entryForm.unit = selectedMetricDefinition.value?.default_unit || ''
  }
}

function toggleEntryPanel() {
  entryPanelOpen.value = !entryPanelOpen.value
  if (entryPanelOpen.value) {
    syncEntryFormContext({ resetValues: false, resetUnit: true })
  }
}

async function submitEntryRecord() {
  if (!canSubmitEntryRecord.value) {
    actionMessage.value = '请先选择测试类型、测试项目和单位。'
    return
  }

  try {
    await createTestRecord({
      athlete_id: trendFilters.athleteId,
      test_date: entryForm.testDate,
      test_type: trendFilters.testType,
      metric_name: trendFilters.metricName,
      result_value: entryForm.resultValue,
      unit: entryActiveUnit.value,
      result_text: entryForm.resultText || null,
      notes: entryForm.notes || null,
    })
    actionMessage.value = '测试记录已保存。'
    await hydrate()
    syncEntryFormContext({ resetValues: true, resetUnit: true })
  } catch (error) {
    actionMessage.value = extractErrorMessage(error, '保存测试记录失败，请稍后重试。')
  }
}

async function handleTemplateDownload() {
  templateBusy.value = true
  actionMessage.value = ''
  try {
    const blob = await downloadTestRecordTemplate()
    downloadBlob(blob, 'test-record-import-template.xlsx')
    actionMessage.value = '导入模板已下载。'
  } finally {
    templateBusy.value = false
  }
}

async function handleLibraryExport() {
  exportBusy.value = true
  actionMessage.value = ''
  try {
    const blob = await exportTestRecordLibrary()
    downloadBlob(blob, 'test-record-library.xlsx')
    actionMessage.value = '测试数据总库已导出。'
  } finally {
    exportBusy.value = false
  }
}

async function handleImport(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  importBusy.value = true
  actionMessage.value = ''
  try {
    const summary = await importTestRecords(file)
    actionMessage.value = `导入完成：共 ${summary.total_rows} 行，新增 ${summary.imported_rows} 行，跳过 ${summary.skipped_rows} 行重复数据。`
    await hydrate()
    await resetAndLoadLibrary()
  } catch (error) {
    actionMessage.value = extractErrorMessage(error)
  } finally {
    importBusy.value = false
    input.value = ''
  }
}

function triggerImport() {
  importInputRef.value?.click()
}

async function handleDeleteFilteredBatch() {
  if (!hasLibraryFilters.value) {
    actionMessage.value = '请先筛选出要删除的测试批次，再执行删除。'
    return
  }
  if (!libraryTotal.value) {
    actionMessage.value = '当前筛选条件下没有可删除的测试数据。'
    return
  }

  const confirmed = confirmDangerousAction({
    title: '批量删除测试数据',
    impactLines: [
      `将删除当前筛选结果 ${libraryTotal.value} 条`,
      `筛选条件：${libraryFilters.athleteKeyword || '全部运动员'} / ${libraryFilters.metricKeyword || '全部项目'} / ${libraryFilters.testType || '全部类型'}`,
    ],
  })
  if (!confirmed) return

  try {
    const result = await deleteFilteredTestRecords(
      {
        athlete_keyword: libraryFilters.athleteKeyword.trim() || undefined,
        metric_keyword: libraryFilters.metricKeyword.trim() || undefined,
        test_type: libraryFilters.testType || undefined,
      },
      { confirmed: true, actor_name: '管理模式' },
    )
    actionMessage.value = `已删除 ${result.deleted_count} 条测试数据。`
    await hydrate()
    await resetAndLoadLibrary()
  } catch (error) {
    actionMessage.value = extractErrorMessage(error)
  }
}

function handleTrendTestTypeChange() {
  const nextMetric =
    selectedTypeDefinition.value?.metrics.find((item) => item.name === trendFilters.metricName) ||
    selectedTypeDefinition.value?.metrics[0] ||
    null
  trendFilters.metricName = nextMetric?.name || ''
  syncEntryFormContext({ resetValues: false, resetUnit: true })
}

function handleTrendSportChange() {
  const availableTeams = collectTrendTeamOptions(trendFilters.sportId)
  if (trendFilters.teamId && !availableTeams.some((item) => item.id === trendFilters.teamId)) {
    trendFilters.teamId = 0
  }

  const nextAthletes = collectTrendAthletes(trendFilters.sportId, trendFilters.teamId)
  if (trendFilters.athleteId && !nextAthletes.some((item) => item.id === trendFilters.athleteId)) {
    trendFilters.athleteId = nextAthletes[0]?.id ?? 0
  } else if (!trendFilters.athleteId) {
    trendFilters.athleteId = nextAthletes[0]?.id ?? 0
  }
}

function handleTrendTeamChange() {
  const nextAthletes = collectTrendAthletes(trendFilters.sportId, trendFilters.teamId)
  if (trendFilters.athleteId && !nextAthletes.some((item) => item.id === trendFilters.athleteId)) {
    trendFilters.athleteId = nextAthletes[0]?.id ?? 0
  } else if (!trendFilters.athleteId) {
    trendFilters.athleteId = nextAthletes[0]?.id ?? 0
  }
}

function handleTrendMetricChange() {
  const scopedMetric = availableMetricDefinitions.value.find((item) => item.name === trendFilters.metricName)
  if (scopedMetric) {
    trendFilters.metricName = scopedMetric.name
    syncEntryFormContext({ resetValues: false, resetUnit: true })
    return
  }

  const metric = metricDefinitions.value.find((item) => item.name === trendFilters.metricName)
  if (!metric) return

  trendFilters.testType = metric.test_type_name
  trendFilters.metricName = metric.name
  syncEntryFormContext({ resetValues: false, resetUnit: true })
}

function openTypeManager() {
  typeManagerError.value = ''
  typeManagerOpen.value = true
  if (!editingTypeId.value && authStore.isAdmin) {
    typeForm.sport_id = null
  }
}

function closeTypeManager() {
  typeManagerOpen.value = false
  typeManagerError.value = ''
  resetTypeForm()
}

function openMetricManager() {
  metricManagerError.value = ''
  metricManagerOpen.value = true
  metricForm.test_type_id = resolvePreferredTypeId()
}

function closeMetricManager() {
  metricManagerOpen.value = false
  metricManagerError.value = ''
  resetMetricForm()
}

function startEditType(definition: TestTypeDefinitionRead) {
  if (!canEditType(definition)) {
    typeManagerError.value = '系统测试类型仅管理员可维护'
    return
  }
  editingTypeId.value = definition.id
  typeForm.name = definition.name
  typeForm.sport_id = definition.sport_id ?? null
  typeForm.notes = definition.notes || ''
  typeManagerError.value = ''
}

function startEditMetric(definition: ManagedMetricDefinition) {
  if (!canEditMetric(definition)) {
    metricManagerError.value = '系统测试项目仅管理员可维护'
    return
  }
  editingMetricId.value = definition.id
  metricForm.test_type_id = definition.test_type_id
  metricForm.name = definition.name
  metricForm.default_unit = definition.default_unit || ''
  metricForm.is_lower_better = definition.is_lower_better
  metricForm.notes = definition.notes || ''
  metricManagerError.value = ''
}

async function submitType() {
  typeManagerError.value = ''
  if (!canSubmitType.value) {
    typeManagerError.value = '测试类型名称不能为空'
    return
  }

  typeSubmitting.value = true
  try {
    const payload = {
      name: typeForm.name.trim(),
      code: resolveTypeCode(),
      notes: normalizeOptionalText(typeForm.notes),
      ...(editingTypeId.value ? {} : { sport_id: authStore.isAdmin ? typeForm.sport_id : undefined }),
    }
    const saved = editingTypeId.value
      ? await updateTestTypeDefinition(editingTypeId.value, payload)
      : await createTestTypeDefinition(payload)
    await refreshDefinitions({ preferredTypeName: saved.name })
    resetTypeForm()
  } catch (error) {
    typeManagerError.value = extractErrorMessage(error, '保存测试类型失败，请稍后重试。')
  } finally {
    typeSubmitting.value = false
  }
}

async function submitMetric() {
  metricManagerError.value = ''
  if (metricForm.test_type_id === null) {
    metricManagerError.value = '请先选择所属测试类型'
    return
  }
  if (!metricForm.name.trim()) {
    metricManagerError.value = '测试项目名称不能为空'
    return
  }

  metricSubmitting.value = true
  try {
    const selectedType = editableTypeDefinitions.value.find((item) => item.id === metricForm.test_type_id)
    if (!selectedType) {
      metricManagerError.value = authStore.isAdmin ? '请选择所属测试类型' : '队伍账号只能在本队自建测试类型下维护测试项目'
      return
    }
    const payload = {
      test_type_id: metricForm.test_type_id,
      name: metricForm.name.trim(),
      code: resolveMetricCode(),
      default_unit: normalizeOptionalText(metricForm.default_unit),
      is_lower_better: metricForm.is_lower_better,
      notes: normalizeOptionalText(metricForm.notes),
    }
    const saved = editingMetricId.value
      ? await updateTestMetricDefinition(editingMetricId.value, payload)
      : await createTestMetricDefinition(payload)
    await refreshDefinitions({
      preferredTypeName: saved.test_type?.name || trendFilters.testType,
      preferredMetricName: saved.name,
    })
    resetMetricForm()
    metricForm.test_type_id = resolvePreferredTypeId()
  } catch (error) {
    metricManagerError.value = extractErrorMessage(error, '保存测试项目失败，请稍后重试。')
  } finally {
    metricSubmitting.value = false
  }
}

async function removeType(definition: TestTypeDefinitionRead) {
  if (!canEditType(definition)) {
    typeManagerError.value = '系统测试类型仅管理员可维护'
    return
  }
  const confirmed = confirmDangerousAction({
    title: '删除测试类型',
    impactLines: [
      `测试类型：${definition.name}`,
      `当前挂接测试项目：${definition.metrics.length} 个`,
      '删除定义不会删除历史测试记录，但会移除后续录入可选项。',
    ],
    recommendation: '如果该类型下仍有测试项目，请先调整或删除这些测试项目，再删除测试类型。',
  })
  if (!confirmed) return

  deletingTypeId.value = definition.id
  typeManagerError.value = ''
  try {
    await deleteTestTypeDefinition(definition.id, { confirmed: true, actor_name: '管理模式' })
    await refreshDefinitions()
    if (editingTypeId.value === definition.id) {
      resetTypeForm()
    }
  } catch (error) {
    typeManagerError.value = extractErrorMessage(error, '删除测试类型失败，请稍后重试。')
  } finally {
    deletingTypeId.value = null
  }
}

async function removeMetric(definition: ManagedMetricDefinition) {
  if (!canEditMetric(definition)) {
    metricManagerError.value = '系统测试项目仅管理员可维护'
    return
  }
  const confirmed = confirmDangerousAction({
    title: '删除测试项目',
    impactLines: [
      `测试项目：${definition.name}`,
      `所属测试类型：${definition.test_type_name}`,
      '删除定义不会删除历史测试记录，但会移除后续录入可选项。',
    ],
  })
  if (!confirmed) return

  deletingMetricId.value = definition.id
  metricManagerError.value = ''
  try {
    await deleteTestMetricDefinition(definition.id, { confirmed: true, actor_name: '管理模式' })
    await refreshDefinitions()
    if (editingMetricId.value === definition.id) {
      resetMetricForm()
      metricForm.test_type_id = resolvePreferredTypeId()
    }
  } catch (error) {
    metricManagerError.value = extractErrorMessage(error, '删除测试项目失败，请稍后重试。')
  } finally {
    deletingMetricId.value = null
  }
}

function resetTypeForm() {
  editingTypeId.value = null
  typeForm.name = ''
  typeForm.sport_id = null
  typeForm.notes = ''
}

function resetMetricForm() {
  editingMetricId.value = null
  metricForm.test_type_id = null
  metricForm.name = ''
  metricForm.default_unit = ''
  metricForm.is_lower_better = false
  metricForm.notes = ''
}

function resolvePreferredTypeId() {
  return (
    editableTypeDefinitions.value.find((item) => item.id === selectedTypeDefinition.value?.id)?.id ||
    editableTypeDefinitions.value.find((item) => item.metrics.length > 0)?.id ||
    editableTypeDefinitions.value[0]?.id ||
    null
  )
}

function canEditType(definition: TestTypeDefinitionRead) {
  return authStore.isAdmin || !definition.is_system
}

function canEditMetric(definition: ManagedMetricDefinition) {
  return authStore.isAdmin || !definition.is_system
}

function resolveDefinitionScopeLabel(definition: { is_system: boolean; sport_name?: string | null }) {
  if (definition.is_system) return '系统项目'
  return definition.sport_name ? `${definition.sport_name} / 本项目` : '本项目'
}

function resolveTypeCode() {
  const current = definitions.value.find((item) => item.id === editingTypeId.value)
  if (current && current.name.trim() === typeForm.name.trim()) {
    return current.code
  }
  return buildDefinitionCode(typeForm.name, 'test-type')
}

function resolveMetricCode() {
  const current = metricDefinitions.value.find((item) => item.id === editingMetricId.value)
  if (current && current.name.trim() === metricForm.name.trim()) {
    return current.code
  }
  return buildDefinitionCode(metricForm.name, 'test-metric')
}

function buildDefinitionCode(name: string, prefix: 'test-type' | 'test-metric') {
  const asciiSlug = name
    .trim()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40)

  if (asciiSlug) return asciiSlug
  return `${prefix}-${Date.now()}`
}

function normalizeOptionalText(value: string) {
  const normalized = value.trim()
  return normalized || null
}

function computeRelativeStrength(record: TestRecord) {
  const athleteWeight = record.athlete?.weight
  if (!ratioMetrics.has(record.metric_name) || !athleteWeight) return null
  return Number(record.result_value / athleteWeight).toFixed(2)
}

function resolveAthleteSportId(athlete: Athlete | null | undefined) {
  return athlete?.sport_id ?? athlete?.sport?.id ?? null
}

function resolveAthleteTeamId(athlete: Athlete | null | undefined) {
  return athlete?.team_id ?? athlete?.team?.id ?? null
}

function resolveRecordAthlete(record: TestRecord) {
  return record.athlete || athleteLookup.value.get(record.athlete_id) || null
}

function collectTrendSportOptions() {
  return Array.from(
    athletes.value.reduce((accumulator, athlete) => {
      const sportId = resolveAthleteSportId(athlete)
      const sportName = athlete.sport?.name?.trim()
      if (!sportId || !sportName || accumulator.has(sportId)) return accumulator
      accumulator.set(sportId, { id: sportId, name: sportName })
      return accumulator
    }, new Map<number, { id: number; name: string }>()),
  )
    .map(([, value]) => value)
    .sort((left, right) => left.name.localeCompare(right.name, 'zh-CN'))
}

function collectTrendTeamOptions(sportId = 0) {
  return Array.from(
    athletes.value.reduce((accumulator, athlete) => {
      const resolvedSportId = resolveAthleteSportId(athlete)
      const teamId = resolveAthleteTeamId(athlete)
      const teamName = athlete.team?.name?.trim()
      if (sportId && resolvedSportId !== sportId) return accumulator
      if (!teamId || !teamName || accumulator.has(teamId)) return accumulator
      accumulator.set(teamId, { id: teamId, sport_id: resolvedSportId ?? 0, name: teamName })
      return accumulator
    }, new Map<number, { id: number; sport_id: number; name: string }>()),
  )
    .map(([, value]) => value)
    .sort((left, right) => left.name.localeCompare(right.name, 'zh-CN'))
}

function collectTrendAthletes(sportId = 0, teamId = 0) {
  return athletes.value.filter((athlete) => {
    if (sportId && resolveAthleteSportId(athlete) !== sportId) return false
    if (teamId && resolveAthleteTeamId(athlete) !== teamId) return false
    return true
  })
}

function recordMatchesTrendScope(record: TestRecord, options?: { includeAthlete?: boolean }) {
  const athlete = resolveRecordAthlete(record)
  if (trendFilters.sportId && resolveAthleteSportId(athlete) !== trendFilters.sportId) return false
  if (trendFilters.teamId && resolveAthleteTeamId(athlete) !== trendFilters.teamId) return false
  if (options?.includeAthlete !== false && trendFilters.athleteId && record.athlete_id !== trendFilters.athleteId) return false
  if (trendFilters.dateFrom && record.test_date < trendFilters.dateFrom) return false
  if (trendFilters.dateTo && record.test_date > trendFilters.dateTo) return false
  return true
}

function displayResult(record: TestRecord) {
  if (record.result_text) return record.result_text
  return `${record.result_value} ${record.unit}`
}

function renderChart() {
  if (!chartRef.value) return
  chart ||= echarts.init(chartRef.value)

  const isLowerBetterMetric = selectedMetricDirectionMeta.value.isLowerBetter
  const athleteData = new Map<string, number>(filteredTrendRecords.value.map((item) => [item.test_date, Number(item.result_value)]))
  const averageData = new Map<string, number>(teamRangeMetricRecords.value.map((item) => [item.test_date, item.average_value]))
  const minData = new Map<string, number>(teamRangeMetricRecords.value.map((item) => [item.test_date, item.min_value]))
  const maxData = new Map<string, number>(teamRangeMetricRecords.value.map((item) => [item.test_date, item.max_value]))
  const bandUpperData = isLowerBetterMetric ? minData : maxData
  const bandLowerData = isLowerBetterMetric ? maxData : minData

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: Array<{ axisValueLabel: string }>) => {
        const axisLabel = params?.[0]?.axisValueLabel || ''
        const unit = chartMetricUnit.value
        return [
          axisLabel,
          `个人成绩：${formatTooltipValue(athleteData.get(axisLabel))} ${unit}`.trim(),
          `全队平均：${formatTooltipValue(averageData.get(axisLabel))} ${unit}`.trim(),
          `全队最高：${formatTooltipValue(maxData.get(axisLabel))} ${unit}`.trim(),
          `全队最低：${formatTooltipValue(minData.get(axisLabel))} ${unit}`.trim(),
        ].join('<br/>')
      },
    },
    legend: { data: ['个人成绩', '全队平均', '全队区间'] },
    grid: { left: 56, right: 24, top: 48, bottom: 32 },
    xAxis: { type: 'category', data: chartDates.value },
    yAxis: {
      type: 'value',
      name: chartMetricUnit.value,
      inverse: isLowerBetterMetric,
      ...(isLowerBetterMetric ? { min: 0 } : {}),
    },
    series: [
      {
        type: 'custom',
        name: '全队区间',
        data: [0],
        silent: true,
        tooltip: { show: false },
        renderItem: (_params: unknown, api: any) => {
          const upperPoints = chartDates.value
            .map((dateLabel, index) => {
              const value = bandUpperData.get(dateLabel)
              return value == null ? null : api.coord([index, value])
            })
            .filter(Boolean)
          const lowerPoints = chartDates.value
            .slice()
            .reverse()
            .map((dateLabel) => {
              const value = bandLowerData.get(dateLabel)
              if (value == null) return null
              const index = chartDates.value.indexOf(dateLabel)
              return api.coord([index, value])
            })
            .filter(Boolean)

          if (upperPoints.length === 1 && lowerPoints.length === 1) {
            const [upperX, upperY] = upperPoints[0] as [number, number]
            const [, lowerY] = lowerPoints[0] as [number, number]
            const bandHalfWidth = 14

            return {
              type: 'rect',
              shape: {
                x: upperX - bandHalfWidth,
                y: Math.min(upperY, lowerY),
                width: bandHalfWidth * 2,
                height: Math.max(Math.abs(lowerY - upperY), 2),
              },
              style: { fill: 'rgba(245,158,11,0.34)' },
            }
          }

          if (upperPoints.length < 2 || lowerPoints.length < 2) return null
          return {
            type: 'polygon',
            shape: { points: [...upperPoints, ...lowerPoints] },
            style: { fill: 'rgba(245,158,11,0.34)' },
          }
        },
      },
      {
        type: 'line',
        smooth: true,
        name: '__max__',
        data: chartDates.value.map((dateLabel) => maxData.get(dateLabel) ?? null),
        lineStyle: { color: 'rgba(245,158,11,0.88)', width: 2 },
        itemStyle: { color: 'rgba(245,158,11,0.96)', borderColor: '#ffffff', borderWidth: 1 },
        symbol: 'circle',
        symbolSize: 8,
        tooltip: { show: false },
        emphasis: { disabled: true },
        connectNulls: false,
      },
      {
        type: 'line',
        smooth: true,
        name: '__min__',
        data: chartDates.value.map((dateLabel) => minData.get(dateLabel) ?? null),
        lineStyle: { color: 'rgba(245,158,11,0.88)', width: 2 },
        itemStyle: { color: 'rgba(245,158,11,0.96)', borderColor: '#ffffff', borderWidth: 1 },
        symbol: 'circle',
        symbolSize: 8,
        tooltip: { show: false },
        emphasis: { disabled: true },
        connectNulls: false,
      },
      {
        type: 'line',
        smooth: true,
        name: '全队平均',
        data: chartDates.value.map((dateLabel) => averageData.get(dateLabel) ?? null),
        lineStyle: { color: '#f59e0b', width: 2.5, type: 'dashed' },
        itemStyle: { color: '#f59e0b' },
        symbolSize: 6,
        connectNulls: false,
        z: 4,
      },
      {
        type: 'line',
        smooth: true,
        name: '个人成绩',
        data: chartDates.value.map((dateLabel) => athleteData.get(dateLabel) ?? null),
        lineStyle: { color: '#0f766e', width: 3 },
        itemStyle: { color: '#0f766e' },
        symbolSize: 7,
        connectNulls: false,
        z: 5,
      },
    ],
  })
}

function extractErrorMessage(error: unknown, fallback = '操作失败，请稍后重试。') {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (Array.isArray(detail)) return detail.join('；')
    if (typeof detail === 'string') return detail
    if (error.message) return error.message
  }
  return fallback
}

function formatTooltipValue(value: unknown) {
  if (value == null || value === '') return '--'
  return value
}

function formatScoreDisplay(value: number | null | undefined) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '--'
  return value.toFixed(1)
}

function getRankMedal(rankIndex: number) {
  if (rankIndex === 0) return '🥇'
  if (rankIndex === 1) return '🥈'
  if (rankIndex === 2) return '🥉'
  return ''
}

function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  anchor.remove()
  window.URL.revokeObjectURL(url)
}

watch(
  () => [libraryFilters.athleteKeyword, libraryFilters.metricKeyword, libraryFilters.testType],
  () => {
    void resetAndLoadLibrary()
  },
)

watch(
  () => selectedScoreAthleteId.value,
  async () => {
    await nextTick()
    renderScoreCharts()
  },
)

watch(
  () => [
    scoreFilters.scoreProfileId,
    scoreFilters.teamId,
    scoreFilters.baselineMode,
    scoreFilters.dateFrom,
    scoreFilters.dateTo,
  ],
  () => {
    queueAutoCalculateScores()
  },
)

watch([filteredTrendRecords, teamRangeMetricRecords, chartMetricUnit, selectedMetricDirectionMeta], async () => {
  await nextTick()
  renderChart()
})

onMounted(async () => {
  await Promise.all([hydrate(), resetAndLoadLibrary()])
  await nextTick()
  libraryTableRef.value?.addEventListener('scroll', handleLibraryScroll)
})

onBeforeUnmount(() => {
  libraryTableRef.value?.removeEventListener('scroll', handleLibraryScroll)
  if (scoreAutoCalculateTimer !== null) {
    window.clearTimeout(scoreAutoCalculateTimer)
  }
})
</script>

<template>
  <AppShell>
    <div class="page-grid">
      <div class="split-view">
        <div class="panel form-panel">
          <div class="section-head">
            <div class="section-head-copy">
              <p class="eyebrow">趋势筛选</p>
              <h3>测试趋势筛选与补录</h3>
            </div>
            <div class="action-stack">
              <div class="action-row">
                <button class="ghost-btn slim" type="button" @click="openTypeManager">管理测试类型</button>
                <button class="ghost-btn slim" type="button" @click="openMetricManager">管理测试项目</button>
              </div>
              <div class="action-row">
                <button class="ghost-btn" :disabled="templateBusy" @click="handleTemplateDownload">
                  {{ templateBusy ? '下载中...' : '下载导入模板' }}
                </button>
                <button class="ghost-btn" :disabled="importBusy" @click="triggerImport">
                  {{ importBusy ? '导入中...' : '导入测试数据 Excel' }}
                </button>
              </div>
            </div>
          </div>

          <input ref="importInputRef" class="hidden-input" type="file" accept=".xlsx" @change="handleImport" />

          <p class="hint-text">
            左侧先用来筛选趋势；手动补录保留在下方折叠区。开始日期和结束日期留空时，表示查看全部日期。
          </p>

          <p v-if="actionMessage" class="status-banner">{{ actionMessage }}</p>

          <div class="two-col">
            <label class="field">
              <span>项目</span>
              <select v-model.number="trendFilters.sportId" class="text-input" @change="handleTrendSportChange">
                <option :value="0">全部项目</option>
                <option v-for="sport in trendSportOptions" :key="sport.id" :value="sport.id">{{ sport.name }}</option>
              </select>
            </label>
            <label class="field">
              <span>队伍</span>
              <select v-model.number="trendFilters.teamId" class="text-input" @change="handleTrendTeamChange">
                <option :value="0">全部队伍</option>
                <option v-for="team in trendTeamOptions" :key="team.id" :value="team.id">{{ team.name }}</option>
              </select>
            </label>
          </div>

          <label class="field">
            <span>运动员</span>
            <select v-model.number="trendFilters.athleteId" class="text-input" :disabled="!availableTrendAthletes.length">
              <option v-if="!availableTrendAthletes.length" :value="0">当前筛选条件下无运动员</option>
              <option v-for="athlete in availableTrendAthletes" :key="athlete.id" :value="athlete.id">
                {{ athlete.full_name }}
              </option>
            </select>
          </label>

          <div v-if="selectedAthlete" class="athlete-meta">
            <span>{{ selectedAthlete.team?.name || '未分队' }}</span>
            <span>体重：{{ selectedAthlete.weight ?? '--' }} kg</span>
          </div>

          <div class="two-col">
            <label class="field">
              <span>开始日期</span>
              <input v-model="trendFilters.dateFrom" type="date" class="text-input" />
            </label>
            <label class="field">
              <span>结束日期</span>
              <input v-model="trendFilters.dateTo" type="date" class="text-input" />
            </label>
          </div>
          <p class="field-note">开始日期和结束日期留空时，默认查看全部日期。</p>

          <div class="two-col">
            <label class="field">
              <span>测试类型</span>
              <select v-model="trendFilters.testType" class="text-input" @change="handleTrendTestTypeChange">
                <option v-for="definition in definitions" :key="definition.id" :value="definition.name">
                  {{ definition.name }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>测试项目</span>
              <select
                v-model="trendFilters.metricName"
                class="text-input"
                :disabled="!availableMetricDefinitions.length"
                @change="handleTrendMetricChange"
              >
                <option v-if="!availableMetricDefinitions.length" value="">请先在该类型下添加测试项目</option>
                <option v-for="definition in availableMetricDefinitions" :key="definition.id" :value="definition.name">
                  {{ definition.name }}
                </option>
              </select>
            </label>
          </div>

          <p v-if="trendFilters.testType && !availableMetricDefinitions.length" class="field-note">
            当前测试类型下还没有测试项目，请先点击“管理测试项目”添加二级分类。
          </p>
          <p v-else-if="selectedMetricDefinition" class="field-note">
            当前项目方向：<strong>{{ selectedMetricDirectionMeta.label }}</strong>（{{ selectedMetricDirectionMeta.hint }}）
          </p>

          <div class="entry-panel">
            <button class="ghost-btn entry-toggle" type="button" @click="toggleEntryPanel">
              {{ entryPanelOpen ? '收起手动添加测试记录' : '展开手动添加测试记录' }}
            </button>

            <div v-if="entryPanelOpen" class="entry-panel-body">
              <p class="field-note">
                当前补录对象：{{ selectedAthlete?.full_name || '未选择运动员' }} / {{ trendFilters.testType || '未选择测试类型' }} /
                {{ trendFilters.metricName || '未选择测试项目' }}
              </p>

              <label class="field">
                <span>测试日期</span>
                <input v-model="entryForm.testDate" type="date" class="text-input" />
              </label>

              <div class="two-col">
                <label class="field">
                  <span>数值结果</span>
                  <input
                    v-model.number="entryForm.resultValue"
                    type="number"
                    step="0.01"
                    class="text-input"
                    placeholder="用于计算和统计"
                  />
                </label>
                <label class="field">
                  <span>显示文本</span>
                  <input v-model="entryForm.resultText" class="text-input" placeholder="如 13′32″3，可留空" />
                </label>
              </div>

              <div class="two-col">
                <label class="field">
                  <span>单位</span>
                  <input
                    v-model="entryForm.unit"
                    class="text-input"
                    :placeholder="selectedMetricDefinition?.default_unit || '手动填写单位'"
                  />
                </label>
                <label class="field">
                  <span>备注</span>
                  <input v-model="entryForm.notes" class="text-input" placeholder="可选" />
                </label>
              </div>

              <button class="primary-btn" :disabled="!canSubmitEntryRecord" @click="submitEntryRecord">保存测试记录</button>
            </div>
          </div>
        </div>

        <div class="panel chart-panel">
          <div class="section-head">
            <div class="section-head-copy">
              <p class="eyebrow">趋势图</p>
              <h3>{{ chartTitle }}</h3>
              <p v-if="selectedMetricDefinition" class="direction-note">
                {{ selectedMetricDirectionMeta.label }}：{{ selectedMetricDirectionMeta.hint }}
              </p>
            </div>
          </div>

          <div ref="chartRef" class="chart"></div>

          <div class="list-grid">
            <div v-for="record in filteredTrendResultCards" :key="record.id" class="row-card adaptive-card">
              <strong class="adaptive-card-title">{{ record.metric_name }}：{{ displayResult(record) }}</strong>
              <span class="adaptive-card-subtitle adaptive-card-clamp-2">{{ record.test_date }} / {{ record.test_type }}</span>
              <small v-if="computeRelativeStrength(record)" class="adaptive-card-meta adaptive-card-clamp-1">
                力量体重比：{{ computeRelativeStrength(record) }}
              </small>
              <small v-else class="adaptive-card-meta adaptive-card-clamp-1">{{ record.notes || '无备注' }}</small>
            </div>
          </div>
          <p v-if="!filteredTrendResultCards.length" class="hint-text">当前趋势筛选条件下没有测试数据。</p>
        </div>
      </div>

      <div class="panel library-panel">
        <div class="section-head">
          <div class="section-head-copy">
            <p class="eyebrow">测试评分</p>
            <h3>测试评分与雷达图</h3>
          </div>
          <div class="action-row">
            <button class="ghost-btn" type="button" @click="openScoreProfileManager">管理评分模板</button>
          </div>
        </div>

        <div class="filter-grid">
          <select v-model.number="scoreFilters.scoreProfileId" class="text-input">
            <option :value="0">请选择评分模板</option>
            <option v-for="profile in scoreProfiles" :key="profile.id" :value="profile.id">{{ profile.name }}</option>
          </select>
          <select v-model.number="scoreFilters.teamId" class="text-input">
            <option :value="0">请选择队伍</option>
            <option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option>
          </select>
          <select v-model="scoreFilters.baselineMode" class="text-input">
            <option value="current_batch">当前批次</option>
            <option value="historical_pool">历史数据池</option>
          </select>
          <input v-model="scoreFilters.dateFrom" type="date" class="text-input" />
          <input v-model="scoreFilters.dateTo" type="date" class="text-input" />
        </div>
        <p class="field-note">
          评分日期留空时，默认使用当前队伍全部测试记录的日期范围
          <template v-if="scoreTeamDateRange">（{{ scoreTeamDateRange.from }} 至 {{ scoreTeamDateRange.to }}）</template>
          <template v-else>。</template>
        </p>
        <p class="field-note">选择评分模板、队伍、评分基准或日期后将自动重新计算。</p>

        <div class="entry-panel-body">
          <p class="hint-text">当前评分模式：Z 分数标准化评分</p>
          <p class="hint-text">T 分数解释：50 表示参考数据平均水平，每 10 分约等于 1 个标准差。</p>
          <p class="hint-text">分数未做截断，极高或极低分可能代表真实极端表现，也可能提示需要检查原始数据。</p>
          <p class="hint-text">当前评分取值口径：每个项目使用所选日期范围内最新一次测试记录。</p>
        </div>

        <template v-if="scoreCalculation">
          <div class="library-meta">
            <span>评分基准：{{ scoreCalculation.baseline_label }}</span>
            <span>模板：{{ scoreCalculation.profile.name }}</span>
            <span>参与排行人数：{{ scoreCalculation.ranking.length }}</span>
          </div>

          <div v-if="scoreCalculation.warnings.length" class="manager-error">
            {{ scoreCalculation.warnings.join('；') }}
          </div>

          <div class="split-view score-split-view">
            <section class="panel">
              <div class="section-head">
                <div class="section-head-copy">
                  <p class="eyebrow">综合评分</p>
                  <h3>排行榜</h3>
                </div>
              </div>
              <div class="list-grid">
                <button
                  v-for="(athlete, index) in scoreCalculation.ranking"
                  :key="athlete.athlete_id"
                  class="row-card adaptive-card score-rank-card"
                  :class="{ active: selectedScoreAthleteId === athlete.athlete_id }"
                  type="button"
                  @click="selectedScoreAthleteId = athlete.athlete_id"
                >
                  <div class="score-rank-card-head">
                    <span class="score-rank-index">#{{ index + 1 }}</span>
                    <span v-if="getRankMedal(index)" class="score-rank-medal" :aria-label="`第 ${index + 1} 名奖牌`">
                      {{ getRankMedal(index) }}
                    </span>
                  </div>
                  <strong class="adaptive-card-title">{{ athlete.athlete_name }}</strong>
                  <span class="adaptive-card-subtitle">{{ athlete.team_name || '未分队' }}</span>
                  <small class="adaptive-card-meta">综合评分：{{ formatScoreDisplay(athlete.overall_score) }}</small>
                </button>
              </div>
            </section>

            <section class="panel">
              <div class="section-head">
                <div class="section-head-copy">
                  <p class="eyebrow">雷达图</p>
                  <h3>个人 vs 团队平均</h3>
                </div>
              </div>
              <div v-if="selectedScoreAthlete" ref="scoreRadarRef" class="chart"></div>
              <div v-else class="empty-state">当前没有可展示的个人评分结果。</div>
              <p class="hint-text">绿色表示当前球员，橙色表示团队平均。50 为参考均值，60 约为高于均值 1 个标准差，40 约为低于均值 1 个标准差。</p>
            </section>
          </div>

          <section v-if="selectedScoreAthlete" class="panel">
            <div class="section-head">
              <div class="section-head-copy">
                <p class="eyebrow">项目明细</p>
                <h3>{{ selectedScoreAthlete.athlete_name }} 评分明细</h3>
              </div>
            </div>

            <div v-if="selectedScoreAthlete.missing_metrics.length" class="manager-error">
              缺失项目：{{ selectedScoreAthlete.missing_metrics.join('；') }}
            </div>

            <div v-for="dimension in selectedScoreAthlete.dimension_scores" :key="dimension.dimension_id" class="detail-section">
              <h4>{{ dimension.dimension_name }}：{{ dimension.score ?? '--' }}</h4>
              <p v-if="dimension.warnings.length" class="hint-text">{{ dimension.warnings.join('；') }}</p>
              <div class="table-scroll">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>测试项目</th>
                      <th>原始值</th>
                      <th>测试日期</th>
                      <th>mean</th>
                      <th>sd</th>
                      <th>z</th>
                      <th>standard_score</th>
                      <th>权重</th>
                      <th>缺失</th>
                      <th>样本不足</th>
                      <th>sd=0</th>
                      <th>异常值提示</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="metric in dimension.metrics" :key="`${dimension.dimension_id}-${metric.metric_definition_id}`">
                      <td>{{ metric.metric_name }}</td>
                      <td>{{ metric.raw_value ?? '-' }}</td>
                      <td>{{ metric.raw_test_date || '-' }}</td>
                      <td>{{ metric.mean ?? '-' }}</td>
                      <td>{{ metric.sd ?? '-' }}</td>
                      <td>{{ metric.z ?? '-' }}</td>
                      <td>{{ metric.standard_score ?? '-' }}</td>
                      <td>{{ metric.weight ?? '-' }}</td>
                      <td>{{ metric.is_missing ? '是' : '否' }}</td>
                      <td>{{ metric.sample_insufficient ? '是' : '否' }}</td>
                      <td>{{ metric.zero_variance ? '是' : '否' }}</td>
                      <td>{{ metric.outlier_warning ? '是' : '否' }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        </template>
      </div>

      <div class="panel library-panel">
        <div class="section-head">
          <div class="section-head-copy">
            <p class="eyebrow">数据总库</p>
            <h3>测试数据总库</h3>
          </div>
          <div class="action-row">
            <button
              class="ghost-btn danger-btn"
              :disabled="!hasLibraryFilters || !libraryTotal"
              @click="handleDeleteFilteredBatch"
            >
              删除当前筛选批次
            </button>
            <button class="ghost-btn" :disabled="exportBusy" @click="handleLibraryExport">
              {{ exportBusy ? '导出中...' : '导出总库 Excel' }}
            </button>
          </div>
        </div>

        <div class="filter-grid">
          <input
            v-model="libraryFilters.athleteKeyword"
            class="text-input"
            list="library-athlete-options"
            placeholder="按运动员姓名搜索或选择"
          />
          <datalist id="library-athlete-options">
            <option v-for="option in libraryAthleteOptions" :key="option" :value="option" />
          </datalist>
          <input
            v-model="libraryFilters.metricKeyword"
            class="text-input"
            list="library-metric-options"
            placeholder="按测试项目搜索或选择"
          />
          <datalist id="library-metric-options">
            <option v-for="option in libraryMetricOptions" :key="option" :value="option" />
          </datalist>
          <select v-model="libraryFilters.testType" class="text-input">
            <option value="">全部测试类型</option>
            <option v-for="option in libraryTestTypeOptions" :key="option" :value="option">{{ option }}</option>
          </select>
        </div>

        <div class="library-meta">
          <span>趋势数据记录数：{{ records.length }}</span>
          <span>总库筛选后总数：{{ libraryTotal }}</span>
          <span>已加载：{{ libraryItems.length }}</span>
          <span>运动员：{{ athletes.length }}</span>
        </div>

        <p v-if="libraryError" class="manager-error">{{ libraryError }}</p>

        <div ref="libraryTableRef" class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>运动员</th>
                <th>队伍</th>
                <th>测试类型</th>
                <th>测试项目</th>
                <th>数值结果</th>
                <th>显示文本</th>
                <th>单位</th>
                <th>备注</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in libraryItems" :key="record.id">
                <td>{{ record.test_date }}</td>
                <td>{{ record.athlete?.full_name || '-' }}</td>
                <td>{{ record.athlete?.team?.name || '-' }}</td>
                <td>{{ record.test_type }}</td>
                <td>{{ record.metric_name }}</td>
                <td>{{ record.result_value }}</td>
                <td>{{ record.result_text || '-' }}</td>
                <td>{{ record.unit }}</td>
                <td>{{ record.notes || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <p v-if="libraryLoading" class="hint-text">测试数据总库加载中...</p>
        <p v-else-if="!libraryItems.length" class="hint-text">当前筛选条件下没有测试数据。</p>
        <p v-else-if="libraryLoadingMore" class="hint-text">正在加载更多测试数据...</p>
        <p v-else-if="libraryHasMore" class="hint-text">向下滚动继续加载更多记录。</p>
      </div>
    </div>
  </AppShell>

  <teleport to="body">
    <div v-if="scoreProfileManagerOpen" class="manager-overlay" @click="closeScoreProfileManager">
      <section class="manager-dialog panel" role="dialog" aria-modal="true" aria-labelledby="score-profile-manager-title" @click.stop>
        <div class="manager-dialog-head">
          <div>
            <p class="eyebrow">测试评分</p>
            <h3 id="score-profile-manager-title">管理评分模板</h3>
          </div>
          <button class="ghost-btn slim" type="button" @click="closeScoreProfileManager">关闭</button>
        </div>

        <div class="manager-dialog-body">
          <div class="manager-list-block">
            <div class="manager-block-head">
              <strong>已有评分模板</strong>
              <span>{{ scoreProfiles.length }} 个</span>
            </div>
            <p v-if="scoreProfileError" class="manager-error">{{ scoreProfileError }}</p>
            <div v-if="!scoreProfiles.length" class="empty-state manager-empty">当前还没有评分模板，请先新增。</div>
            <div v-else class="manager-list">
              <div v-for="profile in scoreProfiles" :key="profile.id" class="manager-row">
                <div class="manager-row-copy">
                  <strong>{{ profile.name }}</strong>
                  <span class="manager-row-meta">维度数：{{ profile.dimensions.length }}</span>
                  <span class="manager-row-meta">状态：{{ profile.is_active ? '启用' : '停用' }}</span>
                  <p v-if="profile.notes" class="manager-row-notes">{{ profile.notes }}</p>
                </div>
                <div class="manager-row-actions">
                  <button class="ghost-btn slim" type="button" @click="startEditScoreProfile(profile)">编辑</button>
                  <button class="ghost-btn slim danger-btn" type="button" @click="removeScoreProfile(profile)">删除</button>
                </div>
              </div>
            </div>
          </div>

          <form class="manager-form-block" @submit.prevent="submitScoreProfile">
            <div class="manager-block-head">
              <strong>{{ editingScoreProfileId ? '编辑评分模板' : '新增评分模板' }}</strong>
              <button v-if="editingScoreProfileId" class="ghost-btn slim" type="button" @click="resetScoreProfileForm">取消编辑</button>
            </div>
            <div class="detail-section score-profile-base-section">
              <label class="field">
                <span>模板名称 <strong class="required-mark">*</strong></span>
                <input v-model="scoreProfileForm.name" class="text-input" placeholder="例如：篮球基础能力评分" />
              </label>
              <label class="field">
                <span>备注</span>
                <textarea v-model="scoreProfileForm.notes" class="text-input manager-textarea" placeholder="可选"></textarea>
              </label>
              <label class="checkbox-field">
                <input v-model="scoreProfileForm.is_active" type="checkbox" />
                <span>启用模板</span>
              </label>
              <div v-if="scoreProfileValidationErrors.length" class="manager-error">
                当前不能保存：
                {{ scoreProfileValidationErrors.join('；') }}
              </div>
            </div>

            <div v-for="(dimension, dimensionIndex) in scoreProfileForm.dimensions" :key="dimensionIndex" class="detail-section">
              <div class="section-head">
                <h4>能力维度 {{ dimensionIndex + 1 }}</h4>
                <button class="ghost-btn slim danger-btn" type="button" @click="removeScoreDimension(dimensionIndex)">删除维度</button>
              </div>
              <label class="field">
                <span>维度名称</span>
                <input v-model="dimension.name" class="text-input" placeholder="例如：下肢力量 / 爆发力 / 速度" />
              </label>
              <div class="action-row">
                <button class="ghost-btn slim" type="button" @click="equalizeDimensionWeights(dimension.metrics)">一键平均分配</button>
                <button class="ghost-btn slim" type="button" @click="normalizeDimensionWeights(dimension.metrics)">一键归一化</button>
                <button class="ghost-btn slim" type="button" @click="addScoreMetric(dimensionIndex)">添加测试项目</button>
              </div>
              <div v-for="(metric, metricIndex) in dimension.metrics" :key="metricIndex" class="grid two">
                <label class="field">
                  <span>测试项目</span>
                  <select v-model.number="metric.test_metric_definition_id" class="text-input" :disabled="!scoreMetricOptions.length">
                    <option :value="0">请选择测试项目</option>
                    <option v-if="!scoreMetricOptions.length" :value="0">当前没有可用测试项目，请先到测试项目管理中维护</option>
                    <option v-for="option in scoreMetricOptions" :key="option.id" :value="option.id">
                      {{ option.label }}
                    </option>
                  </select>
                </label>
                <label class="field">
                  <span>权重</span>
                  <input v-model.number="metric.weight" type="number" step="0.01" min="0" class="text-input" />
                </label>
                <div class="manager-form-actions">
                  <button class="ghost-btn slim danger-btn" type="button" @click="removeScoreMetric(dimensionIndex, metricIndex)">删除项目</button>
                </div>
              </div>
            </div>

            <div class="action-row">
              <button class="ghost-btn slim" type="button" @click="addScoreDimension">添加能力维度</button>
            </div>

            <div class="manager-form-actions">
              <button class="primary-btn" type="submit" :disabled="scoreSubmitting || !canSubmitScoreProfile">
                {{ scoreSubmitting ? '保存中...' : editingScoreProfileId ? '保存修改' : '新增评分模板' }}
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  </teleport>

  <teleport to="body">
    <div v-if="typeManagerOpen" class="manager-overlay" @click="closeTypeManager">
      <section class="manager-dialog panel" role="dialog" aria-modal="true" aria-labelledby="test-type-manager-title" @click.stop>
        <div class="manager-dialog-head">
          <div>
            <p class="eyebrow">测试数据模块</p>
            <h3 id="test-type-manager-title">管理测试类型</h3>
          </div>
          <button class="ghost-btn slim" type="button" @click="closeTypeManager">关闭</button>
        </div>

        <div class="manager-dialog-body">
          <div class="manager-list-block">
            <div class="manager-block-head">
              <strong>已有测试类型</strong>
              <span>{{ definitions.length }} 个</span>
            </div>
            <p v-if="typeManagerError" class="manager-error">{{ typeManagerError }}</p>
            <div v-if="!definitions.length" class="empty-state manager-empty">当前还没有测试类型，请先新增一级分类。</div>
            <div v-else class="manager-list">
              <div v-for="definition in definitions" :key="definition.id" class="manager-row">
                <div class="manager-row-copy">
                  <strong>{{ definition.name }}</strong>
                  <span class="scope-tag" :class="definition.is_system ? 'scope-tag-system' : 'scope-tag-team'">
                    {{ resolveDefinitionScopeLabel(definition) }}
                  </span>
                  <span class="manager-row-meta">编码：{{ definition.code }}</span>
                  <span class="manager-row-meta">测试项目：{{ definition.metrics.length }} 个</span>
                  <p v-if="definition.notes" class="manager-row-notes">{{ definition.notes }}</p>
                </div>
                <div v-if="canEditType(definition)" class="manager-row-actions">
                  <button class="ghost-btn slim" type="button" @click="startEditType(definition)">编辑</button>
                  <button
                    class="ghost-btn slim danger-btn"
                    type="button"
                    :disabled="deletingTypeId === definition.id"
                    @click="removeType(definition)"
                  >
                    {{ deletingTypeId === definition.id ? '删除中...' : '删除' }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <form class="manager-form-block" @submit.prevent="submitType">
            <div class="manager-block-head">
              <strong>{{ editingTypeId ? '编辑测试类型' : '新增测试类型' }}</strong>
              <button v-if="editingTypeId" class="ghost-btn slim" type="button" @click="resetTypeForm">取消编辑</button>
            </div>
            <label class="field">
              <span>测试类型名称 <strong class="required-mark">*</strong></span>
              <input v-model="typeForm.name" class="text-input" placeholder="例如：力量测试" />
            </label>
            <label v-if="authStore.isAdmin" class="field">
              <span>项目范围</span>
              <select v-model="typeForm.sport_id" class="text-input" :disabled="Boolean(editingTypeId)">
                <option :value="null">系统项目（所有队伍可见）</option>
                <option v-for="sport in sports" :key="sport.id" :value="sport.id">{{ sport.name }}</option>
              </select>
            </label>
            <label class="field">
              <span>备注</span>
              <textarea v-model="typeForm.notes" class="text-input manager-textarea" placeholder="可选" />
            </label>
            <p class="manager-help">
              {{ authStore.isAdmin
                ? '管理员可新建系统项目，也可通过接口创建指定队伍私有项目；当前页面编辑时不调整作用域。'
                : '队伍账号新建的测试类型默认归属当前队伍，仅本队和管理员可见。' }}
            </p>
            <div class="manager-form-actions">
              <button class="primary-btn" type="submit" :disabled="typeSubmitting || !canSubmitType">
                {{ typeSubmitting ? '保存中...' : editingTypeId ? '保存修改' : '新增测试类型' }}
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  </teleport>

  <teleport to="body">
    <div v-if="metricManagerOpen" class="manager-overlay" @click="closeMetricManager">
      <section class="manager-dialog panel" role="dialog" aria-modal="true" aria-labelledby="test-metric-manager-title" @click.stop>
        <div class="manager-dialog-head">
          <div>
            <p class="eyebrow">测试数据模块</p>
            <h3 id="test-metric-manager-title">管理测试项目</h3>
          </div>
          <button class="ghost-btn slim" type="button" @click="closeMetricManager">关闭</button>
        </div>

        <div class="manager-dialog-body">
          <div class="manager-list-block">
            <div class="manager-block-head">
              <strong>已有测试项目</strong>
              <span>{{ metricDefinitions.length }} 个</span>
            </div>
            <p v-if="metricManagerError" class="manager-error">{{ metricManagerError }}</p>
            <div v-if="!metricDefinitions.length" class="empty-state manager-empty">当前还没有测试项目，请先在对应测试类型下新增二级分类。</div>
            <div v-else class="manager-list">
              <div v-for="definition in metricDefinitions" :key="definition.id" class="manager-row">
                <div class="manager-row-copy">
                  <strong>{{ definition.name }}</strong>
                  <span class="manager-row-meta">所属测试类型：{{ definition.test_type_name }} / {{ resolveDefinitionScopeLabel(definition) }}</span>
                  <span class="manager-row-meta">默认单位：{{ definition.default_unit || '未设置' }}</span>
                  <span class="manager-row-meta">
                    项目方向：
                    <span
                      class="direction-tag"
                      :class="definition.is_lower_better ? 'direction-tag-lower' : 'direction-tag-higher'"
                    >
                      {{ getTestMetricDirectionMeta(definition).shortLabel }}
                    </span>
                  </span>
                  <span class="manager-row-meta">编码：{{ definition.code }}</span>
                  <p v-if="definition.notes" class="manager-row-notes">{{ definition.notes }}</p>
                </div>
                <div v-if="canEditMetric(definition)" class="manager-row-actions">
                  <button class="ghost-btn slim" type="button" @click="startEditMetric(definition)">编辑</button>
                  <button
                    class="ghost-btn slim danger-btn"
                    type="button"
                    :disabled="deletingMetricId === definition.id"
                    @click="removeMetric(definition)"
                  >
                    {{ deletingMetricId === definition.id ? '删除中...' : '删除' }}
                  </button>
                </div>
              </div>
            </div>
          </div>

          <form class="manager-form-block" @submit.prevent="submitMetric">
            <div class="manager-block-head">
              <strong>{{ editingMetricId ? '编辑测试项目' : '新增测试项目' }}</strong>
              <button v-if="editingMetricId" class="ghost-btn slim" type="button" @click="resetMetricForm">取消编辑</button>
            </div>
            <label class="field">
              <span>所属测试类型 <strong class="required-mark">*</strong></span>
              <select v-model="metricForm.test_type_id" class="text-input">
                <option :value="null">请选择测试类型</option>
                <option v-for="definition in editableTypeDefinitions" :key="definition.id" :value="definition.id">
                  {{ definition.name }}
                </option>
              </select>
            </label>
            <label class="field">
              <span>测试项目名称 <strong class="required-mark">*</strong></span>
              <input v-model="metricForm.name" class="text-input" placeholder="例如：卧推" />
            </label>
            <label class="field">
              <span>默认单位</span>
              <input v-model="metricForm.default_unit" class="text-input" placeholder="例如：kg / cm / s / 次 / RSI" />
            </label>
            <label class="checkbox-field">
              <input v-model="metricForm.is_lower_better" type="checkbox" />
              <span>低值优先（数值越小越好）</span>
            </label>
            <label class="field">
              <span>备注</span>
              <textarea v-model="metricForm.notes" class="text-input manager-textarea" placeholder="可选" />
            </label>
            <p class="manager-help">
              {{ authStore.isAdmin
                ? '管理员可以把测试项目挂到任意系统或队伍私有测试类型下。'
                : '队伍账号只能在本队自建测试类型下维护测试项目；系统项目可用但不可改。' }}
            </p>
            <div class="manager-form-actions">
              <button
                class="primary-btn"
                type="submit"
                :disabled="metricSubmitting || !canSubmitMetric || !editableTypeDefinitions.length"
              >
                {{ metricSubmitting ? '保存中...' : editingMetricId ? '保存修改' : '新增测试项目' }}
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  </teleport>
</template>

<style scoped>
.page-grid {
  display: grid;
  gap: 18px;
  align-content: start;
}

.split-view {
  display: grid;
  grid-template-columns: minmax(360px, 430px) 1fr;
  gap: 18px;
  min-height: 0;
}

.form-panel,
.chart-panel,
.library-panel,
.field,
.list-grid {
  display: grid;
  gap: 12px;
  align-content: start;
  min-height: 0;
}

.section-head,
.section-head-copy,
.action-stack,
.action-row {
  display: flex;
}

.section-head {
  justify-content: space-between;
  align-items: start;
  gap: 16px;
}

.section-head-copy,
.action-stack {
  flex-direction: column;
  gap: 10px;
}

.action-row {
  gap: 10px;
  flex-wrap: wrap;
}

.ghost-btn {
  min-height: 44px;
  border-radius: 14px;
  padding: 0 14px;
  background: #e2e8f0;
  color: #0f172a;
  font-weight: 600;
}

.ghost-btn.slim {
  min-height: 38px;
}

.danger-btn {
  color: #b91c1c;
}

.hidden-input {
  display: none;
}

.eyebrow,
.field span,
.athlete-meta span,
.library-meta span {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
}

.hint-text,
.field-note,
.direction-note {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
}

.field-note {
  margin-top: -4px;
}

.direction-note {
  color: #0f766e;
  font-weight: 600;
}

.entry-panel,
.entry-panel-body {
  display: grid;
  gap: 12px;
}

.entry-panel {
  margin-top: 4px;
  padding-top: 4px;
}

.entry-panel-body {
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.68);
}

.entry-toggle {
  width: 100%;
  justify-content: center;
}

.status-banner {
  margin: 0;
  padding: 12px 14px;
  border-radius: 14px;
  background: #ecfdf5;
  color: #065f46;
  font-size: 13px;
}

.athlete-meta,
.library-meta {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.two-col,
.filter-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.filter-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.chart-panel {
  grid-template-rows: auto auto auto;
}

.chart {
  height: 320px;
  width: 100%;
}

.list-grid {
  overflow-y: auto;
  max-height: 360px;
  padding-right: 8px;
}

.row-card {
  background: var(--panel-soft);
  border-radius: 16px;
  padding: 16px;
  display: grid;
  grid-template-rows: auto auto auto;
  gap: 8px;
  min-height: 112px;
}

.library-panel {
  align-content: start;
}

.table-scroll {
  overflow: auto;
  max-height: 560px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: white;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 920px;
}

.data-table th,
.data-table td {
  padding: 12px 14px;
  border-bottom: 1px solid #e5e7eb;
  text-align: left;
  vertical-align: top;
  font-size: 14px;
}

.data-table th {
  position: sticky;
  top: 0;
  background: #f8fafc;
  z-index: 1;
}

.manager-overlay {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.44);
}

.manager-dialog {
  width: min(980px, 100%);
  max-height: calc(100vh - 48px);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 18px;
  overflow: hidden;
}

.manager-dialog-head,
.manager-block-head,
.manager-row,
.manager-row-actions {
  display: flex;
  gap: 12px;
}

.manager-dialog-head,
.manager-block-head,
.manager-row {
  justify-content: space-between;
}

.manager-dialog-head,
.manager-block-head {
  align-items: center;
}

.manager-row {
  align-items: flex-start;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.72);
}

.manager-dialog-head h3,
.manager-block-head strong,
.manager-row-copy strong,
.manager-row-notes,
.manager-help,
.manager-error {
  margin: 0;
}

.manager-block-head {
  color: var(--muted);
  font-size: 13px;
}

.manager-dialog-body {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(280px, 0.85fr);
  gap: 18px;
  min-height: 0;
  overflow: hidden;
}

.manager-list-block,
.manager-form-block {
  min-height: 0;
  gap: 12px;
}

.manager-list-block {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.manager-form-block {
  display: grid;
  align-content: start;
  overflow-y: auto;
  padding-right: 6px;
  padding-top: 2px;
}

.manager-list {
  display: grid;
  gap: 12px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 6px;
}

.manager-row-copy {
  display: grid;
  gap: 6px;
}

.manager-row-meta,
.manager-row-notes,
.manager-help {
  color: var(--muted);
  font-size: 13px;
}

.scope-tag {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  width: fit-content;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.scope-tag-system {
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
}

.scope-tag-team {
  background: rgba(15, 118, 110, 0.12);
  color: #0f766e;
}

.direction-tag {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 0 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.direction-tag-higher {
  background: rgba(14, 165, 233, 0.12);
  color: #0369a1;
}

.direction-tag-lower {
  background: rgba(245, 158, 11, 0.14);
  color: #b45309;
}

.checkbox-field {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 0 2px;
  color: var(--text-main);
  font-size: 14px;
}

.checkbox-field input {
  width: 18px;
  height: 18px;
}

.manager-textarea {
  min-height: 84px;
  resize: vertical;
}

.manager-form-actions {
  display: flex;
  justify-content: flex-end;
}

.manager-empty {
  min-height: 120px;
}

.manager-error {
  border-radius: 12px;
  border: 1px solid rgba(185, 28, 28, 0.16);
  background: #fef2f2;
  color: #b91c1c;
  padding: 10px 12px;
}

.detail-section {
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.76);
}

.detail-section + .detail-section {
  margin-top: 4px;
}

.detail-section .section-head {
  align-items: flex-start;
}

.detail-section .section-head h4 {
  margin: 0;
  min-width: 0;
}

.detail-section .action-row {
  align-items: center;
}

.detail-section .manager-form-actions {
  justify-content: flex-end;
  align-items: center;
}

.score-profile-base-section {
  gap: 12px;
}

.score-rank-card {
  position: relative;
}

.score-rank-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.score-rank-index {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.12);
  color: #0f766e;
  font-size: 12px;
  font-weight: 700;
}

.score-rank-medal {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 999px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.96), rgba(241, 245, 249, 0.92));
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.18);
  font-size: 18px;
  line-height: 1;
}

@media (max-width: 1100px) {
  .split-view,
  .two-col,
  .filter-grid,
  .manager-dialog-body {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .section-head,
  .manager-dialog-head,
  .manager-row,
  .manager-row-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .manager-overlay {
    padding: 16px;
    align-items: flex-end;
  }

  .manager-dialog {
    max-height: calc(100vh - 24px);
  }

  .detail-section .manager-form-actions {
    justify-content: stretch;
  }

  .detail-section .manager-form-actions > * {
    width: 100%;
  }
}
</style>
