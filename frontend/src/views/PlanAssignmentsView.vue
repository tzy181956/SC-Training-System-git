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
import AssignmentPreviewPanel from '@/components/assignment/AssignmentPreviewPanel.vue'
import AppShell from '@/components/layout/AppShell.vue'
import { todayString } from '@/utils/date'

const athletes = ref<any[]>([])
const templates = ref<any[]>([])
const sports = ref<any[]>([])
const teams = ref<any[]>([])
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
const cancelTargetAthleteId = ref<number | null>(null)
const confirmCancelAssignmentId = ref<number | null>(null)

const filters = reactive({
  sportId: 0,
  teamId: 0,
  onlyUnassigned: false,
})

const form = reactive({
  athlete_ids: [] as number[],
  template_id: 0,
  assigned_date: todayString(),
  start_date: todayString(),
  end_date: todayString(),
  notes: '',
})

const selectedTemplate = computed(() => templates.value.find((item) => item.id === form.template_id) || null)
const filteredTeams = computed(() =>
  filters.sportId ? teams.value.filter((team) => team.sport_id === filters.sportId) : teams.value,
)
const filteredAthletes = computed(() =>
  athletes.value.filter((athlete) => {
    if (!athlete.is_active) return false
    if (filters.sportId && athlete.sport_id !== filters.sportId) return false
    if (filters.teamId && athlete.team_id !== filters.teamId) return false
    if (filters.onlyUnassigned && !overview.value.unassigned_athletes.some((item: any) => item.id === athlete.id)) return false
    return true
  }),
)
const filteredAssignmentGroups = computed(() =>
  overview.value.assignment_groups.filter((group: any) =>
    group.athletes.some((athlete: any) => {
      if (filters.sportId && athlete.sport_id !== filters.sportId) return false
      if (filters.teamId && athlete.team_id !== filters.teamId) return false
      return true
    }),
  ),
)
const filteredUnassignedAthletes = computed(() =>
  overview.value.unassigned_athletes.filter((athlete: any) => {
    if (filters.sportId && athlete.sport_id !== filters.sportId) return false
    if (filters.teamId && athlete.team_id !== filters.teamId) return false
    return true
  }),
)
const filteredAssignedEntries = computed(() =>
  filteredAssignmentGroups.value.flatMap((group: any) =>
    group.entries
      .filter((entry: any) => {
        if (filters.sportId && entry.athlete.sport_id !== filters.sportId) return false
        if (filters.teamId && entry.athlete.team_id !== filters.teamId) return false
        return true
      })
      .map((entry: any) => ({
        ...entry,
        template: group.template,
        start_date: group.start_date,
        end_date: group.end_date,
      })),
  ),
)
const assignedEntriesByAthleteId = computed(() => {
  const map = new Map<number, any[]>()
  filteredAssignedEntries.value.forEach((entry: any) => {
    const bucket = map.get(entry.athlete.id)
    if (bucket) {
      bucket.push(entry)
      return
    }
    map.set(entry.athlete.id, [entry])
  })
  return map
})
const cancelTargetAthlete = computed(() =>
  cancelTargetAthleteId.value ? athletes.value.find((athlete) => athlete.id === cancelTargetAthleteId.value) || null : null,
)
const cancelTargetAssignments = computed(() =>
  cancelTargetAthleteId.value ? assignedEntriesByAthleteId.value.get(cancelTargetAthleteId.value) ?? [] : [],
)
const previewHasMissingBasis = computed(() =>
  Boolean(preview.value?.rows.some((row: any) => row.items.some((item: any) => item.status === 'missing_basis'))),
)

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
  await loadOverview()
}

async function loadOverview() {
  overview.value = await fetchAssignmentOverview(form.start_date)
  if (cancelTargetAthleteId.value && !(assignedEntriesByAthleteId.value.get(cancelTargetAthleteId.value)?.length)) {
    cancelTargetAthleteId.value = null
    confirmCancelAssignmentId.value = null
  }
}

function toggleAthlete(id: number) {
  if (form.athlete_ids.includes(id)) {
    form.athlete_ids = form.athlete_ids.filter((athleteId) => athleteId !== id)
    return
  }
  form.athlete_ids = [...form.athlete_ids, id]
}

