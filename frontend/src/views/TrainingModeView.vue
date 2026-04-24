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
        <label class="compact-field compact-field--date">
          <span class="compact-label">训练日期</span>
          <input :value="trainingStore.sessionDate" class="text-input header-filter-control" type="date" @input="handleDateInput" />
        </label>
        <label class="compact-field compact-field--team">
          <span class="compact-label">队伍</span>
          <select :value="selectedTeamFilter" class="text-input header-filter-control header-team-select" @input="handleTeamFilterInput">
            <option v-for="team in teamOptions" :key="team.id" :value="team.id">{{ team.name }}</option>
          </select>
        </label>
      </div>
    </template>

    <div class="training-mode-layout">
      <TrainingModeSidebar
        :athletes="filteredAthletes"
        :selected-athlete-id="trainingStore.selectedAthleteId"
        :assignments="trainingStore.assignments"
        :preview-assignment-id="trainingStore.previewAssignmentId"
        @update-athlete="trainingStore.selectedAthleteId = $event"
        @open-plan="openPlanById"
      />

      <TrainingSessionOverview :assignment="selectedPreview" />

      <section class="panel help-panel">
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
  grid-template-columns: 320px 1.2fr 320px;
  gap: 18px;
  height: 100%;
  min-height: 0;
}

.header-filter-bar {
  display: flex;
  align-items: flex-end;
  flex-wrap: nowrap;
  gap: 12px;
  min-width: 0;
}

.compact-field {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.compact-field--date {
  width: 170px;
}

.compact-field--team {
  width: 220px;
}

.compact-label {
  margin: 0;
  font-size: 12px;
  line-height: 1.1;
  color: var(--text-soft);
}

.header-filter-control {
  min-height: 42px;
  border-radius: 14px;
}

.header-team-select {
  appearance: none;
  padding-right: 36px;
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

@media (max-width: 1360px) {
  .training-mode-layout {
    grid-template-columns: 1fr;
    height: auto;
  }
}

@media (max-width: 720px) {
  .header-filter-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .compact-field--date,
  .compact-field--team {
    width: 100%;
  }
}
</style>
