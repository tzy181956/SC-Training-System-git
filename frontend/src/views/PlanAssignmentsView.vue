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
const showAssignedList = ref(false)
const selectedAssignedIds = ref<number[]>([])

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
const previewHasMissingBasis = computed(() =>
  Boolean(preview.value?.rows.some((row: any) => row.items.some((item: any) => item.status !== '可分配'))),
)
const allVisibleAssignedSelected = computed(
  () =>
    filteredAssignedEntries.value.length > 0 &&
    filteredAssignedEntries.value.every((entry: any) => selectedAssignedIds.value.includes(entry.assignment_id)),
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
  selectedAssignedIds.value = selectedAssignedIds.value.filter((assignmentId) =>
    overview.value.assignment_groups.some((group: any) => group.assignment_ids.includes(assignmentId)),
  )
}

function toggleAthlete(id: number) {
  if (form.athlete_ids.includes(id)) {
    form.athlete_ids = form.athlete_ids.filter((athleteId) => athleteId !== id)
    return
  }
  form.athlete_ids = [...form.athlete_ids, id]
}

function toggleAssignedList() {
  showAssignedList.value = !showAssignedList.value
  if (!showAssignedList.value) {
    selectedAssignedIds.value = []
  }
}

function toggleAssignedSelection(assignmentId: number) {
  if (selectedAssignedIds.value.includes(assignmentId)) {
    selectedAssignedIds.value = selectedAssignedIds.value.filter((id) => id !== assignmentId)
    return
  }
  selectedAssignedIds.value = [...selectedAssignedIds.value, assignmentId]
}