function handleAthleteCardClick(athlete: any) {
  const assignedEntries = assignedEntriesByAthleteId.value.get(athlete.id) ?? []
  if (assignedEntries.length) {
    cancelTargetAthleteId.value = cancelTargetAthleteId.value === athlete.id ? null : athlete.id
    confirmCancelAssignmentId.value = null
    return
  }
  toggleAthlete(athlete.id)
}

function requestCancelAssignment(assignmentId: number) {
  confirmCancelAssignmentId.value = assignmentId
}

function resetCancelFlow() {
  confirmCancelAssignmentId.value = null
}

async function cancelAssignment(assignmentId: number) {
  cancelling.value = true
  try {
    await cancelBatchAssignments([assignmentId])
    confirmCancelAssignmentId.value = null
    await loadOverview()
  } finally {
    cancelling.value = false
  }
}

function selectUnassignedAthletes() {
  const ids = filteredUnassignedAthletes.value.map((athlete: any) => athlete.id)
  form.athlete_ids = Array.from(new Set([...form.athlete_ids, ...ids]))
}

async function generatePreview() {
  if (!form.athlete_ids.length || !form.template_id) {
    preview.value = null
    return
  }
  loadingPreview.value = true
  try {
    preview.value = await previewBatchAssignments({
      athlete_ids: form.athlete_ids,
      template_id: form.template_id,
      assigned_date: form.start_date,
      start_date: form.start_date,
      end_date: form.end_date,
      notes: form.notes,
      status: 'active',
    })
  } finally {
    loadingPreview.value = false
  }
}

async function submitAssignments() {
  if (!preview.value || previewHasMissingBasis.value) return
  submitting.value = true
  try {
    await createBatchAssignments({
      athlete_ids: form.athlete_ids,
      template_id: form.template_id,
      assigned_date: form.start_date,
      start_date: form.start_date,
      end_date: form.end_date,
      notes: form.notes,
      status: 'active',
    })
    form.athlete_ids = []
    form.template_id = 0
    form.notes = ''
    preview.value = null
    await hydrate()
  } finally {
    submitting.value = false
  }
}

watch(
  () => [form.start_date, filters.sportId, filters.teamId],
  async () => {
    await loadOverview()
  },
)

watch(
  () => [form.start_date, form.end_date, form.template_id, form.athlete_ids.join(',')],
  async () => {
    await generatePreview()
  },
)

watch(
  () => filters.sportId,
  () => {
    if (filters.teamId && !filteredTeams.value.some((team) => team.id === filters.teamId)) {
      filters.teamId = 0
    }
  },
)

onMounted(hydrate)
</script>

