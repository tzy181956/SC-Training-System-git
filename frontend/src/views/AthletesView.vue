<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, reactive, ref } from 'vue'

import {
  type AthleteRead,
  type SportRead,
  type TeamRead,
  createAthlete,
  createSport,
  createTeam,
  deleteAthlete,
  deleteSport,
  deleteTeam,
  updateAthlete,
} from '@/api/athletes'
import AppShell from '@/components/layout/AppShell.vue'
import { useAthletesStore } from '@/stores/athletes'
import { confirmDangerousAction } from '@/utils/dangerousAction'

type SportItem = SportRead
type TeamItem = TeamRead
type AthleteItem = AthleteRead

const store = useAthletesStore()
const selectedId = ref<number | null>(null)

const sportManagerOpen = ref(false)
const teamManagerOpen = ref(false)
const sportSubmitting = ref(false)
const teamSubmitting = ref(false)
const deletingSportId = ref<number | null>(null)
const deletingTeamId = ref<number | null>(null)
const sportManagerError = ref('')
const teamManagerError = ref('')

const filters = reactive({
  keyword: '',
  sportId: '',
  teamId: '',
  gender: '',
})

const form = reactive({
  code: '',
  full_name: '',
  sport_id: null as number | null,
  team_id: null as number | null,
  gender: '',
  position: '',
  height: null as number | null,
  weight: null as number | null,
  body_fat_percentage: null as number | null,
  wingspan: null as number | null,
  standing_reach: null as number | null,
  notes: '',
  is_active: true,
})

const sportForm = reactive({
  name: '',
  notes: '',
})

const teamForm = reactive({
  sport_id: null as number | null,
  name: '',
  notes: '',
})

onMounted(async () => {
  await store.hydrate()
  if (store.athletes[0]) selectAthlete(store.athletes[0] as AthleteItem)
})

const selectedAthlete = computed(() => store.athletes.find((item) => item.id === selectedId.value) as AthleteItem | undefined)

const filteredTeams = computed(() => {
  if (!filters.sportId) return store.teams as TeamItem[]
  return (store.teams as TeamItem[]).filter((team) => String(team.sport_id) === filters.sportId)
})

const availableFormTeams = computed(() => {
  if (!form.sport_id) return store.teams as TeamItem[]
  return (store.teams as TeamItem[]).filter((team) => team.sport_id === form.sport_id)
})

const filteredAthletes = computed(() =>
  (store.athletes as AthleteItem[]).filter((athlete) => {
    const keyword = filters.keyword.trim().toLowerCase()
    if (keyword) {
      const targets = [athlete.code, athlete.full_name, athlete.sport?.name, athlete.team?.name, athlete.gender]
      if (!targets.some((value) => String(value || '').toLowerCase().includes(keyword))) {
        return false
      }
    }

    if (filters.sportId && String(athlete.sport_id || athlete.sport?.id || '') !== filters.sportId) return false
    if (filters.teamId && String(athlete.team_id || athlete.team?.id || '') !== filters.teamId) return false
    if (filters.gender && String(athlete.gender || '') !== filters.gender) return false
    return true
  }),
)

const canSubmitSport = computed(() => sportForm.name.trim().length > 0)
const canSubmitTeam = computed(() => teamForm.name.trim().length > 0 && teamForm.sport_id !== null)

function selectAthlete(athlete: AthleteItem) {
  selectedId.value = athlete.id
  Object.assign(form, {
    code: athlete.code || '',
    full_name: athlete.full_name || '',
    sport_id: athlete.sport_id ?? null,
    team_id: athlete.team_id ?? null,
    gender: athlete.gender || '',
    position: athlete.position || '',
    height: athlete.height ?? null,
    weight: athlete.weight ?? null,
    body_fat_percentage: athlete.body_fat_percentage ?? null,
    wingspan: athlete.wingspan ?? null,
    standing_reach: athlete.standing_reach ?? null,
    notes: athlete.notes || '',
    is_active: athlete.is_active ?? true,
  })
}

async function saveAthlete() {
  try {
    const savedAthlete = selectedId.value ? await updateAthlete(selectedId.value, form) : await createAthlete(form)
    await store.hydrate()

    const nextId = selectedId.value ?? savedAthlete?.id ?? null
    if (nextId) {
      const refreshed = (store.athletes as AthleteItem[]).find((item) => item.id === nextId)
      if (refreshed) {
        selectAthlete(refreshed)
        return
      }
    }
  } catch (error) {
    window.alert(extractErrorMessage(error, '保存运动员失败，请稍后重试。'))
  }
}

