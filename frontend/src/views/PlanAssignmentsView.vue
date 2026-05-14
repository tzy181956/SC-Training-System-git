<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { fetchAthletes, fetchSports, fetchTeams } from '@/api/athletes'
import {
  cancelBatchAssignments,
  createBatchAssignments,
  fetchAssignmentOverview,
  fetchPlanTemplates,
  previewBatchAssignments,
} from '@/api/plans'
import AssignmentOverviewPane from '@/components/assignment/AssignmentOverviewPane.vue'
import AssignmentPreviewPanel from '@/components/assignment/AssignmentPreviewPanel.vue'
import AppShell from '@/components/layout/AppShell.vue'
import { DEFAULT_REPEAT_WEEKDAYS, REPEAT_WEEKDAY_OPTIONS, formatRepeatWeekdays } from '@/constants/repeatWeekdays'
import { useAuthStore } from '@/stores/auth'
import { todayString } from '@/utils/date'
import {
  filterTeamsBySport,
  isSportScoped,
  resolveInitialSportFilterValue,
  retainVisibleTeamId,
} from '@/utils/projectTeamScope'

type AssignmentViewMode = 'builder' | 'overview'
type ScheduleMode = 'single_day' | 'date_range' | 'weekly_repeat'

const athletes = ref<any[]>([])
const templates = ref<any[]>([])
const sports = ref<any[]>([])
const teams = ref<any[]>([])
const authStore = useAuthStore()
const overview = ref<any>({
  assignment_groups: [],
  unassigned_athletes: [],
  assigned_count: 0,
  unassigned_count: 0,
  group_count: 0,
})
const preview = ref<any | null>(null)
const loadingPreview = ref(false)
const submitting = ref(false)
const cancelling = ref(false)

const activeView = ref<AssignmentViewMode>('builder')
const selectedAssignmentsByGroupKey = ref<Record<string, number[]>>({})
const confirmDeleteGroupKey = ref<string | null>(null)
const selectedOverviewGroupKey = ref<string | null>(null)

const overviewState = reactive({
  targetDate: todayString(),
  sportId: resolveInitialSportFilterValue(authStore.currentUser?.sport_id),
  teamId: 0,
})

const builderState = reactive({
  sportId: resolveInitialSportFilterValue(authStore.currentUser?.sport_id),
  teamId: 0,
  keyword: '',
  selectedOnly: false,
  athleteIds: [] as number[],
  templateId: 0,
  scheduleMode: 'single_day' as ScheduleMode,
  singleDate: todayString(),
  startDate: todayString(),
  endDate: todayString(),
  repeatWeekdays: [...DEFAULT_REPEAT_WEEKDAYS] as number[],
  notes: '',
})

const viewButtons = [
  { key: 'builder', label: '新建分配' },
  { key: 'overview', label: '现有分配' },
] as const
const isSportFilterLocked = computed(() => isSportScoped(authStore.currentUser?.sport_id))

const overviewTeams = computed(() => filterTeamsBySport(teams.value, overviewState.sportId))
const builderTeams = computed(() => filterTeamsBySport(teams.value, builderState.sportId))

const filteredOverviewGroups = computed(() =>
  overview.value.assignment_groups.filter((group: any) =>
    group.athletes.some((athlete: any) => {
      if (overviewState.sportId && athlete.sport_id !== overviewState.sportId) return false
      if (overviewState.teamId && athlete.team_id !== overviewState.teamId) return false
      return true
    }),
  ),
)

const filteredOverviewUnassignedAthletes = computed(() =>
  overview.value.unassigned_athletes.filter((athlete: any) => {
    if (overviewState.sportId && athlete.sport_id !== overviewState.sportId) return false
    if (overviewState.teamId && athlete.team_id !== overviewState.teamId) return false
    return true
  }),
)

const assignedCountsByAthleteId = computed(() => {
  const map = new Map<number, number>()
  ;(overview.value.assignment_groups || []).forEach((group: any) => {
    ;(group.entries || []).forEach((entry: any) => {
      const athleteId = entry.athlete.id
      map.set(athleteId, (map.get(athleteId) || 0) + 1)
    })
  })
  return map
})

const unassignedAthleteIdSet = computed(() =>
  new Set<number>((overview.value.unassigned_athletes || []).map((athlete: any) => athlete.id)),
)

