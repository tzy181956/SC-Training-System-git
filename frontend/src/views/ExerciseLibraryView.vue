<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { createExercise, fetchExercises, fetchTags, updateExercise } from '@/api/exercises'
import ExerciseForm from '@/components/exercise/ExerciseForm.vue'
import AppShell from '@/components/layout/AppShell.vue'

const exercises = ref<any[]>([])
const tags = ref<any[]>([])
const selected = ref<any | null>(null)

async function hydrate() {
  ;[exercises.value, tags.value] = await Promise.all([fetchExercises(), fetchTags()])
  if (!selected.value && exercises.value[0]) selected.value = exercises.value[0]
}

async function handleSubmit(payload: Record<string, unknown>) {
  if (selected.value?.id) {
    await updateExercise(selected.value.id, payload)
  } else {
    await createExercise(payload)
  }
  selected.value = null
  await hydrate()
}

onMounted(hydrate)
</script>

<template>
  <AppShell>
    <div class="split-view">
      <div class="panel list-panel">
        <div class="toolbar">
          <h3>动作库</h3>
          <button class="primary-btn slim" @click="selected = null">新建</button>
        </div>
        <div class="list-scroll">
          <button
            v-for="exercise in exercises"
            :key="exercise.id"
            class="row-card adaptive-card"
            :class="{ active: selected?.id === exercise.id }"
            @click="selected = exercise"
          >
            <strong class="adaptive-card-title">{{ exercise.name }}</strong>
            <span class="adaptive-card-subtitle adaptive-card-clamp-2">{{ exercise.alias || exercise.load_profile }}</span>
          </button>
        </div>
      </div>
      <ExerciseForm class="form-panel" :model-value="selected" :tags="tags" @submit="handleSubmit" />
    </div>
  </AppShell>
</template>

<style scoped>
.split-view {
  display: grid;
  grid-template-columns: minmax(360px, 420px) 1fr;
  gap: 18px;
  height: 100%;
  min-height: 0;
}

.list-panel {
  display: grid;
  gap: 12px;
  grid-template-rows: auto minmax(0, 1fr);
  min-height: 0;
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
  justify-content: space-between;
  align-items: center;
}

.row-card {
  background: var(--panel-soft);
  border-radius: 16px;
  padding: 16px 18px;
  text-align: left;
  display: grid;
  gap: 8px;
  min-height: 84px;
  width: 100%;
  justify-items: start;
}

.row-card.active {
  background: #d1fae5;
}

@media (max-width: 1100px) {
  .split-view {
    grid-template-columns: 1fr;
    height: auto;
  }
}
</style>