<template>
  <AppShell>
    <div class="assignment-page">
      <section class="panel overview-panel">
        <div class="section-head">
          <div>
            <p class="eyebrow">计划分配概览</p>
            <h3>先看当前和后续已经安排的计划</h3>
          </div>
          <div class="overview-toolbar">
            <label class="field compact">
              <span>查看日期</span>
              <input v-model="form.start_date" type="date" class="text-input" />
            </label>
            <select v-model.number="filters.sportId" class="text-input compact-input">
              <option :value="0">全部项目</option>
              <option v-for="sport in sports" :key="sport.id" :value="sport.id">{{ sport.name }}</option>
            </select>
            <select v-model.number="filters.teamId" class="text-input compact-input">
              <option :value="0">全部队伍</option>
              <option v-for="team in filteredTeams" :key="team.id" :value="team.id">{{ team.name }}</option>
            </select>
          </div>
        </div>

        <div class="summary-grid">
          <article class="summary-card">
            <span class="summary-label">已有计划人数</span>
            <strong>{{ overview.assigned_count }}</strong>
            <small>在下方队员卡片中直接打开并取消计划</small>
          </article>
          <article class="summary-card">
            <span class="summary-label">当前与后续计划组</span>
            <strong>{{ overview.group_count }}</strong>
            <small>按模板和时间段聚合展示</small>
          </article>
          <article class="summary-card summary-card--subtle">
            <span class="summary-label">未分配人数</span>
            <strong>{{ overview.unassigned_count }}</strong>
            <small>从当前日期往后仍无计划</small>
          </article>
        </div>

        <div class="overview-grid">
          <article class="overview-card overview-card--primary">
            <div class="section-head">
              <div>
                <p class="eyebrow">当前与后续计划</p>
                <h4>按模板和时间段归并展示当前进行中和即将开始的计划</h4>
              </div>
              <span class="muted">共 {{ filteredAssignmentGroups.length }} 组</span>
            </div>
            <div v-if="filteredAssignmentGroups.length" class="group-list">
              <div v-for="group in filteredAssignmentGroups" :key="group.assignment_ids.join('-')" class="group-card">
                <div class="group-head">
                  <div>
                    <strong>{{ group.template.name }}</strong>
                    <p>{{ group.start_date }} 至 {{ group.end_date }}</p>
                  </div>
                  <div class="group-badges">
                    <span class="status-badge" :class="group.group_status === 'active_now' ? 'status-badge--active' : 'status-badge--upcoming'">
                      {{ group.group_status === 'active_now' ? '进行中' : '即将开始' }}
                    </span>
                    <span class="badge">{{ group.athlete_count }} 人</span>
                  </div>
                </div>
                <p v-if="group.template.description" class="muted">{{ group.template.description }}</p>
                <div class="athlete-chip-list">
                  <span v-for="athlete in group.athletes" :key="athlete.id" class="athlete-chip">
                    {{ athlete.full_name }}
                    <small v-if="athlete.team?.name"> / {{ athlete.team.name }}</small>
                  </span>
                </div>
                <p v-if="group.notes.length" class="group-notes">备注：{{ group.notes.join('；') }}</p>
              </div>
            </div>
            <div v-else class="overview-empty">
              <strong>从当前日期往后还没有有效计划组</strong>
              <p class="muted">先在下方为队员分配模板后，这里会自动展示当前进行中和即将开始的计划。</p>
            </div>
          </article>

          <article class="overview-card overview-card--secondary">
            <div class="section-head section-head--tight">
              <div class="overview-side-meta">
                <p class="eyebrow">未分配队员</p>
                <h4>从当前日期往后还没有任何计划的人</h4>
                <span class="muted">共 {{ filteredUnassignedAthletes.length }} 人</span>
              </div>
            </div>
            <label class="checkbox-row checkbox-row--compact">
              <input v-model="filters.onlyUnassigned" type="checkbox" />
              <span>下方分配区只看未分配</span>
            </label>
            <div class="unassigned-list-wrap">
              <div class="unassigned-list">
                <div v-for="athlete in filteredUnassignedAthletes" :key="athlete.id" class="overview-row overview-row--compact">
                  <strong>{{ athlete.full_name }}</strong>
                  <span>{{ athlete.team?.name || '未分队' }}</span>
                </div>
              </div>
              <p v-if="!filteredUnassignedAthletes.length" class="muted">当前筛选条件下所有队员从当前日期往后都已有计划。</p>
            </div>
          </article>
        </div>
      </section>

      <section class="panel assignment-panel">
        <div class="section-head">
          <div>
            <p class="eyebrow">新增 / 调整计划分配</p>
            <h3>为指定队员设置模板和时间阶段</h3>
          </div>
          <button class="ghost-btn slim dark-btn" type="button" @click="selectUnassignedAthletes">选择当前未分配队员</button>
        </div>

        <div class="assignment-layout">
          <div class="wizard-panel">
            <div class="section-block">
              <div class="section-head">
                <div>
                  <p class="eyebrow">第一步</p>
                  <h4>选择队员</h4>
                </div>
                <span class="muted">已选 {{ form.athlete_ids.length }} 人</span>
              </div>
              <div class="athlete-grid">
                <button
                  v-for="athlete in filteredAthletes"
                  :key="athlete.id"
                  class="athlete-card"
                  :class="{
                    active: form.athlete_ids.includes(athlete.id),
                    'athlete-card--assigned': (assignedEntriesByAthleteId.get(athlete.id)?.length ?? 0) > 0,
                    'athlete-card--managing': cancelTargetAthleteId === athlete.id,
                  }"
                  type="button"
                  @click="handleAthleteCardClick(athlete)"
                >
                  <strong>{{ athlete.full_name }}</strong>
                  <span>{{ athlete.team?.name || '未分队' }}</span>
                  <small v-if="assignedEntriesByAthleteId.get(athlete.id)?.length">
                    已安排 {{ assignedEntriesByAthleteId.get(athlete.id)?.length }} 条计划，点击管理
                  </small>
                  <small v-else>{{ form.athlete_ids.includes(athlete.id) ? '已加入本次分配' : '点击加入本次分配' }}</small>
                </button>
              </div>
              <div v-if="cancelTargetAthlete && cancelTargetAssignments.length" class="cancel-panel">
                <div class="section-head section-head--tight">
                  <div>
                    <p class="eyebrow">已分配计划</p>
                    <h4>管理 {{ cancelTargetAthlete.full_name }} 的当前与后续计划</h4>
                  </div>
                  <button class="ghost-btn slim dark-btn" type="button" @click="cancelTargetAthleteId = null">关闭</button>
                </div>
                <p class="muted">点击删除按钮后还需要再次确认。取消后，这条计划将不再计入当前与后续有效计划。</p>
                <div class="cancel-list">
                  <div v-for="entry in cancelTargetAssignments" :key="entry.assignment_id" class="cancel-row">
                    <div class="cancel-main">
                      <strong>{{ entry.template.name }}</strong>
                      <span>{{ entry.start_date }} 至 {{ entry.end_date }}</span>
                      <small>{{ entry.notes || '无分配备注' }}</small>
                    </div>
                    <div class="cancel-actions">
                      <template v-if="confirmCancelAssignmentId === entry.assignment_id">
                        <span class="warning-text">确认删除这条计划？</span>
                        <button class="ghost-btn slim" type="button" :disabled="cancelling" @click="resetCancelFlow">取消</button>
                        <button class="ghost-btn slim danger-btn" type="button" :disabled="cancelling" @click="cancelAssignment(entry.assignment_id)">
                          {{ cancelling ? '删除中...' : '确认删除' }}
                        </button>
                      </template>
                      <button v-else class="ghost-btn slim danger-btn" type="button" :disabled="cancelling" @click="requestCancelAssignment(entry.assignment_id)">
                        删除计划
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div class="section-block">
              <p class="eyebrow">第二步</p>
              <h4>选择训练模板</h4>
              <select v-model.number="form.template_id" class="text-input">
                <option :value="0">请选择训练模板</option>
                <option v-for="template in templates" :key="template.id" :value="template.id">{{ template.name }}</option>
              </select>
              <p v-if="selectedTemplate" class="muted">模板详情请查看右侧预览。</p>
            </div>

            <div class="section-block">
              <p class="eyebrow">第三步</p>
              <h4>设置计划时间段</h4>
              <div class="grid three">
                <label class="field">
                  <span>开始日期</span>
                  <input v-model="form.start_date" type="date" class="text-input" />
                </label>
                <label class="field">
                  <span>结束日期</span>
                  <input v-model="form.end_date" type="date" class="text-input" />
                </label>
                <label class="field">
                  <span>分配备注</span>
                  <input v-model="form.notes" class="text-input" placeholder="例如：第一周主课、比赛周恢复" />
                </label>
              </div>
              <div class="submit-row">
                <button class="ghost-btn slim dark-btn" type="button" @click="generatePreview">刷新预览</button>
                <button class="primary-btn" type="button" :disabled="!preview || previewHasMissingBasis || submitting" @click="submitAssignments">
                  {{ submitting ? '正在提交...' : '确认分配计划' }}
                </button>
              </div>
              <p v-if="previewHasMissingBasis" class="warning-text">当前预览中存在缺少测试基准的动作，请先补全测试数据或改用固定重量。</p>
              <p v-else-if="loadingPreview" class="muted">正在生成分配预览...</p>
            </div>
          </div>

          <AssignmentPreviewPanel :preview="preview" :selected-template="selectedTemplate" />
        </div>
      </section>
    </div>
  </AppShell>
