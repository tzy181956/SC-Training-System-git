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
  training_level: '',
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
  Object.assign(form, athlete)
}

async function saveAthlete() {
  if (selectedId.value) {
    await updateAthlete(selectedId.value, form)
  } else {
    await createAthlete(form)
  }
  await store.hydrate()
}

function resetForm() {
  selectedId.value = null
  Object.assign(form, { full_name: '', sport_id: null, team_id: null, position: '', training_level: '', notes: '', is_active: true })
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
        <button
          v-for="athlete in store.athletes"
          :key="athlete.id"
          class="row-card"
          :class="{ active: athlete.id === selectedId }"
          @click="selectAthlete(athlete)"
        >
          <strong>{{ athlete.full_name }}</strong>
          <span>{{ athlete.team?.name || '未分队' }} / {{ athlete.training_level || '未设训练等级' }}</span>
        </button>
      </div>
      <div class="panel form-panel">
        <h3>{{ selectedAthlete ? '编辑运动员' : '新增运动员' }}</h3>
        <input v-model="form.full_name" class="text-input" placeholder="姓名" />
        <div class="two-col">
          <select v-model="form.sport_id" class="text-input">
            <option :value="null">所属项目</option>
            <option v-for="sport in store.sports" :key="sport.id" :value="sport.id">{{ sport.name }}</option>
          </select>
          <select v-model="form.team_id" class="text-input">
            <option :value="null">所属队伍</option>
            <option v-for="team in store.teams" :key="team.id" :value="team.id">{{ team.name }}</option>
          </select>
        </div>
        <div class="two-col">
          <input v-model="form.position" class="text-input" placeholder="位置 / 角色" />
          <input v-model="form.training_level" class="text-input" placeholder="训练等级" />
        </div>
        <textarea v-model="form.notes" class="text-input area" placeholder="备注" />
        <button class="primary-btn" @click="saveAthlete">保存运动员</button>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.split-view {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 18px;
  min-height: 0;
}

.list-panel,
.form-panel {
  display: grid;
  gap: 12px;
  align-content: start;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.row-card {
  background: var(--panel-soft);
  border-radius: 16px;
  padding: 16px;
  text-align: left;
  display: grid;
  gap: 5px;
  min-height: var(--touch);
}

.row-card.active {
  background: #d1fae5;
}

.two-col {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
</style>