const selectedTemplate = computed(() => templates.value.find((item) => item.id === builderState.templateId) || null)

const builderBaseAthletes = computed(() =>
  athletes.value
    .filter((athlete) => {
      if (!athlete.is_active) return false
      if (builderState.sportId && athlete.sport_id !== builderState.sportId) return false
      if (builderState.teamId && athlete.team_id !== builderState.teamId) return false
      if (builderState.keyword.trim()) {
        const keyword = builderState.keyword.trim().toLowerCase()
        const values = [athlete.full_name, athlete.team?.name, athlete.sport?.name]
        if (!values.some((value) => (value || '').toLowerCase().includes(keyword))) {
          return false
        }
      }
      return true
    })
    .sort((left, right) => {
      const leftSelected = builderState.athleteIds.includes(left.id) ? 1 : 0
      const rightSelected = builderState.athleteIds.includes(right.id) ? 1 : 0
      if (leftSelected !== rightSelected) return rightSelected - leftSelected
      const leftTeam = left.team?.name || ''
      const rightTeam = right.team?.name || ''
      if (leftTeam !== rightTeam) return leftTeam.localeCompare(rightTeam, 'zh-CN')
      return (left.full_name || '').localeCompare(right.full_name || '', 'zh-CN')
    }),
)

const visibleBuilderAthletes = computed(() =>
  builderState.selectedOnly
    ? builderBaseAthletes.value.filter((athlete) => builderState.athleteIds.includes(athlete.id))
    : builderBaseAthletes.value,
)

const selectedAthletes = computed(() => {
  const athleteMap = new Map<number, any>(athletes.value.map((athlete) => [athlete.id, athlete]))
  return builderState.athleteIds
    .map((athleteId) => athleteMap.get(athleteId))
    .filter(Boolean)
})

const selectedTeamNames = computed(() =>
  Array.from(new Set(selectedAthletes.value.map((athlete) => athlete.team?.name).filter(Boolean))),
)

const selectedWithExistingPlans = computed(() =>
  selectedAthletes.value.filter((athlete) => (assignedCountsByAthleteId.value.get(athlete.id) || 0) > 0).length,
)

const selectedUnassignedCount = computed(() =>
  selectedAthletes.value.filter((athlete) => unassignedAthleteIdSet.value.has(athlete.id)).length,
)

const scheduleModeButtons = [
  { key: 'single_day', label: '单日计划' },
  { key: 'date_range', label: '日期段计划' },
  { key: 'weekly_repeat', label: '每周重复计划' },
] as const

const hasSelectedRepeatWeekdays = computed(() => builderState.repeatWeekdays.length > 0)
const previewHasManualControl = computed(() =>
  Boolean(preview.value?.rows.some((row: any) => row.items.some((item: any) => item.status === 'manual_control'))),
)

const scheduleSummary = computed(() => {
  if (builderState.scheduleMode === 'single_day') {
    return `单日计划 · ${builderState.singleDate} · ${weekdayLabelFromDate(builderState.singleDate)}`
  }
  if (builderState.scheduleMode === 'date_range') {
    return `日期段计划 · ${builderState.startDate} 至 ${builderState.endDate}`
  }
  return `每周重复计划 · ${builderState.startDate} 至 ${builderState.endDate} · ${formatRepeatWeekdays(builderState.repeatWeekdays)}`
})

const scheduleHint = computed(() => {
  if (builderState.scheduleMode === 'single_day') {
    return '只在当天生成一次有效分配。'
  }
  if (builderState.scheduleMode === 'date_range') {
    return '区间内每天都按同一模板执行。'
  }
  return `按所选星期重复执行：${formatRepeatWeekdays(builderState.repeatWeekdays)}`
})

const builderValidationMessage = computed(() => {
  if (!builderState.athleteIds.length) return '先选择至少一名队员。'
  if (!builderState.templateId) return '先选择训练模板。'
  if (builderState.scheduleMode === 'single_day') {
    return builderState.singleDate ? '' : '请选择训练日期。'
  }
  if (!builderState.startDate || !builderState.endDate) {
    return '请先补全开始和结束日期。'
  }
  if (builderState.startDate > builderState.endDate) {
    return '开始日期不能晚于结束日期。'
  }
  if (builderState.scheduleMode === 'weekly_repeat' && !builderState.repeatWeekdays.length) {
    return '每周重复计划至少需要选择一个执行日。'
  }
  return ''
})

