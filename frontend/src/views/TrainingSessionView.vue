<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
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
const closingSession = ref(false)
const syncingFullSession = ref(false)
const sessionNotice = ref('')
const sessionNoticeTone = ref<'success' | 'warning' | 'error'>('success')
const ALL_TEAMS_VALUE = '__all__'
const UNASSIGNED_TEAM_VALUE = '__unassigned__'
const selectedTeamFilter = ref(ALL_TEAMS_VALUE)
let noticeTimer: number | null = null

const activeItem = computed(
  () => trainingStore.session?.items?.find((item: any) => item.id === activeItemId.value) || trainingStore.session?.items?.[0] || null,
)
const sessionStatusLabel = computed(() => {
  const status = trainingStore.session?.status
  if (status === 'completed') return '已完成'
  if (status === 'partial_complete') return '未完全完成'
  if (status === 'absent') return '缺席'
  if (status === 'in_progress') return '进行中'
  return '未开始'
})
const syncStatusLabel = computed(() => (trainingStore.syncStatus === 'pending' ? '有未同步数据' : '正常'))
const syncStatusTone = computed(() => (trainingStore.syncStatus === 'pending' ? 'warning' : 'success'))
const canTriggerFullSync = computed(() => {
  if (!trainingStore.session) return false
  if (syncingFullSession.value) return false
  return trainingStore.syncStatus === 'pending'
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

function buildRestorePrompt(draft: any) {
  const modifiedAt = draft?.last_modified_at ? new Date(draft.last_modified_at).toLocaleString('zh-CN') : '未知时间'
  return `检测到这堂训练课在本机有未完成草稿（最后保存于 ${modifiedAt}）。\n\n点击“确定”恢复本地草稿继续训练；点击“取消”放弃本地草稿并继续使用当前记录。`
}

function applyRestoredDraft(draft: any) {
  const restoredSession = trainingStore.restoreDraft(draft)
  activeItemId.value = draft.current_item_id ?? findNextPendingItemId() ?? (restoredSession.items?.[0]?.id || null)
  latestSuggestion.value = draft.latest_suggestion ?? null
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
  if (!draft) return false
  if (!draft.recorded_sets || (!draft.pending_sync && draft.session_snapshot?.status === 'completed')) return false

  if (window.confirm(buildRestorePrompt(draft))) {
    applyRestoredDraft(draft)
    return true
  }

  trainingStore.discardDraft(draft.session_key)
  return false
}

async function maybeRecoverDraftWithoutBackend(sessionId: number) {
  const draft = trainingStore.getDraftBySessionId(sessionId)
  if (!draft) return false

  if (!window.confirm(buildRestorePrompt(draft))) {
    trainingStore.discardDraft(draft.session_key)
    await router.replace({ name: 'training-mode' })
    return true
  }

  applyRestoredDraft(draft)
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

  if (!window.confirm(buildRestorePrompt(draft))) {
    trainingStore.discardDraft(draft.session_key)
    await router.replace({ name: 'training-mode' })
    return true
  }

  applyRestoredDraft(draft)
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
      await router.replace({ name: 'training-session', params: { sessionId: nextSession.id } })
      return
    }

    const restored = await maybeRestoreDraftForSession(nextSession)
    if (!restored) {
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
      showSessionNotice(`本堂训练已结束，状态为 ${sessionStatusLabel.value}。`, 'success')
    }
  } catch {
    showSessionNotice('结束计划失败，请重试。', 'error')
  } finally {
    closingSession.value = false
  }
}

/*
async function triggerFullSync() {
  if (!canTriggerFullSync.value) return

  syncingFullSession.value = true
  try {
    const response = await trainingStore.requestFullSessionSync()
    if (!response) {
      showSessionNotice('鏁村爞琛ヤ紶澶辫触锛岀▼搴忎細缁х画鍚庡彴閲嶈瘯銆?, 'warning')
      return
    }

    if (response.session?.id && !route.params.sessionId) {
      await router.replace({ name: 'training-session', params: { sessionId: response.session.id } })
    }

    showSessionNotice(
      response.conflict_logged
        ? '宸叉寜鏈湴鑽夌瀹屾垚鏁村爞琛ヤ紶锛屽苟璁板綍浜嗗悓姝ュ啿绐佹彁绀恒€?'
        : '宸叉寜鏈湴鑽夌瀹屾垚鏁村爞琛ヤ紶銆?,
      response.conflict_logged ? 'warning' : 'success',
    )
  } catch {
    showSessionNotice('鏁村爞琛ヤ紶澶辫触锛岀▼搴忎細缁х画鍚庡彴閲嶈瘯銆?, 'warning')
  } finally {
    syncingFullSession.value = false
  }
}
*/

async function triggerFullSync() {
  if (!canTriggerFullSync.value) return

  syncingFullSession.value = true
  try {
    const response = await trainingStore.requestFullSessionSync()
    if (!response) {
      showSessionNotice('Full sync failed. Background retry will continue.', 'warning')
      return
    }

    if (response.session?.id && !route.params.sessionId) {
      await router.replace({ name: 'training-session', params: { sessionId: response.session.id } })
    }

    showSessionNotice(
      response.conflict_logged
        ? 'Full sync finished. A conflict log was recorded for review.'
        : 'Full sync finished from the local draft.',
      response.conflict_logged ? 'warning' : 'success',
    )
  } catch {
    showSessionNotice('Full sync failed. Background retry will continue.', 'warning')
  } finally {
    syncingFullSession.value = false
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
          <div class="hero-copy">
            <p class="section-title">训练记录</p>
            <h3>{{ selectedAssignment?.template?.name || '未进入训练计划' }}</h3>
            <p class="muted">
              {{ trainingStore.session ? `当前状态：${sessionStatusLabel}` : '点击左侧计划即可继续或切换当天训练记录。' }}
            </p>
            <p v-if="trainingStore.session" class="session-notice" :class="syncStatusTone">同步状态：{{ syncStatusLabel }}</p>
            <p v-if="sessionNotice" class="session-notice" :class="sessionNoticeTone">{{ sessionNotice }}</p>
          </div>

          <div class="hero-actions">
            <button
              v-if="canTriggerFullSync"
              class="secondary-btn end-plan-btn"
              type="button"
              :disabled="syncingFullSession"
              @click="triggerFullSync"
            >
              {{ syncingFullSession ? '姝ｅ湪鏁村爞琛ヤ紶...' : '鏁村爞琛ヤ紶' }}
            </button>
            <button class="secondary-btn end-plan-btn" type="button" :disabled="!canEndSession" @click="endPlan">
              {{ closingSession ? '正在结束...' : '结束计划' }}
            </button>
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
}

.hero-copy {
  display: grid;
  gap: 8px;
}

.hero-actions {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  flex-shrink: 0;
}

.end-plan-btn {
  min-height: 44px;
  min-width: 120px;
}

.hero h3,
.section-title,
.muted {
  margin: 0;
}

.session-notice {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 13px;
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