async function removeAthlete() {
  if (!selectedAthlete.value) return

  const athlete = selectedAthlete.value
  const confirmed = confirmDangerousAction({
    title: '删除运动员',
    impactLines: [
      `运动员：${athlete.full_name}`,
      `所属项目 / 队伍：${athlete.sport?.name || '未分项目'} / ${athlete.team?.name || '未分队伍'}`,
      '如果该运动员已有计划分配、训练记录或测试记录，系统会拒绝删除。',
    ],
    recommendation: '建议先确认该运动员没有历史训练或测试数据。',
  })
  if (!confirmed) return

  try {
    await deleteAthlete(athlete.id, { confirmed: true, actor_name: '管理模式' })
    await store.hydrate()

    const nextAthlete = filteredAthletes.value[0] || ((store.athletes as AthleteItem[])[0] ?? null)
    if (nextAthlete) {
      selectAthlete(nextAthlete)
      return
    }
    resetForm()
  } catch (error) {
    window.alert(extractErrorMessage(error, '删除运动员失败，请稍后重试。'))
  }
}

function resetForm() {
  selectedId.value = null
  Object.assign(form, {
    code: '',
    full_name: '',
    sport_id: null,
    team_id: null,
    gender: '',
    position: '',
    height: null,
    weight: null,
    body_fat_percentage: null,
    wingspan: null,
    standing_reach: null,
    notes: '',
    is_active: true,
  })
}

function handleSportFilterChange() {
  if (filters.teamId && !filteredTeams.value.some((team) => String(team.id) === filters.teamId)) {
    filters.teamId = ''
  }
}

function handleFormSportChange() {
  if (
    form.team_id &&
    !availableFormTeams.value.some((team) => team.id === form.team_id)
  ) {
    form.team_id = null
  }
}

function openSportManager() {
  sportManagerError.value = ''
  sportManagerOpen.value = true
}

function closeSportManager() {
  sportManagerOpen.value = false
  sportManagerError.value = ''
  resetSportManagerForm()
}

function openTeamManager() {
  teamManagerError.value = ''
  teamManagerOpen.value = true
  teamForm.sport_id = resolvePreferredSportId()
}

function closeTeamManager() {
  teamManagerOpen.value = false
  teamManagerError.value = ''
  resetTeamManagerForm()
}

async function submitSport() {
  sportManagerError.value = ''
  if (!canSubmitSport.value) {
    sportManagerError.value = '项目名称不能为空'
    return
  }

  sportSubmitting.value = true
  try {
    await createSport({
      name: sportForm.name.trim(),
      code: buildEntityCode(sportForm.name, 'sport'),
      notes: normalizeOptionalText(sportForm.notes),
    })
    resetSportManagerForm()
    await refreshLookupData()
  } catch (error) {
    sportManagerError.value = extractErrorMessage(error, '新增项目失败，请稍后重试。')
  } finally {
    sportSubmitting.value = false
  }
}

async function submitTeam() {
  teamManagerError.value = ''
  if (teamForm.sport_id === null) {
    teamManagerError.value = '请先选择所属项目'
    return
  }
  if (!teamForm.name.trim()) {
    teamManagerError.value = '队伍名称不能为空'
    return
  }

  teamSubmitting.value = true
  try {
    await createTeam({
      sport_id: teamForm.sport_id,
      name: teamForm.name.trim(),
      code: buildEntityCode(teamForm.name, 'team'),
      notes: normalizeOptionalText(teamForm.notes),
    })
    resetTeamManagerForm()
    teamForm.sport_id = resolvePreferredSportId()
    await refreshLookupData()
  } catch (error) {
    teamManagerError.value = extractErrorMessage(error, '新增队伍失败，请稍后重试。')
  } finally {
    teamSubmitting.value = false
  }
}

async function removeSport(sport: SportItem) {
  const confirmed = confirmDangerousAction({
    title: '删除项目',
    impactLines: [
      `项目：${sport.name}`,
      '如果该项目下仍有队伍、运动员或训练模板，系统会拒绝删除。',
    ],
    recommendation: '建议先确认该项目下没有队伍、运动员和模板引用。',
  })
  if (!confirmed) return

  deletingSportId.value = sport.id
  sportManagerError.value = ''
  try {
    await deleteSport(sport.id, { confirmed: true, actor_name: '管理模式' })
    await refreshLookupData()
  } catch (error) {
    sportManagerError.value = extractErrorMessage(error, '删除项目失败，请稍后重试。')
  } finally {
    deletingSportId.value = null
  }
}