const builderPayload = computed(() => {
  if (builderValidationMessage.value) {
    return null
  }
  if (builderState.scheduleMode === 'single_day') {
    const weekday = weekdayFromDate(builderState.singleDate)
    return {
      athlete_ids: builderState.athleteIds,
      template_id: builderState.templateId,
      assigned_date: builderState.singleDate,
      start_date: builderState.singleDate,
      end_date: builderState.singleDate,
      repeat_weekdays: [weekday],
      notes: builderState.notes,
      status: 'active',
    }
  }
  if (builderState.scheduleMode === 'date_range') {
    return {
      athlete_ids: builderState.athleteIds,
      template_id: builderState.templateId,
      assigned_date: builderState.startDate,
      start_date: builderState.startDate,
      end_date: builderState.endDate,
      repeat_weekdays: [...DEFAULT_REPEAT_WEEKDAYS],
      notes: builderState.notes,
      status: 'active',
    }
  }
  return {
    athlete_ids: builderState.athleteIds,
    template_id: builderState.templateId,
    assigned_date: builderState.startDate,
    start_date: builderState.startDate,
    end_date: builderState.endDate,
    repeat_weekdays: [...builderState.repeatWeekdays],
    notes: builderState.notes,
    status: 'active',
  }
})

const builderCanSubmit = computed(() => Boolean(builderPayload.value && preview.value))

let previewRequestId = 0

async function hydrate() {
  const [athleteData, templateData, sportData, teamData] = await Promise.all([
    fetchAthletes(),
    fetchPlanTemplates(),
    fetchSports(),
    fetchTeams(),
  ])
  athletes.value = athleteData
  templates.value = templateData
  sports.value = sportData
  teams.value = teamData
  if (isSportFilterLocked.value) {
    overviewState.sportId = resolveInitialSportFilterValue(authStore.currentUser?.sport_id)
    builderState.sportId = resolveInitialSportFilterValue(authStore.currentUser?.sport_id)
  }
  overviewState.teamId = retainVisibleTeamId(overviewState.teamId, overviewTeams.value)
  builderState.teamId = retainVisibleTeamId(builderState.teamId, builderTeams.value)
  await loadOverview()
}

async function loadOverview() {
  overview.value = await fetchAssignmentOverview(overviewState.targetDate)
  selectedAssignmentsByGroupKey.value = {}
  confirmDeleteGroupKey.value = null
  if (
    selectedOverviewGroupKey.value
    && !filteredOverviewGroups.value.some((group: any) => group.assignment_ids.join('-') === selectedOverviewGroupKey.value)
  ) {
    selectedOverviewGroupKey.value = null
  }
}

function toggleAthlete(id: number) {
  if (builderState.athleteIds.includes(id)) {
    builderState.athleteIds = builderState.athleteIds.filter((athleteId) => athleteId !== id)
    return
  }
  builderState.athleteIds = [...builderState.athleteIds, id]
}

function selectAllFilteredAthletes() {
  const ids = builderBaseAthletes.value.map((athlete) => athlete.id)
  builderState.athleteIds = Array.from(new Set([...builderState.athleteIds, ...ids]))
}

function selectFilteredUnassignedAthletes() {
  const ids = builderBaseAthletes.value
    .filter((athlete) => unassignedAthleteIdSet.value.has(athlete.id))
    .map((athlete) => athlete.id)
  builderState.athleteIds = Array.from(new Set([...builderState.athleteIds, ...ids]))
}

function clearSelectedAthletes() {
  builderState.athleteIds = []
}

