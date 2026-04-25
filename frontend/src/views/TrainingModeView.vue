<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import TrainingShell from '@/components/layout/TrainingShell.vue'
import TrainingDraftRestoreModal from '@/components/training/TrainingDraftRestoreModal.vue'
import TrainingModeSidebar from '@/components/training/TrainingModeSidebar.vue'
import TrainingSessionOverview from '@/components/training/TrainingSessionOverview.vue'
import { useTrainingStore } from '@/stores/training'
import { todayString } from '@/utils/date'

const router = useRouter()
const trainingStore = useTrainingStore()
const loading = ref(false)
const restoreDraft = ref<any | null>(null)
const restoreBusy = ref(false)
const ALL_TEAMS_VALUE = '__all__'
const UNASSIGNED_TEAM_VALUE = '__unassigned__'
const selectedTeamFilter = ref(ALL_TEAMS_VALUE)

const selectedPreview = computed(
  () => trainingStore.assignments.find((assignment) => assignment.id === trainingStore.previewAssignmentId) || null,
)
const selectedAthlete = computed(
  () => trainingStore.athletes.find((athlete) => athlete.id === trainingStore.selectedAthleteId) || null,
)
const selectedAthleteName = computed(() => selectedAthlete.value?.full_name || '')
const displaySessionDate = computed(() => formatSessionDate(trainingStore.sessionDate))

const teamOptions = computed(() => {
  const teams = trainingStore.athletes
    .filter((athlete) => athlete.team?.id)
    .map((athlete) => ({
      id: String(athlete.team.id),
      name: athlete.team.name,
    }))

  const uniqueTeams = teams.filter((team, index, source) => source.findIndex((current) => current.id === team.id) === index)
  const hasUnassignedAthletes = trainingStore.athletes.some((athlete) => !athlete.team?.id)
  const options = [...uniqueTeams]

  if (hasUnassignedAthletes) {
    options.push({ id: UNASSIGNED_TEAM_VALUE, name: '未分队' })
  }

  if (options.length <= 1) {
    return options
  }

  return [{ id: ALL_TEAMS_VALUE, name: '全部队伍' }, ...options]
})

const selectedTeamLabel = computed(() => {
  const matched = teamOptions.value.find((team) => team.id === selectedTeamFilter.value)
  return matched?.name || '队伍'
})

const filteredAthletes = computed(() => {
  if (selectedTeamFilter.value === ALL_TEAMS_VALUE) {
    return trainingStore.athletes
  }

  if (selectedTeamFilter.value === UNASSIGNED_TEAM_VALUE) {
    return trainingStore.athletes.filter((athlete) => !athlete.team?.id)
  }

  return trainingStore.athletes.filter((athlete) => String(athlete.team?.id || '') === selectedTeamFilter.value)
})

async function hydrate() {
  if (!trainingStore.sessionDate) {
    trainingStore.sessionDate = todayString()
  }
  await trainingStore.hydrateAthletes(trainingStore.sessionDate)
  if (trainingStore.selectedAthleteId) {
    await loadPlans()
  }
  maybePromptDraftRestore()
}

async function loadPlans() {
  if (!trainingStore.selectedAthleteId || !trainingStore.sessionDate) {
    trainingStore.assignments = []
    trainingStore.previewAssignmentId = 0
    return
  }

  loading.value = true
  try {
    await Promise.all([
      trainingStore.loadPlans(trainingStore.selectedAthleteId, trainingStore.sessionDate),
      trainingStore.hydrateAthletes(trainingStore.sessionDate),
    ])
  } finally {
    loading.value = false
  }
}

async function openPlanById(assignmentId: number) {
  trainingStore.setPreviewAssignment(assignmentId)
  const session = await trainingStore.openPlanSession(assignmentId, trainingStore.sessionDate)
  if (session.id) {
    router.push({ name: 'training-session', params: { sessionId: session.id } })
    return
  }

  router.push({
    name: 'training-session',
    query: {
      assignmentId: String(assignmentId),
      athleteId: String(trainingStore.selectedAthleteId),
      sessionDate: trainingStore.sessionDate,
    },
  })
}

function maybePromptDraftRestore() {
  restoreDraft.value = trainingStore.getLatestRecoverableDraft()
}

