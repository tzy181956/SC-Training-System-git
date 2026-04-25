<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import TrainingShell from '@/components/layout/TrainingShell.vue'
import TrainingDraftRestoreModal from '@/components/training/TrainingDraftRestoreModal.vue'
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
const closingSession = ref(false)
const syncingFullSession = ref(false)
const sessionNotice = ref('')
const sessionNoticeTone = ref<'success' | 'warning' | 'error'>('success')
const restorePromptDraft = ref<any | null>(null)
const restorePromptResolver = ref<((accepted: boolean) => void) | null>(null)
const restoreToActionList = ref(false)
const ALL_TEAMS_VALUE = '__all__'
const UNASSIGNED_TEAM_VALUE = '__unassigned__'
const selectedTeamFilter = ref(ALL_TEAMS_VALUE)
let noticeTimer: number | null = null

const activeItem = computed(
  () =>
    restoreToActionList.value
      ? null
      : trainingStore.session?.items?.find((item: any) => item.id === activeItemId.value) || trainingStore.session?.items?.[0] || null,
)
const sessionStatusText = computed(() => {
  const status = trainingStore.session?.status
  if (status === 'completed') return '已完成'
  if (status === 'partial_complete') return '未完全完成'
  if (status === 'absent') return '缺席'
  if (status === 'in_progress') return '进行中'
  return '未开始'
})
const syncIndicatorLabel = computed(() => (trainingStore.syncStatus === 'synced' ? '正常' : '有未同步数据'))
const syncIndicatorTone = computed(() => (trainingStore.syncStatus === 'synced' ? 'success' : 'warning'))
const manualRetryHint = computed(() =>
  trainingStore.syncStatus === 'manual_retry_required' ? '自动重试已暂停，需教练手动补传。' : '',
)
const canTriggerManualSync = computed(() => {
  if (!trainingStore.session) return false
  if (syncingFullSession.value) return false
  return trainingStore.syncStatus !== 'synced'
})
const canEndSession = computed(() => {
  if (!trainingStore.session) return false
  const hasRecordedSets = (trainingStore.session.items || []).some((item: any) => (item.records?.length || 0) > 0)
  if (!trainingStore.session.id && !hasRecordedSets) return false
  return !closingSession.value && !['completed', 'absent', 'partial_complete'].includes(trainingStore.session.status)
})
const selectedAssignment = computed(
  () => trainingStore.assignments.find((item) => item.id === trainingStore.previewAssignmentId) || null,
)
const displaySessionDate = computed(() => formatSessionDate(trainingStore.sessionDate))
const currentAthleteName = computed(() => {
  const athleteId = trainingStore.session?.athlete_id || trainingStore.selectedAthleteId
  return trainingStore.athletes.find((athlete) => athlete.id === athleteId)?.full_name || ''
})
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

function buildResumeQuery() {
  const nextQuery: Record<string, string> = {}
  if (route.query.resumeDraft === '1') {
    nextQuery.resumeDraft = '1'
  }
  if (typeof route.query.resumeTarget === 'string' && route.query.resumeTarget) {
    nextQuery.resumeTarget = route.query.resumeTarget
  }
  if (typeof route.query.draftSessionKey === 'string' && route.query.draftSessionKey) {
    nextQuery.draftSessionKey = route.query.draftSessionKey
  }
  return nextQuery
}

function isExplicitResumeRequest(draft: any) {
  return route.query.resumeDraft === '1' && typeof route.query.draftSessionKey === 'string' && route.query.draftSessionKey === draft?.session_key
}

async function clearResumeQuery() {
  if (!('resumeDraft' in route.query) && !('resumeTarget' in route.query) && !('draftSessionKey' in route.query)) {
    return
  }

  const nextQuery = { ...route.query }
  delete nextQuery.resumeDraft
  delete nextQuery.resumeTarget
  delete nextQuery.draftSessionKey
  await router.replace({
    name: 'training-session',
    params: route.params,
    query: nextQuery,
  })
}