function setScheduleMode(mode: ScheduleMode) {
  if (builderState.scheduleMode === mode) return

  if (mode === 'single_day') {
    const nextDate = builderState.scheduleMode === 'single_day' ? builderState.singleDate : builderState.startDate
    builderState.singleDate = nextDate || todayString()
    builderState.repeatWeekdays = [weekdayFromDate(builderState.singleDate)]
  } else if (mode === 'date_range') {
    const nextStart = builderState.scheduleMode === 'single_day' ? builderState.singleDate : builderState.startDate
    builderState.startDate = nextStart || todayString()
    builderState.endDate = builderState.endDate < builderState.startDate ? builderState.startDate : builderState.endDate
    builderState.repeatWeekdays = [...DEFAULT_REPEAT_WEEKDAYS]
  } else {
    const nextStart = builderState.scheduleMode === 'single_day' ? builderState.singleDate : builderState.startDate
    builderState.startDate = nextStart || todayString()
    builderState.endDate = builderState.endDate < builderState.startDate ? builderState.startDate : builderState.endDate
    if (!builderState.repeatWeekdays.length) {
      builderState.repeatWeekdays = [weekdayFromDate(builderState.startDate)]
    }
  }

  builderState.scheduleMode = mode
}

function toggleRepeatWeekday(weekday: number) {
  if (builderState.repeatWeekdays.includes(weekday)) {
    builderState.repeatWeekdays = builderState.repeatWeekdays.filter((current) => current !== weekday)
    return
  }
  builderState.repeatWeekdays = [...builderState.repeatWeekdays, weekday].sort((left, right) => left - right)
}

function getAssignedPlanHint(athleteId: number) {
  const assignedCount = assignedCountsByAthleteId.value.get(athleteId) ?? 0
  if (!assignedCount) {
    return '当前查看日期口径下暂无后续计划'
  }
  if (builderState.athleteIds.includes(athleteId)) {
    return `已有 ${assignedCount} 条当前/后续计划，已加入本次分配`
  }
  return `已有 ${assignedCount} 条当前/后续计划`
}

function selectOverviewGroup(groupKey: string) {
  selectedOverviewGroupKey.value = groupKey
  confirmDeleteGroupKey.value = null
}

function toggleOverviewAssignment(groupKey: string, assignmentId: number) {
  const current = selectedAssignmentsByGroupKey.value[groupKey] ?? []
  selectedAssignmentsByGroupKey.value = {
    ...selectedAssignmentsByGroupKey.value,
    [groupKey]: current.includes(assignmentId)
      ? current.filter((currentId) => currentId !== assignmentId)
      : [...current, assignmentId],
  }

  if (!(selectedAssignmentsByGroupKey.value[groupKey] || []).length && confirmDeleteGroupKey.value === groupKey) {
    confirmDeleteGroupKey.value = null
  }
}

function requestDeleteGroupAssignments(groupKey: string) {
  if (!(selectedAssignmentsByGroupKey.value[groupKey] || []).length) return
  confirmDeleteGroupKey.value = groupKey
}

function resetDeleteFlow() {
  confirmDeleteGroupKey.value = null
}

async function cancelSelectedGroupAssignments(groupKey: string) {
  const assignmentIds = selectedAssignmentsByGroupKey.value[groupKey] ?? []
  if (!assignmentIds.length) return

  cancelling.value = true
  try {
    await cancelBatchAssignments(assignmentIds)
    await loadOverview()
  } finally {
    cancelling.value = false
  }
}

async function generatePreview() {
  const payload = builderPayload.value
  previewRequestId += 1
  const requestId = previewRequestId

  if (!payload) {
    preview.value = null
    loadingPreview.value = false
    return
  }

  loadingPreview.value = true
  try {
    const data = await previewBatchAssignments(payload)
    if (requestId === previewRequestId) {
      preview.value = data
    }
  } finally {
    if (requestId === previewRequestId) {
      loadingPreview.value = false
    }
  }
}

async function submitAssignments() {
  if (!builderPayload.value || !preview.value) return

  submitting.value = true
  try {
    await createBatchAssignments(builderPayload.value)
    builderState.athleteIds = []
    builderState.templateId = 0
    builderState.notes = ''
    builderState.scheduleMode = 'single_day'
    builderState.singleDate = todayString()
    builderState.startDate = todayString()
    builderState.endDate = todayString()
    builderState.repeatWeekdays = [...DEFAULT_REPEAT_WEEKDAYS]
    preview.value = null
    await loadOverview()
    activeView.value = 'overview'
  } finally {
    submitting.value = false
  }
}

watch(
  () => [overviewState.targetDate, overviewState.sportId, overviewState.teamId],
  async () => {
    await loadOverview()
  },
)

watch(
  () => builderPayload.value ? JSON.stringify(builderPayload.value) : 'no-preview',
  async () => {
    await generatePreview()
  },
)