</template>

<style scoped>
.assignment-page,
.overview-panel,
.assignment-panel,
.overview-card,
.group-list,
.unassigned-list,
.wizard-panel,
.section-block,
.cancel-list {
  display: grid;
  gap: 16px;
}

.assignment-page {
  gap: 18px;
}

.assignment-layout,
.overview-grid {
  display: grid;
  grid-template-columns: 1.6fr 0.75fr;
  gap: 18px;
  align-items: start;
}

.section-head,
.overview-toolbar,
.submit-row,
.group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.summary-card,
.group-card {
  display: grid;
  gap: 10px;
  padding: 16px;
  border-radius: 18px;
  background: var(--panel-soft);
}

.summary-card--subtle {
  background: rgba(241, 245, 249, 0.76);
}

.summary-label,
.eyebrow,
.muted,
.warning-text,
.field span,
.summary-card small,
.group-head p,
.group-notes,
.overview-row span,
.athlete-card span,
.athlete-card small,
.preview-row span,
.cancel-main small {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

.summary-card strong {
  font-size: 32px;
}

.badge {
  min-width: 64px;
  padding: 8px 12px;
  border-radius: 999px;
  text-align: center;
  background: rgba(15, 118, 110, 0.12);
  color: var(--primary);
  font-weight: 600;
}

.group-badges {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.status-badge {
  min-width: 72px;
  padding: 8px 12px;
  border-radius: 999px;
  text-align: center;
  font-size: 12px;
  font-weight: 600;
}

.status-badge--active {
  background: rgba(15, 118, 110, 0.16);
  color: var(--primary);
}

.status-badge--upcoming {
  background: rgba(59, 130, 246, 0.14);
  color: #1d4ed8;
}

.athlete-chip-list,
.athlete-grid,
.grid.three {
  display: grid;
  gap: 12px;
}

.athlete-chip-list {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.athlete-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.grid.three {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.athlete-chip,
.overview-row,
.preview-row,
.athlete-card,
.cancel-row {
  display: grid;
  gap: 4px;
  text-align: left;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
}

.overview-card--primary {
  gap: 14px;
}

.overview-card--secondary {
  gap: 12px;
  align-self: start;
}

.overview-empty {
  display: grid;
  gap: 8px;
  min-height: 180px;
  padding: 18px;
  border-radius: 18px;
  place-content: center start;
  background: rgba(241, 245, 249, 0.72);
}

.overview-empty strong {
  font-size: 18px;
}

.section-head--tight {
  align-items: start;
}

.overview-side-meta {
  display: grid;
  gap: 4px;
}

.athlete-card {
  border: 1px solid transparent;
  background: var(--panel-soft);
}

.athlete-card.active {
  background: #d1fae5;
  border: 1px solid rgba(15, 118, 110, 0.18);
}

.athlete-card--assigned {
  background: rgba(239, 246, 255, 0.82);
  border-color: rgba(59, 130, 246, 0.2);
}

.athlete-card--managing {
  background: rgba(224, 231, 255, 0.8);
  border-color: rgba(79, 70, 229, 0.24);
}

.field {
  display: grid;
  gap: 6px;
}

.compact {
  min-width: 180px;
}

.compact-input {
  min-width: 180px;
}

.warning-text {
  color: var(--danger);
}

.checkbox-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--muted);
  font-size: 13px;
}

.checkbox-row--compact {
  align-self: start;
}

.group-list {
  gap: 12px;
}

.group-card {
  gap: 8px;
  padding: 14px 16px;
}

.cancel-panel {
  display: grid;
  gap: 12px;
  padding: 16px;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.86);
  border: 1px solid rgba(15, 23, 42, 0.08);
}

.cancel-list {
  gap: 12px;
}

.cancel-row {
  grid-template-columns: 1fr auto;
  align-items: center;
  gap: 16px;
  background: rgba(255, 255, 255, 0.82);
}

.cancel-main,
.cancel-actions {
  display: grid;
  gap: 6px;
}

.cancel-actions {
  justify-items: end;
  text-align: right;
}

.unassigned-list-wrap {
  display: grid;
  gap: 10px;
}

.unassigned-list {
  gap: 10px;
  max-height: 420px;
  padding-right: 4px;
  overflow-y: auto;
}

.overview-row--compact {
  gap: 2px;
  padding: 12px 14px;
}

.overview-row--compact strong {
  font-size: 15px;
}

.dark-btn {
  background: #0f172a;
  color: white;
}

.danger-btn {
  background: #b91c1c;
  color: white;
}

@media (max-width: 1280px) {
  .overview-grid,
  .assignment-layout {
    grid-template-columns: 1fr;
  }

  .unassigned-list {
    max-height: none;
    overflow: visible;
    padding-right: 0;
  }
}

@media (max-width: 900px) {
  .summary-grid,
  .athlete-grid,
  .athlete-chip-list,
  .grid.three,
  .cancel-row {
    grid-template-columns: 1fr;
  }

  .cancel-actions {
    text-align: left;
    justify-items: start;
  }
}
</style>
