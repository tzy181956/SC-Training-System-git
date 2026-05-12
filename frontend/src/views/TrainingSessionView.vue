<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import TrainingShell from '@/components/layout/TrainingShell.vue'
import TrainingHeaderFilters from '@/components/training/TrainingHeaderFilters.vue'
import SessionRpeModal from '@/components/training/SessionRpeModal.vue'
import TrainingModeSidebar from '@/components/training/TrainingModeSidebar.vue'
import TrainingSessionOverview from '@/components/training/TrainingSessionOverview.vue'
import TrainingSetPanel from '@/components/training/TrainingSetPanel.vue'
import { TRAINING_SYNC_NOTICE_TEXT } from '@/constants/trainingSync'
import { getSessionRpeHelp, getSessionRpeLabel } from '@/constants/sessionRpe'
import { getTrainingStatusLabel, getTrainingStatusTone, isFinalTrainingStatus } from '@/constants/trainingStatus'
import { useTeamFilter } from '@/composables/useTeamFilter'
import { useTrainingStore } from '@/stores/training'
import { todayString } from '@/utils/date'
import { TRAINING_DRAFT_REMOTE_RELATION } from '@/utils/trainingDraft'

const route = useRoute()
const router = useRouter()
const trainingStore = useTrainingStore()
const activeItemId = ref<number | null>(null)
const latestSuggestion = ref<any | null>(null)
const closingSession = ref(false)
const syncingFullSession = ref(false)
const sessionNotice = ref('')
const sessionNoticeTone = ref<'success' | 'warning' | 'error'>('success')
const sessionRpeModalOpen = ref(false)
const sessionRpeDeferred = ref(false)
const sessionRpeSubmitting = ref(false)
const sessionRpeError = ref('')
const restoreToActionList = ref(false)
let noticeTimer: number | null = null
const selectedAthleteIdRef = computed({
  get: () => trainingStore.selectedAthleteId,
  set: (value: number) => {
    trainingStore.selectedAthleteId = value
  },
})

const activeItem = computed(
  () =>
    restoreToActionList.value
      ? null
      : trainingStore.session?.items?.find((item: any) => item.id === activeItemId.value) || trainingStore.session?.items?.[0] || null,
)
const sessionStatusText = computed(() => getTrainingStatusLabel(trainingStore.session?.status))
const sessionStatusTone = computed(() => getTrainingStatusTone(trainingStore.session?.status))
const syncIndicatorLabel = computed(() => {
  if (trainingStore.syncStatus === 'manual_retry_required') return '待教练处理'
  return trainingStore.syncStatus === 'synced' ? '正常' : '正在同步'
})
const syncIndicatorTone = computed(() => {
  if (trainingStore.syncStatus === 'manual_retry_required') return 'danger'
  return trainingStore.syncStatus === 'synced' ? 'success' : 'warning'
})
const manualRetryHint = computed(() =>
  trainingStore.syncStatus === 'manual_retry_required'
    ? trainingStore.manualRetryReason === 'conflict'
      ? TRAINING_SYNC_NOTICE_TEXT.conflictHandoff
      : '自动重试已暂停，需教练手动补传。'
    : '',
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
  return !closingSession.value && !isFinalTrainingStatus(trainingStore.session.status)
})
const selectedAssignment = computed(
  () => trainingStore.assignments.find((item) => item.id === trainingStore.previewAssignmentId) || null,
)
const displaySessionDate = computed(() => formatSessionDate(trainingStore.sessionDate))
const currentAthleteName = computed(() => {
  const athleteId = trainingStore.session?.athlete_id || trainingStore.selectedAthleteId
  return trainingStore.athletes.find((athlete) => athlete.id === athleteId)?.full_name || ''
})
const canCollectSessionRpe = computed(() => {
  const currentSession = trainingStore.session
  return (
    Boolean(currentSession?.id)
    && currentSession?.status === 'completed'
    && currentSession?.session_date === todayString()
    && trainingStore.syncStatus === 'synced'
  )
})
const hasSubmittedSessionRpe = computed(
  () => typeof trainingStore.session?.session_rpe === 'number' && Number.isInteger(trainingStore.session.session_rpe),
)
const shouldShowSessionRpeReminder = computed(
  () => canCollectSessionRpe.value && !hasSubmittedSessionRpe.value && sessionRpeDeferred.value,
)
const sessionRpeLabel = computed(() => getSessionRpeLabel(trainingStore.session?.session_rpe))
const sessionRpeHelp = computed(() => getSessionRpeHelp(trainingStore.session?.session_rpe))
const sessionCompletedAtLabel = computed(() => formatDateTime(trainingStore.session?.completed_at))
const {
  selectedSportFilter,
  sportOptions,
  selectedSportLabel,
  selectedTeamFilter,
  teamOptions,
  selectedTeamLabel,
  filteredAthletes,
  isSportLocked,
  syncSportFilter,
  syncTeamFilter,
  syncSelectedAthleteForFilter,
} = useTeamFilter({
  athletes: () => trainingStore.athletes,
  selectedAthleteId: selectedAthleteIdRef,
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
    showSessionNotice(TRAINING_SYNC_NOTICE_TEXT.offlineRecoverable, 'warning', 4200)
  }
}