watch(
  () => overviewState.sportId,
  () => {
    if (isSportFilterLocked.value) {
      overviewState.sportId = resolveInitialSportFilterValue(authStore.currentUser?.sport_id)
    }
    overviewState.teamId = retainVisibleTeamId(overviewState.teamId, overviewTeams.value)
  },
)

watch(
  () => builderState.sportId,
  () => {
    if (isSportFilterLocked.value) {
      builderState.sportId = resolveInitialSportFilterValue(authStore.currentUser?.sport_id)
    }
    builderState.teamId = retainVisibleTeamId(builderState.teamId, builderTeams.value)
  },
)

watch(
  () => builderState.singleDate,
  (nextDate) => {
    if (builderState.scheduleMode === 'single_day' && nextDate) {
      builderState.repeatWeekdays = [weekdayFromDate(nextDate)]
    }
  },
)

watch(
  () => filteredOverviewGroups.value.map((group: any) => group.assignment_ids.join('-')).join('|'),
  () => {
    if (
      selectedOverviewGroupKey.value
      && !filteredOverviewGroups.value.some((group: any) => group.assignment_ids.join('-') === selectedOverviewGroupKey.value)
    ) {
      selectedOverviewGroupKey.value = null
      confirmDeleteGroupKey.value = null
    }
  },
)

onMounted(hydrate)

function weekdayFromDate(dateString: string) {
  const [year, month, day] = dateString.split('-').map(Number)
  const weekday = new Date(year, (month || 1) - 1, day || 1).getDay()
  return weekday === 0 ? 7 : weekday
}

function weekdayLabelFromDate(dateString: string) {
  const weekday = weekdayFromDate(dateString)
  return REPEAT_WEEKDAY_OPTIONS.find((option) => option.value === weekday)?.label || '未识别星期'
}
</script>