async function removeTeam(team: TeamItem) {
  const confirmed = confirmDangerousAction({
    title: '删除队伍',
    impactLines: [
      `队伍：${team.name}`,
      `所属项目：${team.sport?.name || '未分项目'}`,
      '如果该队伍仍被运动员、训练模板或用户引用，系统会拒绝删除。',
    ],
    recommendation: '建议先确认该队伍没有运动员、模板和用户引用。',
  })
  if (!confirmed) return

  deletingTeamId.value = team.id
  teamManagerError.value = ''
  try {
    await deleteTeam(team.id, { confirmed: true, actor_name: '管理模式' })
    await refreshLookupData()
  } catch (error) {
    teamManagerError.value = extractErrorMessage(error, '删除队伍失败，请稍后重试。')
  } finally {
    deletingTeamId.value = null
  }
}

async function refreshLookupData() {
  await store.hydrate()

  if (filters.sportId && !(store.sports as SportItem[]).some((sport) => String(sport.id) === filters.sportId)) {
    filters.sportId = ''
  }
  handleSportFilterChange()

  if (form.sport_id && !(store.sports as SportItem[]).some((sport) => sport.id === form.sport_id)) {
    form.sport_id = null
  }
  if (form.team_id && !(store.teams as TeamItem[]).some((team) => team.id === form.team_id)) {
    form.team_id = null
  }
  handleFormSportChange()

  if (teamForm.sport_id && !(store.sports as SportItem[]).some((sport) => sport.id === teamForm.sport_id)) {
    teamForm.sport_id = resolvePreferredSportId()
  }
}

function resetSportManagerForm() {
  sportForm.name = ''
  sportForm.notes = ''
}

function resetTeamManagerForm() {
  teamForm.name = ''
  teamForm.notes = ''
  teamForm.sport_id = null
}

function resolvePreferredSportId() {
  if (form.sport_id) return form.sport_id
  if (filters.sportId) {
    const sportId = Number(filters.sportId)
    if (Number.isFinite(sportId)) return sportId
  }
  return (store.sports as SportItem[])[0]?.id ?? null
}

function buildEntityCode(name: string, prefix: 'sport' | 'team') {
  const asciiSlug = name
    .trim()
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 40)

  if (asciiSlug) return asciiSlug
  return `${prefix}-${Date.now()}`
}

function normalizeOptionalText(value: string) {
  const normalized = value.trim()
  return normalized || null
}

function extractErrorMessage(error: unknown, fallback = '操作失败，请稍后重试。') {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    if (Array.isArray(detail) && detail.length) return detail.join('；')
    if (error.message) return error.message
  }
  return fallback
}
</script>