function applyRestoredDraft(draft: any, options: { focusActionList?: boolean; showNotice?: boolean } = {}) {
  const restoredSession = trainingStore.restoreDraft(draft)
  activeItemId.value = draft.current_item_id ?? findNextPendingItemId() ?? (restoredSession.items?.[0]?.id || null)
  latestSuggestion.value = draft.latest_suggestion ?? null
  restoreToActionList.value = !!options.focusActionList
  if (options.showNotice) {
    showSessionNotice('已恢复本地草稿，请从动作列表继续录课。', 'success')
  }
}

function openRestorePrompt(draft: any) {
  restorePromptDraft.value = draft
  return new Promise<boolean>((resolve) => {
    restorePromptResolver.value = resolve
  })
}

function handleRestorePromptDecision(accepted: boolean) {
  if (!restorePromptResolver.value) return
  const resolve = restorePromptResolver.value
  restorePromptResolver.value = null
  restorePromptDraft.value = null
  resolve(accepted)
}

async function confirmRestoreDraft(draft: any) {
  if (isExplicitResumeRequest(draft)) {
    return true
  }

  return openRestorePrompt(draft)
}

function showSessionNotice(message: string, tone: 'success' | 'warning' | 'error' = 'success') {
  sessionNotice.value = message
  sessionNoticeTone.value = tone
  if (noticeTimer !== null) {
    window.clearTimeout(noticeTimer)
  }
  noticeTimer = window.setTimeout(() => {
    sessionNotice.value = ''
    noticeTimer = null
  }, 2500)
}

async function maybeRestoreDraftForSession(nextSession: any) {
  const draft = trainingStore.getDraftForSession(nextSession)
  if (!draft) {
    if (route.query.resumeDraft === '1') {
      await clearResumeQuery()
    }
    return false
  }
  if (!draft.recorded_sets || (!draft.pending_sync && draft.session_snapshot?.status === 'completed')) return false

  if (await confirmRestoreDraft(draft)) {
    applyRestoredDraft(draft, {
      focusActionList: true,
      showNotice: true,
    })
    if (isExplicitResumeRequest(draft)) {
      await clearResumeQuery()
    }
    return true
  }

  trainingStore.discardDraft(draft.session_key)
  if (isExplicitResumeRequest(draft)) {
    await clearResumeQuery()
  }
  return false
}

async function maybeRecoverDraftWithoutBackend(sessionId: number) {
  const draft = trainingStore.getDraftBySessionId(sessionId)
  if (!draft) return false

  if (!(await confirmRestoreDraft(draft))) {
    trainingStore.discardDraft(draft.session_key)
    if (isExplicitResumeRequest(draft)) {
      await clearResumeQuery()
    }
    await router.replace({ name: 'training-mode' })
    return true
  }

  applyRestoredDraft(draft, {
    focusActionList: true,
    showNotice: true,
  })
  if (isExplicitResumeRequest(draft)) {
    await clearResumeQuery()
  }
  try {
    await Promise.all([
      trainingStore.loadPlans(draft.athlete_id, draft.session_date),
      trainingStore.hydrateAthletes(draft.session_date),
    ])
  } catch {
    // Backend unavailable does not block draft-only recovery.
  }
  return true
}

async function maybeRecoverDraftByContext(assignmentId: number, athleteId: number, targetDate: string) {
  const draft = trainingStore.getDraftByContext(athleteId, assignmentId, targetDate)
  if (!draft) return false

  if (!(await confirmRestoreDraft(draft))) {
    trainingStore.discardDraft(draft.session_key)
    if (isExplicitResumeRequest(draft)) {
      await clearResumeQuery()
    }
    await router.replace({ name: 'training-mode' })
    return true
  }

  applyRestoredDraft(draft, {
    focusActionList: true,
    showNotice: true,
  })
  if (isExplicitResumeRequest(draft)) {
    await clearResumeQuery()
  }
  return true
}