<template>
  <AppShell>
    <div class="assignment-page">
      <section class="panel control-panel">
        <div class="control-head">
          <div>
            <p class="eyebrow">计划分配工作台</p>
            <h3>{{ activeView === 'builder' ? '先完成新分配，再切回现有计划查看结果' : '先看现状，再决定是否补齐未分配对象' }}</h3>
          </div>
          <div class="view-switch" role="tablist" aria-label="计划分配视图切换">
            <button
              v-for="button in viewButtons"
              :key="button.key"
              class="view-btn"
              :class="{ active: activeView === button.key }"
              type="button"
              @click="activeView = button.key"
            >
              {{ button.label }}
            </button>
          </div>
        </div>

        <div class="toolbar-fields">
          <template v-if="activeView === 'overview'">
            <label class="field compact">
              <span>查看日期</span>
              <input v-model="overviewState.targetDate" type="date" class="text-input" />
            </label>
            <label class="field compact">
              <span>项目</span>
              <select v-model.number="overviewState.sportId" class="text-input" :disabled="isSportFilterLocked">
                <option :value="0">全部项目</option>
                <option v-for="sport in sports" :key="sport.id" :value="sport.id">{{ sport.name }}</option>
              </select>
            </label>
            <label class="field compact">
              <span>队伍</span>
              <select v-model.number="overviewState.teamId" class="text-input">
                <option :value="0">全部队伍</option>
                <option v-for="team in overviewTeams" :key="team.id" :value="team.id">{{ team.name }}</option>
              </select>
            </label>
          </template>

          <template v-else>
            <label class="field compact">
              <span>项目</span>
              <select v-model.number="builderState.sportId" class="text-input" :disabled="isSportFilterLocked">
                <option :value="0">全部项目</option>
                <option v-for="sport in sports" :key="sport.id" :value="sport.id">{{ sport.name }}</option>
              </select>
            </label>
            <label class="field compact">
              <span>队伍</span>
              <select v-model.number="builderState.teamId" class="text-input">
                <option :value="0">全部队伍</option>
                <option v-for="team in builderTeams" :key="team.id" :value="team.id">{{ team.name }}</option>
              </select>
            </label>
            <label class="field search-field">
              <span>姓名搜索</span>
              <input v-model="builderState.keyword" class="text-input" placeholder="输入姓名、队伍或项目关键词" />
            </label>
          </template>
        </div>
      </section>

      <AssignmentOverviewPane
        v-if="activeView === 'overview'"
        :overview="overview"
        :groups="filteredOverviewGroups"
        :unassigned-athletes="filteredOverviewUnassignedAthletes"
        :selected-group-key="selectedOverviewGroupKey"
        :selected-assignments-by-group-key="selectedAssignmentsByGroupKey"
        :confirm-delete-group-key="confirmDeleteGroupKey"
        :target-date="overviewState.targetDate"
        :cancelling="cancelling"
        @select-group="selectOverviewGroup"
        @switch-to-builder="activeView = 'builder'"
        @toggle-assignment="toggleOverviewAssignment"
        @request-cancel="requestDeleteGroupAssignments"
        @reset-cancel="resetDeleteFlow"
        @confirm-cancel="cancelSelectedGroupAssignments"
      />

      <section v-else class="assignment-layout">
        <div class="wizard-panel">
          <section class="panel section-block">
            <div class="section-head">
              <div>
                <p class="eyebrow">第一步</p>
                <h3>选择范围与队员</h3>
              </div>
              <span class="muted">已选 {{ builderState.athleteIds.length }} 人</span>
            </div>

            <div class="action-row">
              <button class="ghost-btn slim" type="button" @click="selectAllFilteredAthletes">全选当前筛选结果</button>
              <button class="ghost-btn slim dark-btn" type="button" @click="selectFilteredUnassignedAthletes">选择当前未分配</button>
              <button class="ghost-btn slim" type="button" :disabled="!builderState.athleteIds.length" @click="clearSelectedAthletes">清空已选</button>
              <label class="checkbox-row">
                <input v-model="builderState.selectedOnly" type="checkbox" />
                <span>仅看已选</span>
              </label>
            </div>

            <p class="muted helper-copy">
              当前可选 {{ builderBaseAthletes.length }} 人。先用上方项目、队伍和姓名搜索缩小范围，再手动点选或批量加入。
            </p>

            <div class="athlete-grid">
              <button
                v-for="athlete in visibleBuilderAthletes"
                :key="athlete.id"
                class="athlete-card"
                :class="{
                  active: builderState.athleteIds.includes(athlete.id),
                  'athlete-card--assigned': (assignedCountsByAthleteId.get(athlete.id) ?? 0) > 0,
                  'athlete-card--unassigned': unassignedAthleteIdSet.has(athlete.id),
                }"
                type="button"
                @click="toggleAthlete(athlete.id)"
              >
                <div class="athlete-card-head">
                  <strong>{{ athlete.full_name }}</strong>
                  <span v-if="builderState.athleteIds.includes(athlete.id)" class="state-pill state-pill--selected">已选</span>
                  <span v-else-if="(assignedCountsByAthleteId.get(athlete.id) ?? 0) > 0" class="state-pill state-pill--assigned">已有安排</span>
                  <span v-else class="state-pill state-pill--unassigned">未分配</span>
                </div>
                <span>{{ athlete.team?.name || '未分队' }}</span>
                <small>{{ getAssignedPlanHint(athlete.id) }}</small>
              </button>
            </div>
          </section>

          <section class="panel section-block">
            <div class="section-head">
              <div>
                <p class="eyebrow">第二步</p>
                <h3>选择训练模板</h3>
              </div>
            </div>

            <label class="field">
              <span>训练模板</span>
              <select v-model.number="builderState.templateId" class="text-input">
                <option :value="0">请选择训练模板</option>
                <option v-for="template in templates" :key="template.id" :value="template.id">{{ template.name }}</option>
              </select>
            </label>
            <p class="muted helper-copy">
              {{ selectedTemplate ? `${selectedTemplate.name}${selectedTemplate.description ? `：${selectedTemplate.description}` : ''}` : '先选模板，右侧再查看折叠后的模块动作摘要。' }}
            </p>
          </section>

          <section class="panel section-block">
            <div class="section-head">
              <div>
                <p class="eyebrow">第三步</p>
                <h3>设置日期与执行日</h3>
              </div>
            </div>

            <div class="schedule-mode-switch" role="tablist" aria-label="日期模式切换">
              <button
                v-for="button in scheduleModeButtons"
                :key="button.key"
                class="schedule-mode-btn"
                :class="{ active: builderState.scheduleMode === button.key }"
                type="button"
                @click="setScheduleMode(button.key)"
              >
                {{ button.label }}
              </button>
            </div>

            <div v-if="builderState.scheduleMode === 'single_day'" class="grid two">
              <label class="field">
                <span>训练日期</span>
                <input v-model="builderState.singleDate" type="date" class="text-input" />
              </label>
              <div class="info-card">
                <strong>自动执行日</strong>
                <span>{{ weekdayLabelFromDate(builderState.singleDate) }}</span>
              </div>
            </div>

            <div v-else class="grid three">
              <label class="field">
                <span>开始日期</span>
                <input v-model="builderState.startDate" type="date" class="text-input" />
              </label>
              <label class="field">
                <span>结束日期</span>
                <input v-model="builderState.endDate" type="date" class="text-input" />
              </label>
              <label class="field">
                <span>分配备注</span>
                <input v-model="builderState.notes" class="text-input" placeholder="例如：第一周主课、比赛周恢复" />
              </label>
            </div>

            <label v-if="builderState.scheduleMode === 'single_day'" class="field">
              <span>分配备注</span>
              <input v-model="builderState.notes" class="text-input" placeholder="例如：赛前唤醒、恢复课" />
            </label>

            <div v-if="builderState.scheduleMode === 'weekly_repeat'" class="field">
              <span>每周执行日</span>
              <div class="weekday-picker">
                <button
                  v-for="option in REPEAT_WEEKDAY_OPTIONS"
                  :key="option.value"
                  class="weekday-chip"
                  :class="{ active: builderState.repeatWeekdays.includes(option.value) }"
                  type="button"
                  @click="toggleRepeatWeekday(option.value)"
                >
                  {{ option.label }}
                </button>
              </div>
              <small class="helper-text">当前选择：{{ formatRepeatWeekdays(builderState.repeatWeekdays) }}</small>
            </div>

            <p class="muted helper-copy">{{ scheduleHint }}</p>
          </section>

          <section class="panel section-block">
            <div class="section-head">
              <div>
                <p class="eyebrow">第四步</p>
                <h3>确认本次分配</h3>
              </div>
            </div>

            <div class="confirm-grid">
              <div class="confirm-card">
                <span>本次对象</span>
                <strong>{{ builderState.athleteIds.length }} 人</strong>
              </div>
              <div class="confirm-card">
                <span>已有后续计划</span>
                <strong>{{ selectedWithExistingPlans }} 人</strong>
              </div>
              <div class="confirm-card">
                <span>当前未分配</span>
                <strong>{{ selectedUnassignedCount }} 人</strong>
              </div>
            </div>

            <div class="confirm-details">
              <div>
                <strong>涉及队伍</strong>
                <span>{{ selectedTeamNames.length ? selectedTeamNames.join('、') : '待选择队员' }}</span>
              </div>
              <div>
                <strong>日期摘要</strong>
                <span>{{ scheduleSummary }}</span>
              </div>
              <div>
                <strong>风险提示</strong>
                <span v-if="previewHasManualControl">存在训练时需现场控制的动作，请优先核对右侧提示。</span>
                <span v-else-if="builderValidationMessage">{{ builderValidationMessage }}</span>
                <span v-else>当前可以提交，右侧会保留主按钮用于最终确认。</span>
              </div>
            </div>

            <p v-if="loadingPreview" class="muted helper-copy">正在生成最新分配预览...</p>
          </section>
        </div>

        <AssignmentPreviewPanel
          :preview="preview"
          :selected-template="selectedTemplate"
          :selected-athletes="selectedAthletes"
          :schedule-summary="scheduleSummary"
          :schedule-hint="scheduleHint"
          :selected-team-names="selectedTeamNames"
          :selected-with-existing-plans="selectedWithExistingPlans"
          :selected-unassigned-count="selectedUnassignedCount"
          :notes="builderState.notes"
          :can-submit="builderCanSubmit"
          :submitting="submitting"
          :validation-message="builderValidationMessage"
          @submit="submitAssignments"
        />
      </section>
    </div>
  </AppShell>
