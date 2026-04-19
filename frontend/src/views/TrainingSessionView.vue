<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import TrainingShell from '@/components/layout/TrainingShell.vue'
import TrainingModeSidebar from '@/components/training/TrainingModeSidebar.vue'
import TrainingSessionOverview from '@/components/training/TrainingSessionOverview.vue'
import TrainingSetPanel from '@/components/training/TrainingSetPanel.vue'
import { useTrainingStore } from '@/stores/training'
import { todayString } from '@/utils/date'

const route = useRoute()
const router = useRouter()
const trainingStore = useTrainingStore()
const activeItemId = ref<number | null>(null)
const latestSuggestion = ref<any | null>(null)
const ALL_TEAMS_VALUE = '__all__'
const UNASSIGNED_TEAM_VALUE = '__unassigned__'
const selectedTeamFilter = ref(ALL_TEAMS_VALUE)

const activeItem = computed(
  () => trainingStore.session?.items?.find((item: any) => item.id === activeItemId.value) || trainingStore.session?.items?.[0] || null,
)
const selectedAssignment = computed(
  () => trainingStore.assignments.find((item) => item.id === trainingStore.previewAssignmentId) || null,
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

function findNextPendingItemId(currentItemId?: number | null) {
  const items = trainingStore.session?.items || []
  if (!items.length) return null

  const currentIndex = items.findIndex((item: any) => item.id === currentItemId)
  const remainingItems = currentIndex >= 0 ? items.slice(currentIndex + 1) : items
  const nextPending = remainingItems.find((item: any) => item.status !== 'completed')
  if (nextPending) return nextPending.id

  const firstPending = items.find((item: any) => item.status !== 'completed')
  return firstPending?.id || null
}

async function hydrate() {
  if (!trainingStore.sessionDate) {
    trainingStore.sessionDate = todayString()
  }
  if (!trainingStore.athletes.length) {
    await trainingStore.hydrateAthletes(trainingStore.sessionDate)
  }

  const sessionId = Number(route.params.sessionId)
  if (!sessionId) return

  const session = await trainingStore.loadSession(sessionId)
  trainingStore.selectedAthleteId = session.athlete_id
  trainingStore.sessionDate = session.session_date
  await Promise.all([
    trainingStore.loadPlans(session.athlete_id, session.session_date),
    trainingStore.hydrateAthletes(session.session_date),
  ])
  trainingStore.setPreviewAssignment(session.assignment_id)
  activeItemId.value = findNextPendingItemId() ?? (session.items?.[0]?.id || null)
}

async function loadPlans() {
  if (!trainingStore.selectedAthleteId || !trainingStore.sessionDate) return
  await Promise.all([
    trainingStore.loadPlans(trainingStore.selectedAthleteId, trainingStore.sessionDate),
    trainingStore.hydrateAthletes(trainingStore.sessionDate),
  ])
}

async function openPlan(assignmentId?: number) {
  const nextAssignmentId = assignmentId || trainingStore.previewAssignmentId
  if (!nextAssignmentId) return
  const session = await trainingStore.openPlanSession(nextAssignmentId, trainingStore.sessionDate)
  activeItemId.value = findNextPendingItemId() ?? (session.items?.[0]?.id || null)
  latestSuggestion.value = null
  await router.replace({ name: 'training-session', params: { sessionId: session.id } })
}

async function submitCurrentSet(payload: Record<string, unknown>) {
  if (!activeItem.value) return
  const currentItemId = activeItem.value.id
  const response = await trainingStore.recordSet(currentItemId, payload)
  if (response.item.status === 'completed') {
    latestSuggestion.value = null
    activeItemId.value = findNextPendingItemId(currentItemId) ?? currentItemId
    return response
  }
  activeItemId.value = currentItemId
  latestSuggestion.value = response.next_suggestion
  return response
}

async function updateRecord(recordId: number, payload: Record<string, unknown>) {
  if (!activeItem.value) return
  const currentItemId = activeItem.value.id
  const response = await trainingStore.reviseSetRecord(recordId, payload)
  latestSuggestion.value = response.next_suggestion
  if (response.item.status === 'completed') {
    activeItemId.value = findNextPendingItemId(currentItemId) ?? currentItemId
  }
}

function selectActiveItem(itemId: number) {
  activeItemId.value = itemId
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
  if (!visibleAthletes.length) return

  const selectedStillVisible = visibleAthletes.some((athlete) => athlete.id === trainingStore.selectedAthleteId)
  if (!selectedStillVisible) {
    trainingStore.selectedAthleteId = visibleAthletes[0].id
  }
}

watch(
  () => trainingStore.session?.items,
  (items) => {
    if (!items?.length) return
    if (!activeItemId.value || !items.find((item: any) => item.id === activeItemId.value)) {
      activeItemId.value = findNextPendingItemId() ?? items[0].id
    }
  },
)

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
    <div class="training-mode-layout">
      <TrainingModeSidebar
        :athletes="filteredAthletes"
        :selected-athlete-id="trainingStore.selectedAthleteId"
        :session-date="trainingStore.sessionDate"
        :team-options="teamOptions"
        :selected-team-filter="selectedTeamFilter"
        :assignments="trainingStore.assignments"
        :preview-assignment-id="trainingStore.previewAssignmentId"
        @update-athlete="trainingStore.selectedAthleteId = $event"
        @update-date="trainingStore.sessionDate = $event"
        @update-team-filter="selectedTeamFilter = $event"
        @open-plan="openPlan"
      />

      <div class="center-column">
        <div class="panel hero">
          <div>
            <p class="section-title">训练记录</p>
            <h3>{{ selectedAssignment?.template?.name || '未进入训练计划' }}</h3>
            <p class="muted">
              {{ trainingStore.session ? `当前状态：${trainingStore.session.status}` : '点击左侧计划即可继续或切换当天训练记录。' }}
            </p>
          </div>
        </div>

        <TrainingSessionOverview
          :assignment="selectedAssignment"
          :session="trainingStore.session"
          :active-item-id="activeItemId"
          :on-select-item="selectActiveItem"
        />
      </div>

      <TrainingSetPanel
        :item="activeItem"
        :suggestion="latestSuggestion"
        :on-submit-current-set="submitCurrentSet"
        :on-update-record="updateRecord"
      />
    </div>
  </TrainingShell>
</template>

<style scoped>
.training-mode-layout {
  display: grid;
  grid-template-columns: 320px 1.2fr 360px;
  gap: 18px;
  height: 100%;
  min-height: 0;
}

.center-column {
  display: grid;
  gap: 18px;
  align-content: start;
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  min-width: 0;
}

.hero h3,
.section-title,
.muted {
  margin: 0;
}

.muted,
.section-title {
  color: var(--muted);
}

@media (max-width: 1360px) {
  .training-mode-layout {
    grid-template-columns: 1fr;
    height: auto;
  }

  .hero {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
