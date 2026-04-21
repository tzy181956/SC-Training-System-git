<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { createAthlete, updateAthlete } from '@/api/athletes'
import AppShell from '@/components/layout/AppShell.vue'
import { useAthletesStore } from '@/stores/athletes'

const store = useAthletesStore()
const selectedId = ref<number | null>(null)

const filters = reactive({
  keyword: '',
  sportId: '',
  teamId: '',
  gender: '',
})

const form = reactive({
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

onMounted(async () => {
  await store.hydrate()
  if (store.athletes[0]) selectAthlete(store.athletes[0])
})

const selectedAthlete = computed(() => store.athletes.find((item) => item.id === selectedId.value) || null)

const filteredTeams = computed(() => {
  if (!filters.sportId) return store.teams
  return store.teams.filter((team) => String(team.sport_id) === filters.sportId)
})

const filteredAthletes = computed(() =>
  store.athletes.filter((athlete) => {
    const keyword = filters.keyword.trim().toLowerCase()
    if (keyword) {
      const targets = [athlete.full_name, athlete.sport?.name, athlete.team?.name, athlete.gender]
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

function selectAthlete(athlete: any) {
  selectedId.value = athlete.id
  Object.assign(form, {
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
  if (selectedId.value) {
    await updateAthlete(selectedId.value, form)
  } else {
    await createAthlete(form)
  }

  await store.hydrate()
  if (selectedId.value) {
    const refreshed = store.athletes.find((item) => item.id === selectedId.value)
    if (refreshed) selectAthlete(refreshed)
  }
}

function resetForm() {
  selectedId.value = null
  Object.assign(form, {
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
</script>

<template>
  <AppShell>
    <div class="split-view">
      <div class="panel list-panel">
        <div class="toolbar">
          <h3>运动员列表</h3>
          <button class="primary-btn slim" @click="resetForm">新建</button>
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
            @click="selectAthlete(athlete)"
          >
            <strong class="adaptive-card-title">{{ athlete.full_name }}</strong>
            <span class="adaptive-card-subtitle adaptive-card-clamp-2">
              {{ athlete.sport?.name || '未分项目' }} / {{ athlete.team?.name || '未分队伍' }}
            </span>
            <small class="adaptive-card-meta adaptive-card-clamp-1">
              {{ athlete.gender || '未填写性别' }}
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

        <div class="two-col">
          <label class="field">
            <span class="field-label">所属项目</span>
            <select v-model="form.sport_id" class="text-input">
              <option :value="null">未选择</option>
              <option v-for="sport in store.sports" :key="sport.id" :value="sport.id">{{ sport.name }}</option>
            </select>
          </label>
          <label class="field">
            <span class="field-label">所属队伍</span>
            <select v-model="form.team_id" class="text-input">
              <option :value="null">未选择</option>
              <option v-for="team in store.teams" :key="team.id" :value="team.id">{{ team.name }}</option>
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

        <button class="primary-btn" @click="saveAthlete">保存运动员</button>
      </div>
    </div>
  </AppShell>
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

@media (max-width: 1100px) {
  .split-view,
  .two-col,
  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .list-panel {
    max-height: none;
  }
}
</style>