<template>
  <AppShell>
    <div class="split-view">
      <div class="panel list-panel">
        <div class="toolbar">
          <h3>运动员列表</h3>
          <div class="toolbar-actions">
            <button class="ghost-btn slim" type="button" @click="openSportManager">管理项目</button>
            <button class="ghost-btn slim" type="button" @click="openTeamManager">管理队伍</button>
            <button class="primary-btn slim" type="button" @click="resetForm">新建</button>
          </div>
        </div>

        <div class="stacked-filters">
          <label class="field filter-row filter-row--search">
            <span class="field-label">搜索</span>
            <input v-model="filters.keyword" class="text-input filter-control" placeholder="搜索姓名、项目、队伍或性别" />
          </label>

          <div class="filter-row filter-row--triple">
            <label class="field">
              <span class="field-label">项目</span>
              <select v-model="filters.sportId" class="text-input filter-control filter-select" @change="handleSportFilterChange">
                <option value="">全部项目</option>
                <option v-for="sport in store.sports" :key="sport.id" :value="String(sport.id)">{{ sport.name }}</option>
              </select>
            </label>
            <label class="field">
              <span class="field-label">队伍</span>
              <select v-model="filters.teamId" class="text-input filter-control filter-select">
                <option value="">全部队伍</option>
                <option v-for="team in filteredTeams" :key="team.id" :value="String(team.id)">{{ team.name }}</option>
              </select>
            </label>
            <label class="field">
              <span class="field-label">性别</span>
              <select v-model="filters.gender" class="text-input filter-control filter-select">
                <option value="">全部性别</option>
                <option value="男">男</option>
                <option value="女">女</option>
              </select>
            </label>
          </div>
        </div>

        <div class="list-scroll">
          <p class="filter-summary">共 {{ filteredAthletes.length }} 人</p>
          <button
            v-for="athlete in filteredAthletes"
            :key="athlete.id"
            class="row-card adaptive-card"
            :class="{ active: athlete.id === selectedId }"
            type="button"
            @click="selectAthlete(athlete)"
          >
            <strong class="adaptive-card-title">{{ athlete.full_name }}</strong>
            <span class="adaptive-card-subtitle adaptive-card-clamp-2">
              {{ athlete.sport?.name || '未分项目' }} / {{ athlete.team?.name || '未分队伍' }}
            </span>
            <small class="adaptive-card-meta adaptive-card-clamp-1">
              {{ athlete.code }}{{ athlete.gender ? ` / ${athlete.gender}` : '' }}
            </small>
          </button>
          <div v-if="!filteredAthletes.length" class="empty-state">没有符合筛选条件的运动员。</div>
        </div>
      </div>

      <div class="panel form-panel">
        <h3>{{ selectedAthlete ? '编辑运动员' : '新增运动员' }}</h3>

        <label class="field">
          <span class="field-label">姓名 <strong class="required-mark">*</strong></span>
          <input v-model="form.full_name" class="text-input" placeholder="必填" />
        </label>

        <label class="field">
          <span class="field-label">运动员编码</span>
          <input
            v-model.trim="form.code"
            class="text-input"
            :placeholder="selectedAthlete ? '可手动修改，需全系统唯一' : '留空则保存后自动生成'"
          />
        </label>

        <div class="two-col">
          <label class="field">
            <span class="field-label">所属项目</span>
            <select v-model="form.sport_id" class="text-input" @change="handleFormSportChange">
              <option :value="null">未选择</option>
              <option v-for="sport in store.sports" :key="sport.id" :value="sport.id">{{ sport.name }}</option>
            </select>
          </label>
          <label class="field">
            <span class="field-label">所属队伍</span>
            <select v-model="form.team_id" class="text-input">
              <option :value="null">未选择</option>
              <option v-for="team in availableFormTeams" :key="team.id" :value="team.id">{{ team.name }}</option>
            </select>
          </label>
        </div>

        <div class="two-col">
          <label class="field">
            <span class="field-label">性别</span>
            <select v-model="form.gender" class="text-input">
              <option value="">未选择</option>
              <option value="男">男</option>
              <option value="女">女</option>
            </select>
          </label>
          <label class="field">
            <span class="field-label">位置 / 角色</span>
            <input v-model="form.position" class="text-input" placeholder="可选" />
          </label>
        </div>

        <div class="metrics-grid">
          <label class="field">
            <span class="field-label">身高 (cm)</span>
            <input v-model.number="form.height" type="number" step="0.1" class="text-input" />
          </label>
          <label class="field">
            <span class="field-label">体重 (kg)</span>
            <input v-model.number="form.weight" type="number" step="0.1" class="text-input" />
          </label>
          <label class="field">
            <span class="field-label">体脂率 (%)</span>
            <input v-model.number="form.body_fat_percentage" type="number" step="0.1" class="text-input" />
          </label>
          <label class="field">
            <span class="field-label">臂展 (cm)</span>
            <input v-model.number="form.wingspan" type="number" step="0.1" class="text-input" />
          </label>
          <label class="field">
            <span class="field-label">站摸 (cm)</span>
            <input v-model.number="form.standing_reach" type="number" step="0.1" class="text-input" />
          </label>
        </div>

        <label class="field">
          <span class="field-label">备注</span>
          <textarea v-model="form.notes" class="text-input area" placeholder="可选" />
        </label>

        <div class="form-actions">
          <button v-if="selectedAthlete" class="ghost-btn danger-btn" type="button" @click="removeAthlete">删除运动员</button>
          <button class="primary-btn" type="button" @click="saveAthlete">保存运动员</button>
        </div>
      </div>
    </div>
  </AppShell>

  <teleport to="body">
    <div v-if="sportManagerOpen" class="manager-overlay" @click="closeSportManager">
      <section class="manager-dialog panel" role="dialog" aria-modal="true" aria-labelledby="sport-manager-title" @click.stop>
        <div class="manager-dialog-head">
          <div>
            <p class="section-title">运动员模块</p>
            <h3 id="sport-manager-title">管理项目</h3>
          </div>
          <button class="ghost-btn slim" type="button" @click="closeSportManager">关闭</button>
        </div>

        <div class="manager-dialog-body">
          <div class="manager-list-block">
            <div class="manager-block-head">
              <strong>已有项目</strong>
              <span>{{ store.sports.length }} 个</span>
            </div>
            <p v-if="sportManagerError" class="manager-error">{{ sportManagerError }}</p>
            <div v-if="!store.sports.length" class="empty-state manager-empty">还没有项目，可先新增一个项目。</div>
            <div v-else class="manager-list">
              <div v-for="sport in store.sports" :key="sport.id" class="manager-row">
                <div class="manager-row-copy">
                  <strong>{{ sport.name }}</strong>
                  <span class="manager-row-meta">编码：{{ sport.code }}</span>
                  <p v-if="sport.notes" class="manager-row-notes">{{ sport.notes }}</p>
                </div>
                <button
                  class="ghost-btn slim danger-btn"
                  type="button"
                  :disabled="deletingSportId === sport.id"
                  @click="removeSport(sport)"
                >
                  {{ deletingSportId === sport.id ? '删除中...' : '删除' }}
                </button>
              </div>
            </div>
          </div>

          <form class="manager-form-block" @submit.prevent="submitSport">
            <div class="manager-block-head">
              <strong>新增项目</strong>
              <span>编码按名称自动生成</span>
            </div>
            <label class="field">
              <span class="field-label">项目名称 <strong class="required-mark">*</strong></span>
              <input v-model="sportForm.name" class="text-input" placeholder="例如：篮球" />
            </label>
            <label class="field">
              <span class="field-label">备注</span>
              <textarea v-model="sportForm.notes" class="text-input manager-textarea" placeholder="可选" />
            </label>
            <div class="manager-form-actions">
              <button class="primary-btn" type="submit" :disabled="sportSubmitting || !canSubmitSport">
                {{ sportSubmitting ? '保存中...' : '新增项目' }}
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  </teleport>

  <teleport to="body">
    <div v-if="teamManagerOpen" class="manager-overlay" @click="closeTeamManager">
      <section class="manager-dialog panel" role="dialog" aria-modal="true" aria-labelledby="team-manager-title" @click.stop>
        <div class="manager-dialog-head">
          <div>
            <p class="section-title">运动员模块</p>
            <h3 id="team-manager-title">管理队伍</h3>
          </div>
          <button class="ghost-btn slim" type="button" @click="closeTeamManager">关闭</button>
        </div>

        <div class="manager-dialog-body">
          <div class="manager-list-block">
            <div class="manager-block-head">
              <strong>已有队伍</strong>
              <span>{{ store.teams.length }} 支</span>
            </div>
            <p v-if="teamManagerError" class="manager-error">{{ teamManagerError }}</p>
            <div v-if="!store.teams.length" class="empty-state manager-empty">还没有队伍，可先选择项目后新增。</div>
            <div v-else class="manager-list">
              <div v-for="team in store.teams" :key="team.id" class="manager-row">
                <div class="manager-row-copy">
                  <strong>{{ team.name }}</strong>
                  <span class="manager-row-meta">所属项目：{{ team.sport?.name || '未分项目' }}</span>
                  <span class="manager-row-meta">编码：{{ team.code }}</span>
                  <p v-if="team.notes" class="manager-row-notes">{{ team.notes }}</p>
                </div>
                <button
                  class="ghost-btn slim danger-btn"
                  type="button"
                  :disabled="deletingTeamId === team.id"
                  @click="removeTeam(team)"
                >
                  {{ deletingTeamId === team.id ? '删除中...' : '删除' }}
                </button>
              </div>
            </div>
          </div>

          <form class="manager-form-block" @submit.prevent="submitTeam">
            <div class="manager-block-head">
              <strong>新增队伍</strong>
              <span>编码按名称自动生成</span>
            </div>
            <label class="field">
              <span class="field-label">所属项目 <strong class="required-mark">*</strong></span>
              <select v-model="teamForm.sport_id" class="text-input">
                <option :value="null">请选择项目</option>
                <option v-for="sport in store.sports" :key="sport.id" :value="sport.id">{{ sport.name }}</option>
              </select>
            </label>
            <label class="field">
              <span class="field-label">队伍名称 <strong class="required-mark">*</strong></span>
              <input v-model="teamForm.name" class="text-input" placeholder="例如：U18 男队" />
            </label>
            <label class="field">
              <span class="field-label">备注</span>
              <textarea v-model="teamForm.notes" class="text-input manager-textarea" placeholder="可选" />
            </label>
            <p v-if="!store.sports.length" class="manager-help">当前还没有项目，请先新增项目，再新增队伍。</p>
            <div class="manager-form-actions">
              <button class="primary-btn" type="submit" :disabled="teamSubmitting || !canSubmitTeam || !store.sports.length">
                {{ teamSubmitting ? '保存中...' : '新增队伍' }}
              </button>
            </div>
          </form>
        </div>
      </section>
    </div>
  </teleport>