async function hydrate() {
  if (!trainingStore.sessionDate) {
    trainingStore.sessionDate = todayString()
  }
  if (!trainingStore.athletes.length) {
    try {
      await trainingStore.hydrateAthletes(trainingStore.sessionDate)
    } catch {
      // The session page can still recover from a local draft without athlete hydration.
    }
  }

  const sessionId = Number(route.params.sessionId)
  const assignmentId = Number(route.query.assignmentId)
  const athleteId = Number(route.query.athleteId)
  const requestedDate = typeof route.query.sessionDate === 'string' ? route.query.sessionDate : trainingStore.sessionDate

  if (sessionId) {
    try {
      const session = await trainingStore.loadSession(sessionId)
      trainingStore.selectedAthleteId = session.athlete_id
      trainingStore.sessionDate = session.session_date
      try {
        await Promise.all([
          trainingStore.loadPlans(session.athlete_id, session.session_date),
          trainingStore.hydrateAthletes(session.session_date),
        ])
      } catch {
        // Existing draft restore should not be blocked by temporary backend failures here.
      }
      trainingStore.setPreviewAssignment(session.assignment_id)
      const restored = await maybeRestoreDraftForSession(session)
      if (!restored) {
        restoreToActionList.value = false
        activeItemId.value = findNextPendingItemId() ?? (session.items?.[0]?.id || null)
      }
    } catch {
      const recovered = await maybeRecoverDraftWithoutBackend(sessionId)
      if (!recovered) {
        await router.replace({ name: 'training-mode' })
      }
    }
    return
  }

  if (!assignmentId) return

  trainingStore.sessionDate = requestedDate
  if (athleteId) {
    trainingStore.selectedAthleteId = athleteId
  }

  try {
    if (athleteId) {
      await Promise.all([
        trainingStore.loadPlans(athleteId, requestedDate),
        trainingStore.hydrateAthletes(requestedDate),
      ])
    }
    const nextSession = await trainingStore.openPlanSession(assignmentId, requestedDate)
    if (nextSession.id) {
      await router.replace({
        name: 'training-session',
        params: { sessionId: nextSession.id },
        query: buildResumeQuery(),
      })
      return
    }

    const restored = await maybeRestoreDraftForSession(nextSession)
    if (!restored) {
      restoreToActionList.value = false
      activeItemId.value = findNextPendingItemId() ?? (nextSession.items?.[0]?.id || null)
      latestSuggestion.value = null
    }
  } catch {
    if (!(await maybeRecoverDraftByContext(assignmentId, athleteId, requestedDate))) {
      await router.replace({ name: 'training-mode' })
    }
  }
}

async function loadPlans() {
  if (!trainingStore.selectedAthleteId || !trainingStore.sessionDate) return
  try {
    await Promise.all([
      trainingStore.loadPlans(trainingStore.selectedAthleteId, trainingStore.sessionDate),
      trainingStore.hydrateAthletes(trainingStore.sessionDate),
    ])
  } catch {
    // Local draft editing can continue without reloading plan lists.
  }
}

async function openPlan(assignmentId?: number) {
  const nextAssignmentId = assignmentId || trainingStore.previewAssignmentId
  if (!nextAssignmentId) return
  const session = await trainingStore.openPlanSession(nextAssignmentId, trainingStore.sessionDate)
  restoreToActionList.value = false
  activeItemId.value = findNextPendingItemId() ?? (session.items?.[0]?.id || null)
  latestSuggestion.value = null
  if (session.id) {
    await router.replace({ name: 'training-session', params: { sessionId: session.id } })
    return
  }

  await router.replace({
    name: 'training-session',
    query: {
      assignmentId: String(nextAssignmentId),
      athleteId: String(trainingStore.selectedAthleteId),
      sessionDate: trainingStore.sessionDate,
    },
  })
}

async function submitCurrentSet(payload: Record<string, unknown>) {
  if (!activeItem.value) return
  restoreToActionList.value = false
  const currentItemId = activeItem.value.id
  const response = await trainingStore.recordSet(currentItemId, payload, {
    activeItemId: currentItemId,
    latestSuggestion: latestSuggestion.value,
  })
  if (response.item.status === 'completed') {
    latestSuggestion.value = null
    activeItemId.value = findNextPendingItemId(currentItemId) ?? currentItemId
  } else {
    activeItemId.value = currentItemId
    latestSuggestion.value = response.next_suggestion
  }
  if (response.session?.id && !route.params.sessionId) {
    await router.replace({ name: 'training-session', params: { sessionId: response.session.id } })
  }
  if (response.session_status === 'completed') {
    showSessionNotice(
      response.local_only ? '整堂训练已在本机标记为完成，待后续同步。' : '整堂训练已自动完成。',
      'success',
    )
  }
  return response
}

