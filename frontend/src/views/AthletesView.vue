<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { createAthlete, updateAthlete } from '@/api/athletes'
import AppShell from '@/components/layout/AppShell.vue'
import { useAthletesStore } from '@/stores/athletes'

const store = useAthletesStore()
const selectedId = ref<number | null>(null)
const form = reactive({
  full_name: '',
  sport_id: null as number | null,
  team_id: null as number | null,
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

function selectAthlete(athlete: any) {
  selectedId.value = athlete.id
  Object.assign(form, {
    full_name: athlete.full_name || '',
    sport_id: athlete.sport_id ?? null,
    team_id: athlete.team_id ?? null,
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
</script>

<template>
  <AppShell>
    <div class="split-view">
      <div class="panel list-panel">
        <div class="toolbar">
          <h3>运动员列表</h3>
          <button class="primary-btn slim" @click="resetForm">新建</button>
        </div>
        <div class="list-scroll">
          <button
            v-for="athlete in store.athletes"
            :key="athlete.id"
            class="row-card adaptive-card"
            :class="{ active: athlete.id === selectedId }"
            @click="selectAthlete(athlete)"
          >
            <strong class="adaptive-card-title">{{ athlete.full_name }}</strong>
            <span class="adaptive-card-subtitle adaptive-card-clamp-2">
              {{ athlete.team?.name || '未分队' }}
            </span>
            <small v-if="athlete.weight || athlete.height" class="adaptive-card-meta adaptive-card-clamp-1">
              {{ athlete.weight ? `${athlete.weight} kg` : '--' }} / {{ athlete.height ? `${athlete.height} cm` : '--' }}
            </small>
          </button>
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
  grid-template-columns: minmax(360px, 430px) 1fr;
  gap: 18px;
  height: 100%;
  min-height: 0;
}

.list-panel,
.form-panel {
  display: grid;
  gap: 12px;
  align-content: start;
  min-height: 0;
}

.list-panel {
  grid-template-rows: auto minmax(0, 1fr);
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
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.row-card {
  background: var(--panel-soft);
  border-radius: 16px;
  padding: 16px 18px;
  text-align: left;
  display: grid;
  grid-template-rows: auto auto auto;
  gap: 8px;
  min-height: 118px;
  width: 100%;
  justify-items: start;
}

.row-card.active {
  background: #d1fae5;
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

  .split-view {
    height: auto;
  }
}
</style>