</template>

<style scoped>
.split-view {
  display: grid;
  grid-template-columns: minmax(380px, 480px) 1fr;
  gap: 18px;
  align-items: start;
}

.list-panel,
.form-panel {
  display: grid;
  gap: 12px;
  align-content: start;
  min-height: 0;
}

.list-panel {
  grid-template-rows: auto auto minmax(0, 1fr);
  max-height: calc(100vh - 140px);
  overflow: hidden;
}

.list-scroll,
.form-panel {
  min-height: 0;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.list-scroll {
  display: grid;
  gap: 12px;
  padding-right: 8px;
  align-content: start;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.toolbar-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-summary {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

.row-card {
  background: var(--panel-soft);
  border-radius: 16px;
  padding: 16px 18px;
  text-align: left;
  display: grid;
  grid-template-rows: auto auto auto;
  gap: 8px;
  min-height: 108px;
  width: 100%;
  justify-items: start;
}

.row-card.active {
  background: #d1fae5;
}

.empty-state {
  border: 1px dashed var(--line);
  border-radius: 14px;
  padding: 20px 16px;
  color: var(--muted);
  text-align: center;
  background: rgba(255, 255, 255, 0.65);
}

.two-col {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.area {
  min-height: 92px;
  resize: vertical;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.ghost-btn {
  min-height: 44px;
  border-radius: 14px;
  padding: 0 14px;
  background: #f8fafc;
  font-weight: 600;
}

.danger-btn {
  border: 1px solid rgba(185, 28, 28, 0.18);
  background: #fef2f2;
  color: #b91c1c;
}

.manager-overlay {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.44);
}

.manager-dialog {
  width: min(860px, 100%);
  max-height: calc(100vh - 48px);
  display: grid;
  gap: 18px;
  overflow: hidden;
}

.manager-dialog-head,
.manager-block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.manager-dialog-head h3,
.manager-block-head strong,
.manager-row-copy strong,
.manager-row-notes,
.manager-help,
.manager-error {
  margin: 0;
}

.manager-block-head {
  color: var(--muted);
  font-size: 13px;
}

.manager-dialog-body {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(280px, 0.85fr);
  gap: 18px;
  min-height: 0;
}

.manager-list-block,
.manager-form-block {
  min-height: 0;
  display: grid;
  gap: 12px;
  align-content: start;
}

.manager-list {
  display: grid;
  gap: 12px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 6px;
}

.manager-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 14px 16px;
  background: rgba(255, 255, 255, 0.72);
}

.manager-row-copy {
  display: grid;
  gap: 6px;
}

.manager-row-meta,
.manager-row-notes,
.manager-help {
  color: var(--muted);
  font-size: 13px;
}

.manager-textarea {
  min-height: 84px;
  resize: vertical;
}

.manager-form-actions {
  display: flex;
  justify-content: flex-end;
}

.manager-empty {
  min-height: 120px;
}

.manager-error {
  border-radius: 12px;
  border: 1px solid rgba(185, 28, 28, 0.16);
  background: #fef2f2;
  color: #b91c1c;
  padding: 10px 12px;
}

@media (max-width: 1100px) {
  .split-view,
  .two-col,
  .metrics-grid,
  .manager-dialog-body {
    grid-template-columns: 1fr;
  }

  .list-panel {
    max-height: none;
  }
}

@media (max-width: 720px) {
  .toolbar,
  .manager-dialog-head,
  .manager-row {
    align-items: stretch;
  }

  .toolbar,
  .toolbar-actions,
  .manager-dialog-head,
  .manager-block-head,
  .manager-row,
  .form-actions {
    flex-direction: column;
  }

  .manager-overlay {
    padding: 16px;
    align-items: flex-end;
  }

  .manager-dialog {
    max-height: calc(100vh - 24px);
  }
}
</style>