</template>

<style scoped>
.assignment-page,
.control-panel,
.assignment-layout,
.wizard-panel,
.section-block,
.athlete-grid,
.weekday-picker,
.confirm-grid,
.confirm-details {
  display: grid;
  gap: 16px;
}

.assignment-page {
  gap: 18px;
}

.control-panel {
  padding: 18px;
}

.control-head,
.toolbar-fields,
.section-head,
.action-row,
.view-switch,
.schedule-mode-switch,
.athlete-card-head {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
}

.toolbar-fields {
  justify-content: flex-start;
}

.view-switch,
.schedule-mode-switch {
  padding: 4px;
  border-radius: 999px;
  background: rgba(14, 116, 144, 0.08);
}

.view-btn,
.schedule-mode-btn {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  background: transparent;
  color: var(--text-soft);
  font-weight: 700;
}

.view-btn.active,
.schedule-mode-btn.active {
  background: white;
  color: #0f766e;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
}

.field {
  display: grid;
  gap: 6px;
}

.compact {
  min-width: 190px;
}

.search-field {
  min-width: min(420px, 100%);
  flex: 1 1 320px;
}

.assignment-layout {
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, 0.85fr);
  align-items: start;
}

.wizard-panel {
  align-content: start;
}

.section-block {
  padding: 18px;
}