async function continueDraftRestore() {
  if (!restoreDraft.value) return

  const draft = restoreDraft.value
  restoreBusy.value = true
  try {
    trainingStore.selectedAthleteId = draft.athlete_id
    trainingStore.sessionDate = draft.session_date
    trainingStore.setPreviewAssignment(draft.assignment_id)

    if (draft.session_id) {
      await router.push({
        name: 'training-session',
        params: { sessionId: draft.session_id },
        query: {
          resumeDraft: '1',
          resumeTarget: 'overview',
          draftSessionKey: draft.session_key,
        },
      })
      return
    }

    await router.push({
      name: 'training-session',
      query: {
        assignmentId: String(draft.assignment_id),
        athleteId: String(draft.athlete_id),
        sessionDate: draft.session_date,
        resumeDraft: '1',
        resumeTarget: 'overview',
        draftSessionKey: draft.session_key,
      },
    })
  } finally {
    restoreBusy.value = false
  }
}

function discardDraftRestore() {
  if (!restoreDraft.value) return
  trainingStore.discardDraft(restoreDraft.value.session_key)
  maybePromptDraftRestore()
}

function syncTeamFilter() {
  const options = teamOptions.value
  if (!options.length) {
    selectedTeamFilter.value = ALL_TEAMS_VALUE
    return
  }

  const currentExists = options.some((option) => option.id === selectedTeamFilter.value)
  if (currentExists) return

  selectedTeamFilter.value = options.length === 1 ? options[0].id : ALL_TEAMS_VALUE
}

function syncSelectedAthleteForFilter() {
  const visibleAthletes = filteredAthletes.value
  if (!visibleAthletes.length) {
    trainingStore.selectedAthleteId = 0
    trainingStore.assignments = []
    trainingStore.previewAssignmentId = 0
    return
  }

  const selectedStillVisible = visibleAthletes.some((athlete) => athlete.id === trainingStore.selectedAthleteId)
  if (!selectedStillVisible) {
    trainingStore.selectedAthleteId = visibleAthletes[0].id
  }
}

function handleDateInput(event: Event) {
  trainingStore.sessionDate = (event.target as HTMLInputElement).value
}

function handleTeamFilterInput(event: Event) {
  selectedTeamFilter.value = (event.target as HTMLSelectElement).value
}

function formatSessionDate(value: string) {
  if (!value) return '训练日期'

  const parts = value.split('-')
  if (parts.length !== 3) return value

  const [year, month, day] = parts
  const monthNumber = Number(month)
  const dayNumber = Number(day)
  if (!year || Number.isNaN(monthNumber) || Number.isNaN(dayNumber)) return value

  return `${year}年${monthNumber}月${dayNumber}日`
}

watch(
  () => [trainingStore.selectedAthleteId, trainingStore.sessionDate],
  async ([athleteId, sessionDate], [prevAthleteId, prevDate]) => {
    if (!athleteId || !sessionDate) return
    if (athleteId === prevAthleteId && sessionDate === prevDate) return
    await loadPlans()
  },
)

watch(
  () => trainingStore.athletes,
  () => {
    syncTeamFilter()
    syncSelectedAthleteForFilter()
  },
  { immediate: true, deep: true },
)

watch(
  () => selectedTeamFilter.value,
  () => {
    syncSelectedAthleteForFilter()
  },
)

onMounted(hydrate)
</script>

<template>
  <TrainingShell>
    <TrainingDraftRestoreModal
      :open="!!restoreDraft"
      :draft="restoreDraft"
      :busy="restoreBusy"
      @continue-restore="continueDraftRestore"
      @discard-restore="discardDraftRestore"
    />

    <template #header-filters>
      <div class="header-filter-bar">
        <div class="compact-field compact-field--date">
          <span class="compact-label">训练日期</span>
          <div class="filter-pill-shell">
            <button class="filter-pill date-filter" type="button" tabindex="-1" aria-hidden="true">
              <span class="filter-pill-text">{{ displaySessionDate }}</span>
            </button>
            <input
              :value="trainingStore.sessionDate"
              class="header-filter-control filter-native-control filter-native-date"
              type="date"
              aria-label="训练日期"
              title="训练日期"
              @input="handleDateInput"
            />
          </div>
        </div>
        <div class="compact-field compact-field--team">
          <span class="compact-label">队伍</span>
          <div class="filter-pill-shell">
            <button class="filter-pill team-filter" type="button" tabindex="-1" aria-hidden="true">
              <span class="filter-pill-text">{{ selectedTeamLabel }}</span>
            </button>
            <select
              :value="selectedTeamFilter"
              class="header-filter-control filter-native-control filter-native-team"
              aria-label="队伍筛选"
              title="队伍筛选"
              @input="handleTeamFilterInput"
            >
              <option v-for="team in teamOptions" :key="team.id" :value="team.id">{{ team.name }}</option>
            </select>
          </div>
        </div>
      </div>
    </template>

    <div class="training-mode-layout">
      <TrainingModeSidebar
        class="layout-sidebar"
        :athletes="filteredAthletes"
        :selected-athlete-id="trainingStore.selectedAthleteId"
        :assignments="trainingStore.assignments"
        :preview-assignment-id="trainingStore.previewAssignmentId"
        @update-athlete="trainingStore.selectedAthleteId = $event"
        @open-plan="openPlanById"
      />

      <TrainingSessionOverview class="layout-overview" :assignment="selectedPreview" :athlete-name="selectedAthleteName" />

      <section class="panel help-panel layout-help">
        <p class="section-title">2. 训练提示</p>
        <strong v-if="loading">正在同步当天训练状态...</strong>
        <template v-else-if="selectedPreview">
          <strong>当前选中：{{ selectedPreview.template.name }}</strong>
          <span>
            点击左侧计划卡片会直接打开当天训练记录。红色表示未开始，黄色表示仍有未完成动作，绿色表示当天计划已经完成。
          </span>
        </template>
        <template v-else>
          <strong>先选择日期、队伍和队员，再点击左侧计划开始录入。</strong>
          <span>列表里的颜色会直接提醒教练今天哪些人还没开始，哪些人做了一半，哪些人已经全部完成。</span>
        </template>
      </section>
    </div>
  </TrainingShell>