function selectVisibleAssigned() {
  if (allVisibleAssignedSelected.value) {
    const visibleIds = new Set(filteredAssignedEntries.value.map((entry: any) => entry.assignment_id))
    selectedAssignedIds.value = selectedAssignedIds.value.filter((id) => !visibleIds.has(id))
    return
  }
  selectedAssignedIds.value = Array.from(
    new Set([...selectedAssignedIds.value, ...filteredAssignedEntries.value.map((entry: any) => entry.assignment_id)]),
  )
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

async function cancelSelectedAssignments() {
  if (!selectedAssignedIds.value.length) return
  cancelling.value = true
  try {
    await cancelBatchAssignments(selectedAssignedIds.value)
    selectedAssignedIds.value = []
    await loadOverview()
  } finally {
    cancelling.value = false
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
            <h3>先看当前有哪些计划在执行</h3>
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
          <button class="summary-card summary-button" type="button" @click="toggleAssignedList">
            <span class="summary-label">已有计划人数</span>
            <strong>{{ overview.assigned_count }}</strong>
            <small>{{ showAssignedList ? '点击收起已分配列表' : '点击展开并直接取消计划' }}</small>
          </button>
          <article class="summary-card">
            <span class="summary-label">未分配人数</span>
            <strong>{{ overview.unassigned_count }}</strong>
            <small>当前日期下还没有有效计划</small>
          </article>
          <article class="summary-card">
            <span class="summary-label">进行中的计划组</span>
            <strong>{{ overview.group_count }}</strong>
            <small>按模板和时间段聚合</small>
          </article>
        </div>

        <section v-if="showAssignedList" class="assigned-expand">
          <div class="section-head">
            <div>
              <p class="eyebrow">已分配列表</p>
              <h4>勾选需要取消计划的队员</h4>
            </div>
            <div class="assigned-actions">
              <button class="ghost-btn slim dark-btn" type="button" @click="selectVisibleAssigned">
                {{ allVisibleAssignedSelected ? '取消全选' : '全选当前列表' }}
              </button>
              <button class="ghost-btn slim danger-btn" type="button" :disabled="!selectedAssignedIds.length || cancelling" @click="cancelSelectedAssignments">
                {{ cancelling ? '正在取消...' : `取消已选 ${selectedAssignedIds.length} 人计划` }}
              </button>
              <button class="ghost-btn slim dark-btn" type="button" @click="toggleAssignedList">收起</button>
            </div>
          </div>
          <p class="muted">取消后会保留历史记录，但不再作为当前有效计划统计。</p>
          <div class="assigned-list">
            <label v-for="entry in filteredAssignedEntries" :key="entry.assignment_id" class="assigned-row">
              <div class="assigned-check">
                <input :checked="selectedAssignedIds.includes(entry.assignment_id)" type="checkbox" @change="toggleAssignedSelection(entry.assignment_id)" />
              </div>
              <div class="assigned-main">
                <strong>{{ entry.athlete.full_name }}</strong>
                <span>{{ entry.athlete.team?.name || '未分队' }} / {{ entry.athlete.training_level || '未设置训练等级' }}</span>
              </div>
              <div class="assigned-side">
                <strong>{{ entry.template.name }}</strong>
                <span>{{ entry.start_date }} 至 {{ entry.end_date }}</span>
                <small>{{ entry.notes || '无分配备注' }}</small>
              </div>
            </label>
            <p v-if="!filteredAssignedEntries.length" class="muted">当前筛选条件下没有可以取消的分配记录。</p>
          </div>
        </section>

        <div class="overview-grid">
          <article class="overview-card">
            <div class="section-head">
              <div>
                <p class="eyebrow">进行中的计划</p>
                <h4>同模板同时间段的队员已归并展示</h4>
              </div>
              <span class="muted">共 {{ filteredAssignmentGroups.length }} 组</span>
            </div>
            <div class="group-list">
              <div v-for="group in filteredAssignmentGroups" :key="group.assignment_ids.join('-')" class="group-card">
                <div class="group-head">
                  <div>
                    <strong>{{ group.template.name }}</strong>
                    <p>{{ group.start_date }} 至 {{ group.end_date }}</p>
                  </div>
                  <span class="badge">{{ group.athlete_count }} 人</span>
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
              <p v-if="!filteredAssignmentGroups.length" class="muted">当前筛选条件下没有进行中的计划组。</p>
            </div>
          </article>

          <article class="overview-card">
            <div class="section-head">
              <div>
                <p class="eyebrow">未分配队员</p>
                <h4>当前日期下还没有计划的人</h4>
              </div>
              <label class="checkbox-row">
                <input v-model="filters.onlyUnassigned" type="checkbox" />
                <span>下方分配区只看未分配</span>
              </label>
            </div>
            <div class="unassigned-list">
              <div v-for="athlete in filteredUnassignedAthletes" :key="athlete.id" class="overview-row">
                <strong>{{ athlete.full_name }}</strong>
                <span>{{ athlete.team?.name || '未分队' }} / {{ athlete.training_level || '未设置训练等级' }}</span>
              </div>
              <p v-if="!filteredUnassignedAthletes.length" class="muted">当前筛选条件下所有队员都已有计划。</p>
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
                  :class="{ active: form.athlete_ids.includes(athlete.id) }"
                  type="button"
                  @click="toggleAthlete(athlete.id)"
                >
                  <strong>{{ athlete.full_name }}</strong>
                  <span>{{ athlete.team?.name || '未分队' }} / {{ athlete.position || '未填写位置' }}</span>
                  <small>{{ athlete.training_level || '未填写训练等级' }}</small>
                </button>
              </div>
            </div>

            <div class="section-block">
              <p class="eyebrow">第二步</p>
              <h4>选择训练模板</h4>
              <select v-model.number="form.template_id" class="text-input">
                <option :value="0">请选择训练模板</option>
                <option v-for="template in templates" :key="template.id" :value="template.id">{{ template.name }}</option>
              </select>
              <div v-if="selectedTemplate" class="template-preview">
                <h5>{{ selectedTemplate.name }}</h5>
                <p>{{ selectedTemplate.description || '暂无模板说明' }}</p>
                <div class="preview-list">
                  <div v-for="item in selectedTemplate.items" :key="item.id" class="preview-row">
                    <strong>{{ item.sort_order }}. {{ item.exercise.name }}</strong>
                    <span>
                      {{ item.prescribed_sets }} 组 x {{ item.prescribed_reps }} 次
                      <template v-if="item.initial_load_mode === 'percent_1rm'"> / 按最近测试的 {{ item.initial_load_value }}%</template>
                      <template v-else> / 固定重量 {{ item.initial_load_value ?? 0 }} 公斤</template>
                    </span>
                  </div>
                </div>
              </div>
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

          <AssignmentPreviewPanel :preview="preview" />
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
.template-preview,
.preview-list,
.assigned-expand,
.assigned-list {
  display: grid;
  gap: 16px;
}

.assignment-page {
  gap: 18px;
}

.assignment-layout,
.overview-grid {
  display: grid;
  grid-template-columns: 1.2fr 0.9fr;
  gap: 18px;
}

.section-head,
.overview-toolbar,
.submit-row,
.group-head,
.assigned-actions {
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

.summary-button {
  text-align: left;
}

.summary-button:hover {
  background: #d1fae5;
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
.assigned-row span,
.assigned-side small {
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
.assigned-row {
  display: grid;
  gap: 4px;
  text-align: left;
  padding: 14px 16px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
}

.assigned-row {
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 16px;
}

.assigned-main,
.assigned-side {
  display: grid;
  gap: 4px;
}

.assigned-side {
  text-align: right;
}

.athlete-card {
  background: var(--panel-soft);
}

.athlete-card.active {
  background: #d1fae5;
  border: 1px solid rgba(15, 118, 110, 0.18);
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
}

@media (max-width: 900px) {
  .summary-grid,
  .athlete-grid,
  .athlete-chip-list,
  .grid.three,
  .assigned-row {
    grid-template-columns: 1fr;
  }

  .assigned-side {
    text-align: left;
  }
}
</style>