function showSessionNotice(message: string, tone: 'success' | 'warning' | 'error' = 'success', durationMs = 2500) {
  sessionNotice.value = message
  sessionNoticeTone.value = tone
  if (noticeTimer !== null) {
    window.clearTimeout(noticeTimer)
  }
  noticeTimer = window.setTimeout(() => {
    sessionNotice.value = ''
    noticeTimer = null
  }, durationMs)
}

function formatDateTime(value?: string | null) {
  if (!value) return ''

  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

function openSessionRpeModal() {
  if (!canCollectSessionRpe.value) return
  sessionRpeError.value = ''
  sessionRpeModalOpen.value = true
}

function closeSessionRpeForLater() {
  sessionRpeModalOpen.value = false
  sessionRpeDeferred.value = true
  sessionRpeError.value = ''
}

async function submitSessionRpeFeedback(payload: { session_rpe: number; session_feedback: string | null }) {
  if (!canCollectSessionRpe.value || !trainingStore.session?.id) return

  sessionRpeSubmitting.value = true
  sessionRpeError.value = ''
  try {
    await trainingStore.submitSessionFinishFeedback(payload)
    sessionRpeModalOpen.value = false
    sessionRpeDeferred.value = false
    showSessionNotice('整体 RPE 已保存。', 'success')
  } catch (error: any) {
    sessionRpeError.value = error?.response?.data?.detail || '提交失败，请检查网络或稍后重试'
  } finally {
    sessionRpeSubmitting.value = false
  }
}

async function maybeRestoreDraftForSession(nextSession: any) {
  const draft = trainingStore.getDraftForSession(nextSession)
  if (!draft) {
    if (route.query.resumeDraft === '1') {
      await clearResumeQuery()
    }
    return false
  }

  const relation = trainingStore.classifyDraftRelation(nextSession)
  if (!relation) {
    if (isExplicitResumeRequest(draft)) {
      await clearResumeQuery()
    }
    return false
  }

  if (relation === TRAINING_DRAFT_REMOTE_RELATION.IDENTICAL) {
    trainingStore.replaceSessionFromRemote(nextSession, {
      activeItemId: activeItemId.value,
      latestSuggestion: null,
    })
    if (isExplicitResumeRequest(draft)) {
      await clearResumeQuery()
    }
    return false
  }

  if (relation === TRAINING_DRAFT_REMOTE_RELATION.REMOTE_AHEAD_NO_LOCAL_CHANGES) {
    trainingStore.replaceSessionFromRemote(nextSession, {
      activeItemId: activeItemId.value,
      latestSuggestion: null,
    })
    if (isExplicitResumeRequest(draft)) {
      await clearResumeQuery()
    }
    return false
  }

  applyRestoredDraft(draft, { focusActionList: true })

  if (relation === TRAINING_DRAFT_REMOTE_RELATION.LOCAL_AHEAD) {
    showSessionNotice(TRAINING_SYNC_NOTICE_TEXT.localAhead, 'warning', 3200)
    void trainingStore.syncPendingOperations()
  } else if (relation === TRAINING_DRAFT_REMOTE_RELATION.DIVERGED) {
    await trainingStore.handoffConflictToCoach(draft)
    showSessionNotice(TRAINING_SYNC_NOTICE_TEXT.conflictHandoff, 'warning', 5200)
  }

  if (isExplicitResumeRequest(draft)) {
    await clearResumeQuery()
  }
  return true
}

async function maybeRecoverDraftWithoutBackend(sessionId: number) {
  const draft = trainingStore.getDraftBySessionId(sessionId)
  if (!draft) return false

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
  const submittedWhileFocusedItemId = activeItemId.value
  const response = await trainingStore.recordSet(currentItemId, payload, {
    activeItemId: currentItemId,
    latestSuggestion: latestSuggestion.value,
  })
  const userStillFocusedSubmittedItem = activeItemId.value === submittedWhileFocusedItemId
  if (response.item.status === 'completed') {
    if (userStillFocusedSubmittedItem) {
      latestSuggestion.value = null
      activeItemId.value = findNextPendingItemId(currentItemId) ?? currentItemId
    }
  } else {
    if (userStillFocusedSubmittedItem) {
      activeItemId.value = currentItemId
      latestSuggestion.value = response.next_suggestion
    }
  }
  if (response.session?.id && !route.params.sessionId) {
    await router.replace({ name: 'training-session', params: { sessionId: response.session.id } })
  }
  if (response.session_status === 'completed') {
    const recordedLocally = 'local_only' in response && response.local_only
    showSessionNotice(
      recordedLocally ? '整堂训练已在本机标记为完成，待后续同步。' : '整堂训练已自动完成。',
      'success',
    )
  }
  return response
}

async function updateRecord(recordId: number, payload: Record<string, unknown>) {
  if (!activeItem.value) return
  restoreToActionList.value = false
  const currentItemId = activeItem.value.id
  const submittedWhileFocusedItemId = activeItemId.value
  const response = await trainingStore.reviseSetRecord(recordId, payload, {
    activeItemId: currentItemId,
    latestSuggestion: latestSuggestion.value,
  })
  const userStillFocusedSubmittedItem = activeItemId.value === submittedWhileFocusedItemId
  if (userStillFocusedSubmittedItem) {
    latestSuggestion.value = response.next_suggestion
  }
  if (response.item.status === 'completed' && userStillFocusedSubmittedItem) {
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
  () => trainingStore.session?.id,
  () => {
    sessionRpeModalOpen.value = false
    sessionRpeDeferred.value = false
    sessionRpeSubmitting.value = false
    sessionRpeError.value = ''
  },
)

watch(
  () => trainingStore.athletes,
  () => {
    syncSportFilter()
    syncTeamFilter()
    syncSelectedAthleteForFilter()
  },
  { immediate: true, deep: true },
)

watch(
  () => [selectedSportFilter.value, selectedTeamFilter.value],
  () => {
    syncTeamFilter()
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

watch(
  () => [
    trainingStore.session?.id,
    trainingStore.session?.status,
    trainingStore.session?.session_rpe,
    trainingStore.syncStatus,
  ],
  ([sessionId, sessionStatus, sessionRpe, syncStatus]) => {
    if (typeof sessionRpe === 'number') {
      sessionRpeModalOpen.value = false
      sessionRpeDeferred.value = false
      sessionRpeError.value = ''
      return
    }
    if (!sessionId || sessionStatus !== 'completed' || syncStatus !== 'synced') return
    if (sessionRpeDeferred.value || sessionRpeModalOpen.value) return
    sessionRpeError.value = ''
    sessionRpeModalOpen.value = true
  },
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
    <SessionRpeModal
      :open="sessionRpeModalOpen"
      :initial-rpe="trainingStore.session?.session_rpe ?? null"
      :initial-feedback="trainingStore.session?.session_feedback ?? null"
      :submitting="sessionRpeSubmitting"
      :error="sessionRpeError"
      @close-later="closeSessionRpeForLater"
      @submit="submitSessionRpeFeedback"
    />

    <template #header-filters>
      <TrainingHeaderFilters
        :session-date="trainingStore.sessionDate"
        :session-date-label="displaySessionDate"
        :selected-sport-value="selectedSportFilter"
        :selected-sport-label="selectedSportLabel"
        :sport-options="sportOptions"
        :sport-disabled="isSportLocked"
        :selected-team-value="selectedTeamFilter"
        :selected-team-label="selectedTeamLabel"
        :team-options="teamOptions"
        sport-field-label="训练项目"
        sport-aria-label="训练项目筛选"
        team-field-label="训练队伍"
        team-aria-label="训练队伍筛选"
        @update:session-date="handleDateInput"
        @update:sport-value="handleSportFilterInput"
        @update:team-value="handleTeamFilterInput"
      />
    </template>

    <div class="training-session-layout training-three-column-layout">
      <TrainingModeSidebar
        class="layout-sidebar"
        :athletes="filteredAthletes"
        :selected-athlete-id="trainingStore.selectedAthleteId"
        :assignments="trainingStore.assignments"
        :preview-assignment-id="trainingStore.previewAssignmentId"
        @update-athlete="trainingStore.selectedAthleteId = $event"
        @open-plan="openPlan"
      />

      <div class="center-column layout-center training-scroll-column">
        <div class="panel hero">
          <div class="hero-copy">
            <h3 class="hero-athlete-name">{{ currentAthleteName || '未选择队员' }}</h3>
            <span class="hero-status-pill" :class="trainingStore.session ? sessionStatusTone : 'neutral'">
              {{ trainingStore.session ? sessionStatusText : '待开始' }}
            </span>
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

        <div v-if="shouldShowSessionRpeReminder" class="panel session-rpe-reminder">
          <div class="session-rpe-copy">
            <strong>今日训练已完成，请补充整体 RPE</strong>
            <span>训练完成反馈尚未提交。</span>
          </div>
          <button class="primary-btn session-rpe-action" type="button" @click="openSessionRpeModal">填写 RPE</button>
        </div>

        <div v-if="hasSubmittedSessionRpe" class="session-rpe-summary-bar">
          <div class="session-rpe-summary-meta">
            <span class="session-rpe-summary-label">
              Session RPE：<strong class="session-rpe-summary-value">{{ trainingStore.session?.session_rpe }}/10</strong>
            </span>
            <span class="session-rpe-summary-separator" aria-hidden="true">｜</span>
            <span class="session-rpe-summary-description">{{ sessionRpeLabel }}</span>
            <span v-if="sessionRpeHelp" class="session-rpe-summary-separator" aria-hidden="true">｜</span>
            <span v-if="sessionRpeHelp" class="session-rpe-summary-help">{{ sessionRpeHelp }}</span>
            <template v-if="sessionCompletedAtLabel">
              <span class="session-rpe-summary-separator" aria-hidden="true">｜</span>
              <span class="session-rpe-summary-time">完成时间：{{ sessionCompletedAtLabel }}</span>
            </template>
          </div>
          <button
            v-if="canCollectSessionRpe"
            class="secondary-btn session-rpe-summary-edit"
            type="button"
            @click="openSessionRpeModal"
          >
            修改 RPE
          </button>
        </div>

        <TrainingSessionOverview
          class="session-overview-slot"
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
.training-session-layout {
  --training-panel-min-width: 280px;
  grid-template-areas: 'sidebar center panel';
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

.center-column {
  display: flex;
  flex-direction: column;
  gap: 18px;
  min-height: 0;
}

.session-rpe-reminder,
.session-rpe-summary-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.session-rpe-copy {
  display: grid;
  gap: 6px;
}

.session-rpe-copy strong,
.session-rpe-copy span {
  margin: 0;
}

.session-rpe-copy span {
  color: var(--text-soft);
}

.session-rpe-reminder {
  padding: 16px;
  border: 1px solid rgba(245, 158, 11, 0.24);
  background: rgba(254, 243, 199, 0.68);
}

.session-rpe-summary-bar {
  min-height: 52px;
  padding: 10px 14px;
  border-radius: 14px;
  border: 1px solid rgba(15, 118, 110, 0.12);
  background: rgba(236, 253, 245, 0.5);
  min-width: 0;
}

.session-rpe-summary-meta {
  display: flex;
  align-items: center;
  flex: 1 1 320px;
  flex-wrap: wrap;
  gap: 6px 10px;
  min-width: 0;
}

.session-rpe-summary-label,
.session-rpe-summary-description,
.session-rpe-summary-help,
.session-rpe-summary-time,
.session-rpe-summary-separator {
  margin: 0;
  line-height: 1.25;
}

.session-rpe-summary-label {
  color: var(--text);
  font-size: 0.94rem;
  font-weight: 600;
}

.session-rpe-summary-value {
  font-size: 1rem;
  font-weight: 800;
}

.session-rpe-summary-description,
.session-rpe-summary-help,
.session-rpe-summary-time {
  color: var(--text-soft);
  font-size: 0.9rem;
}

.session-rpe-summary-description {
  color: var(--text);
  font-weight: 700;
}

.session-rpe-summary-separator {
  color: rgba(15, 23, 42, 0.28);
}

.session-rpe-summary-edit {
  min-height: 36px;
  min-width: auto;
  padding: 0 14px;
  border-radius: 12px;
  flex-shrink: 0;
  font-size: 0.9rem;
}

.session-overview-slot {
  flex: 1 1 auto;
  min-height: 0;
}

.session-rpe-action {
  min-height: 44px;
  min-width: 120px;
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
  font-size: 0.9rem;
  line-height: 1.1;
  font-weight: 700;
  white-space: nowrap;
}

.hero-status-pill.success {
  background: #dcfce7;
  color: #166534;
}

.hero-status-pill.progress {
  background: #dbeafe;
  color: #1d4ed8;
}

.hero-status-pill.partial {
  background: #ffedd5;
  color: #c2410c;
}

.hero-status-pill.neutral {
  background: #e5e7eb;
  color: #374151;
}

.hero-status-pill.danger {
  background: #fee2e2;
  color: #b91c1c;
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

.sync-indicator.danger {
  background: #fee2e2;
  color: #b91c1c;
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
  .center-column {
    gap: 12px;
  }

  .session-rpe-reminder,
  .session-rpe-summary-bar {
    padding: 14px;
  }

  .session-rpe-summary-bar {
    min-height: 48px;
    padding: 9px 12px;
  }

  .session-rpe-summary-meta {
    gap: 6px 8px;
  }

  .session-rpe-summary-edit {
    min-height: 34px;
    padding-inline: 12px;
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

@media (max-width: 767px) {
  .training-session-layout {
    grid-template-areas:
      'sidebar'
      'center'
      'panel';
  }

  .hero {
    flex-direction: column;
    align-items: flex-start;
    padding: 14px;
  }

  .session-rpe-reminder {
    flex-direction: column;
    align-items: flex-start;
  }

  .session-rpe-summary-bar {
    align-items: flex-start;
    gap: 10px;
  }

  .session-rpe-summary-meta {
    gap: 4px 8px;
  }

  .session-rpe-summary-edit {
    min-height: 34px;
  }

  .hero-athlete-name {
    font-size: 1.65rem;
  }

  .hero-copy {
    align-items: flex-start;
  }

  .hero-actions {
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}

</style>