</template>

<style scoped>
.training-mode-layout {
  display: grid;
  grid-template-columns: minmax(280px, 320px) minmax(0, 1.15fr) minmax(280px, 320px);
  grid-template-areas: 'sidebar overview help';
  gap: 18px;
  height: 100%;
  min-height: 0;
}

.training-mode-layout > * {
  min-width: 0;
}

.layout-sidebar {
  grid-area: sidebar;
  min-height: 0;
}

.layout-overview {
  grid-area: overview;
  min-height: 0;
}

.layout-help {
  grid-area: help;
  min-height: 0;
}

.header-filter-bar {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}

.compact-field {
  display: block;
  flex: 0 0 auto;
  min-width: 0;
  max-width: 100%;
}

.compact-field--date {
  flex-basis: 160px;
  width: 160px;
}

.compact-field--team {
  flex-basis: 160px;
  width: 160px;
}

.filter-pill-shell {
  position: relative;
  width: 100%;
}

.compact-label {
  margin: 0;
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.header-filter-control {
  display: inline-block;
  width: 100%;
  min-width: 0;
  max-width: 100%;
}

.filter-native-control {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  min-height: 100%;
  margin: 0;
  border: 0;
  opacity: 0;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
}

.filter-pill {
  min-width: 120px;
  max-width: 180px;
  width: 100%;
  height: 34px;
  min-height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 12px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: white;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  box-sizing: border-box;
  color: var(--text);
  pointer-events: none;
}

.filter-pill-text {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 14px;
  font-weight: 500;
  line-height: 1;
  text-align: center;
  white-space: nowrap;
}

.filter-pill-shell:focus-within .filter-pill {
  border-color: rgba(15, 118, 110, 0.42);
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.12);
}

.help-panel {
  display: grid;
  gap: 10px;
  align-content: start;
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.center-column {
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.help-panel span,
.section-title {
  margin: 0;
  color: var(--muted);
}

@media (min-width: 768px) and (max-width: 1199px) {
  .training-mode-layout {
    grid-template-columns: 240px minmax(0, 1fr) 240px;
    grid-template-areas: 'sidebar overview help';
    gap: 12px;
    height: 100%;
  }

  .header-filter-bar {
    gap: 8px;
  }

  .compact-field--date,
  .compact-field--team {
    flex-basis: 155px;
    width: 155px;
  }

  .filter-pill {
    min-width: 130px;
    max-width: 165px;
    height: 32px;
    min-height: 32px;
    padding: 0 10px;
  }

  .filter-pill-text {
    font-size: 14px;
  }

  .help-panel {
    gap: 8px;
  }
}

@media (min-width: 768px) and (max-width: 1050px) {
  .compact-field--date,
  .compact-field--team {
    flex-basis: 150px;
    width: 150px;
  }

  .filter-pill {
    min-width: 125px;
    max-width: 155px;
  }
}

@media (max-width: 767px) {
  .training-mode-layout {
    grid-template-columns: 1fr;
    grid-template-areas:
      'sidebar'
      'overview'
      'help';
    height: auto;
  }

  .header-filter-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .compact-field {
    display: grid;
    gap: 4px;
  }

  .filter-pill {
    width: 100%;
    min-width: 0;
    max-width: none;
  }

  .compact-field--date,
  .compact-field--team {
    flex-basis: auto;
    width: 100%;
  }

  .compact-label {
    position: static;
    width: auto;
    height: auto;
    padding: 0;
    margin: 0;
    overflow: visible;
    clip: auto;
    white-space: normal;
    font-size: 12px;
    line-height: 1.1;
    color: var(--text-soft);
  }
}

</style>
