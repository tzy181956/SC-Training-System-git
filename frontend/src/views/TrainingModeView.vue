<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import TrainingShell from '@/components/layout/TrainingShell.vue'
import TrainingDraftRestoreModal from '@/components/training/TrainingDraftRestoreModal.vue'
import TrainingHeaderFilters from '@/components/training/TrainingHeaderFilters.vue'
import TrainingModeSidebar from '@/components/training/TrainingModeSidebar.vue'
import { useTeamFilter } from '@/composables/useTeamFilter'
import TrainingSessionOverview from '@/components/training/TrainingSessionOverview.vue'
import { useTrainingStore } from '@/stores/training'
import { todayString } from '@/utils/date'

const router = useRouter()
const route = useRoute()
const trainingStore = useTrainingStore()
const loading = ref(false)
const restoreDraft = ref<any | null>(null)
const restoreBusy = ref(false)
const selectedAthleteIdRef = computed({
  get: () => trainingStore.selectedAthleteId,
  set: (value: number) => {
    trainingStore.selectedAthleteId = value
  },
})

const selectedPreview = computed(
  () => trainingStore.assignments.find((assignment) => assignment.id === trainingStore.previewAssignmentId) || null,
)
const selectedAthlete = computed(
  () => trainingStore.athletes.find((athlete) => athlete.id === trainingStore.selectedAthleteId) || null,
)
const selectedAthleteName = computed(() => selectedAthlete.value?.full_name || '')
const displaySessionDate = computed(() => formatSessionDate(trainingStore.sessionDate))
const {
  selectedSportFilter,
  sportOptions,
  selectedSportLabel,
  selectedTeamFilter,
  teamOptions,
  selectedTeamLabel,
  filteredAthletes,
  syncSportFilter,
  syncTeamFilter,
  syncSelectedAthleteForFilter,
} = useTeamFilter({
  athletes: () => trainingStore.athletes,
  selectedAthleteId: selectedAthleteIdRef,
})

async function hydrate() {
  const requestedSessionDate = typeof route.query.sessionDate === 'string' ? route.query.sessionDate : ''
  if (requestedSessionDate) {
    trainingStore.sessionDate = requestedSessionDate
  } else if (!trainingStore.sessionDate) {
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

function handleDateInput(value: string) {
  trainingStore.sessionDate = value
}

function handleSportFilterInput(value: string) {
  selectedSportFilter.value = value
}

function handleTeamFilterInput(value: string) {
  selectedTeamFilter.value = value
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
    syncSportFilter()
    syncTeamFilter()
    syncSelectedAthleteForFilter(() => {
      trainingStore.selectedAthleteId = 0
      trainingStore.assignments = []
      trainingStore.previewAssignmentId = 0
    })
  },
  { immediate: true, deep: true },
)

watch(
  () => [selectedSportFilter.value, selectedTeamFilter.value],
  () => {
    syncTeamFilter()
    syncSelectedAthleteForFilter(() => {
      trainingStore.selectedAthleteId = 0
      trainingStore.assignments = []
      trainingStore.previewAssignmentId = 0
    })
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
      <TrainingHeaderFilters
        :session-date="trainingStore.sessionDate"
        :session-date-label="displaySessionDate"
        :selected-sport-value="selectedSportFilter"
        :selected-sport-label="selectedSportLabel"
        :sport-options="sportOptions"
        :selected-team-value="selectedTeamFilter"
        :selected-team-label="selectedTeamLabel"
        :team-options="teamOptions"
        sport-field-label="训练项目"
        sport-aria-label="训练项目筛选"
        @update:session-date="handleDateInput"
        @update:sport-value="handleSportFilterInput"
        @update:team-value="handleTeamFilterInput"
      />
    </template>

    <div class="training-mode-layout training-three-column-layout">
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

      <section class="panel help-panel layout-help training-scroll-column">
        <p class="section-title">2. 训练提示</p>
        <strong v-if="loading">正在同步当天训练状态...</strong>
        <template v-else-if="selectedPreview">
          <strong>当前选中：{{ selectedPreview.template.name }}</strong>
          <span>
            点击左侧计划卡片会直接打开当天训练记录。红色表示未开始，黄色表示仍有未完成动作，绿色表示当天计划已经完成。
          </span>
        </template>
        <template v-else>
          <strong>先选择日期、项目、队伍和队员，再点击左侧计划开始录入。</strong>
          <span>列表里的颜色会直接提醒教练今天哪些人还没开始，哪些人做了一半，哪些人已经全部完成。</span>
        </template>
      </section>
    </div>
  </TrainingShell>
</template>

<style scoped>
.training-mode-layout {
  --training-panel-min-width: 280px;
  grid-template-areas: 'sidebar overview help';
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

.help-panel {
  display: grid;
  gap: 10px;
  align-content: start;
}

.help-panel span,
.section-title {
  margin: 0;
  color: var(--muted);
}

@media (min-width: 768px) and (max-width: 1199px) {
  .help-panel {
    gap: 8px;
  }
}

@media (max-width: 767px) {
  .training-mode-layout {
    grid-template-areas:
      'sidebar'
      'overview'
      'help';
  }
}

</style>