async function updateRecord(recordId: number, payload: Record<string, unknown>) {
  if (!activeItem.value) return
  restoreToActionList.value = false
  const currentItemId = activeItem.value.id
  const response = await trainingStore.reviseSetRecord(recordId, payload, {
    activeItemId: currentItemId,
    latestSuggestion: latestSuggestion.value,
  })
  latestSuggestion.value = response.next_suggestion
  if (response.item.status === 'completed') {
    activeItemId.value = findNextPendingItemId(currentItemId) ?? currentItemId
  }
}

async function endPlan() {
  const currentSession = trainingStore.session
  if (!currentSession || !canEndSession.value) return

  const confirmMessage =
    '确认结束当前训练计划？\n\n如果还有动作或组没有录完，本堂课将记为“未完全完成”。'
  if (!window.confirm(confirmMessage)) return

  closingSession.value = true
  try {
    const nextSession = await trainingStore.endSession(currentSession.id || 0, {
      activeItemId: activeItemId.value,
      latestSuggestion: null,
    })
    latestSuggestion.value = null
    if (nextSession.status === 'completed') {
      showSessionNotice('本堂训练已结束，状态为已完成。', 'success')
    } else if (nextSession.status === 'partial_complete') {
      showSessionNotice('本堂训练已结束，状态记为未完全完成。', 'warning')
    } else {
      showSessionNotice(`本堂训练已结束，状态为 ${sessionStatusText.value}。`, 'success')
    }
  } catch {
    showSessionNotice('结束计划失败，请重试。', 'error')
  } finally {
    closingSession.value = false
  }
}

async function triggerFullSync() {
  if (!canTriggerManualSync.value) return

  syncingFullSession.value = true
  try {
    const response = await trainingStore.requestFullSessionSync()
    if (!response) {
      showSessionNotice('整课补传失败，已转为人工处理。', 'warning')
      return
    }

    if (response.session?.id && !route.params.sessionId) {
      await router.replace({ name: 'training-session', params: { sessionId: response.session.id } })
    }

    showSessionNotice(
      response.conflict_logged
        ? '整课补传完成，已记录同步冲突，待教练或管理员复核。'
        : '整课补传完成，已按本地草稿覆盖后端。',
      response.conflict_logged ? 'warning' : 'success',
    )
  } catch {
    showSessionNotice('整课补传失败，已转为人工处理。', 'warning')
  } finally {
    syncingFullSession.value = false
  }
}