.eyebrow,
.muted,
.helper-copy,
.helper-text,
.field span,
.confirm-card span,
.confirm-details span,
.athlete-card span,
.athlete-card small,
.info-card span {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
}

.helper-copy {
  line-height: 1.5;
}

.athlete-grid {
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}

.athlete-card,
.confirm-card,
.info-card {
  display: grid;
  gap: 6px;
  text-align: left;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
}

.athlete-card {
  border: 1px solid transparent;
  gap: 4px;
  min-height: 88px;
  padding: 10px 12px;
  border-radius: 12px;
  cursor: pointer;
  transition:
    background-color 0.18s ease,
    border-color 0.18s ease,
    box-shadow 0.18s ease;
}

.athlete-card-head {
  gap: 8px;
  flex-wrap: nowrap;
}

.athlete-card strong {
  min-width: 0;
  font-size: 16px;
  line-height: 1.25;
  overflow-wrap: anywhere;
}

.athlete-card > span,
.athlete-card small {
  font-size: 12px;
  line-height: 1.35;
}

.athlete-card:hover {
  border-color: rgba(15, 118, 110, 0.2);
}

.athlete-card.active {
  background: #d1fae5;
  border-color: rgba(15, 118, 110, 0.22);
  box-shadow: 0 10px 22px rgba(15, 23, 42, 0.06);
}

.athlete-card--assigned {
  background: rgba(239, 246, 255, 0.82);
}

.athlete-card--unassigned:not(.active) {
  background: rgba(240, 253, 250, 0.8);
}

.state-pill {
  flex: 0 0 auto;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.2;
}

.state-pill--selected {
  background: rgba(15, 118, 110, 0.14);
  color: var(--primary);
}

.state-pill--assigned {
  background: rgba(59, 130, 246, 0.14);
  color: #1d4ed8;
}

.state-pill--unassigned {
  background: rgba(15, 118, 110, 0.08);
  color: #0f766e;
}

.checkbox-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--text-soft);
  font-size: 13px;
}

.dark-btn {
  background: #0f172a;
  color: white;
}

.grid.two,
.grid.three {
  display: grid;
  gap: 12px;
}

.grid.two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.info-card {
  align-content: center;
  background: rgba(240, 253, 250, 0.86);
}

.weekday-picker {
  grid-template-columns: repeat(7, minmax(0, 1fr));
}

.weekday-chip {
  min-height: 42px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  color: var(--text);
  font: inherit;
  cursor: pointer;
  transition:
    background-color 0.16s ease,
    border-color 0.16s ease,
    color 0.16s ease;
}

.weekday-chip.active {
  background: rgba(15, 118, 110, 0.12);
  border-color: rgba(15, 118, 110, 0.26);
  color: var(--primary);
}

.confirm-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.confirm-card strong {
  font-size: 28px;
}

.confirm-details {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.confirm-details > div {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.74);
}

.confirm-details strong {
  display: block;
}

@media (max-width: 1280px) {
  .assignment-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .grid.two,
  .grid.three,
  .weekday-picker,
  .confirm-grid,
  .confirm-details {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 560px) {
  .athlete-grid {
    grid-template-columns: 1fr;
  }
}
</style>