function selectActiveItem(itemId: number) {
  restoreToActionList.value = false
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

watch(
  () => [activeItemId.value, latestSuggestion.value, trainingStore.session?.id, trainingStore.session?.status],
  () => {
    trainingStore.persistLocalDraftState({
      activeItemId: activeItemId.value,
      latestSuggestion: latestSuggestion.value,
    })
  },
  { deep: true },
)

onBeforeUnmount(() => {
  if (noticeTimer !== null) {
    window.clearTimeout(noticeTimer)
  }
})

onMounted(hydrate)
</script>

<template>
  <TrainingShell>
    <TrainingDraftRestoreModal
      :open="!!restorePromptDraft"
      :draft="restorePromptDraft"
      @continue-restore="handleRestorePromptDecision(true)"
      @discard-restore="handleRestorePromptDecision(false)"
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
          <span class="compact-label">训练队伍</span>
          <div class="filter-pill-shell">
            <button class="filter-pill team-filter" type="button" tabindex="-1" aria-hidden="true">
              <span class="filter-pill-text">{{ selectedTeamLabel }}</span>
            </button>
            <select
              :value="selectedTeamFilter"
              class="header-filter-control filter-native-control filter-native-team"
              aria-label="训练队伍筛选"
              title="训练队伍筛选"
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
        @open-plan="openPlan"
      />

      <div class="center-column layout-center">
        <div class="panel hero">
          <div class="hero-copy">
            <h3 class="hero-athlete-name">{{ currentAthleteName || '未选择队员' }}</h3>
            <span class="hero-status-pill">{{ trainingStore.session ? sessionStatusText : '待开始' }}</span>
            <div v-if="trainingStore.session" class="sync-indicator" :class="syncIndicatorTone">
              <span class="sync-indicator-dot"></span>
              <span>同步{{ syncIndicatorLabel }}</span>
            </div>
            <p v-else class="hero-inline-hint">点击左侧计划即可继续或切换当天训练记录。</p>
            <p v-if="manualRetryHint" class="session-notice warning">{{ manualRetryHint }}</p>
            <p v-if="sessionNotice" class="session-notice" :class="sessionNoticeTone">{{ sessionNotice }}</p>
          </div>

          <div class="hero-actions">
            <button
              v-if="canTriggerManualSync"
              class="secondary-btn end-plan-btn"
              type="button"
              :disabled="syncingFullSession"
              @click="triggerFullSync"
            >
              {{ syncingFullSession ? '正在同步个人训练数据...' : '同步个人训练数据' }}
            </button>
            <button class="secondary-btn end-plan-btn" type="button" :disabled="!canEndSession" @click="endPlan">
              {{ closingSession ? '正在结束...' : '结束计划' }}
            </button>
          </div>
        </div>

        <TrainingSessionOverview
          :assignment="selectedAssignment"
          :session="trainingStore.session"
          :athlete-name="currentAthleteName"
          :active-item-id="activeItemId"
          :on-select-item="selectActiveItem"
        />
      </div>

      <TrainingSetPanel
        class="layout-panel"
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
  grid-template-columns: minmax(280px, 320px) minmax(0, 1.15fr) minmax(320px, 360px);
  grid-template-areas: 'sidebar center panel';
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

.layout-center {
  grid-area: center;
  min-height: 0;
}

.layout-panel {
  grid-area: panel;
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

.center-column {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 18px;
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
  padding: 14px 16px;
}

.hero-copy {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  min-width: 0;
}

.hero-athlete-name {
  margin: 0;
  font-size: clamp(1.45rem, 1.9vw, 1.85rem);
  line-height: 1.05;
  font-weight: 900;
  color: var(--text);
  white-space: nowrap;
}

.hero-status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  background: var(--panel-soft);
  color: var(--text);
  font-size: 0.9rem;
  line-height: 1.1;
  font-weight: 700;
  white-space: nowrap;
}

.hero-inline-hint {
  margin: 0;
  color: var(--muted);
  font-size: 0.92rem;
  line-height: 1.25;
}

.sync-indicator {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  width: fit-content;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 0.86rem;
  line-height: 1.2;
  font-weight: 600;
  white-space: nowrap;
}

.sync-indicator-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: currentColor;
}

.sync-indicator.success {
  background: #dcfce7;
  color: #166534;
}

.sync-indicator.warning {
  background: #fef3c7;
  color: #92400e;
}

.hero-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  flex-shrink: 0;
  gap: 12px;
  min-width: 0;
}

.end-plan-btn {
  min-height: 44px;
  min-width: 120px;
}

.hero h3,
.muted {
  margin: 0;
}

.session-notice {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 999px;
  font-size: 0.84rem;
  line-height: 1.2;
  font-weight: 600;
}

.session-notice.success {
  background: #dcfce7;
  color: #166534;
}

.session-notice.warning {
  background: #fef3c7;
  color: #92400e;
}

.session-notice.error {
  background: #fee2e2;
  color: #b91c1c;
}

.muted {
  color: var(--muted);
}

@media (min-width: 768px) and (max-width: 1199px) {
  .training-mode-layout {
    grid-template-columns: 240px minmax(0, 1fr) 260px;
    grid-template-areas: 'sidebar center panel';
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

  .center-column {
    gap: 12px;
  }

  .hero {
    gap: 12px;
    padding: 12px 14px;
  }

  .hero-copy {
    gap: 8px;
  }

  .hero-athlete-name {
    font-size: clamp(1.25rem, 2.2vw, 1.55rem);
  }

  .hero-actions {
    gap: 8px;
    flex-wrap: wrap;
    justify-content: flex-end;
  }

  .end-plan-btn {
    min-width: 0;
    padding-inline: 14px;
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
      'center'
      'panel';
    height: auto;
  }

  .hero {
    flex-direction: column;
    align-items: flex-start;
    padding: 14px;
  }

  .hero-athlete-name {
    font-size: 1.65rem;
  }

  .hero-copy {
    align-items: flex-start;
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

  .hero-actions {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}

</style>
