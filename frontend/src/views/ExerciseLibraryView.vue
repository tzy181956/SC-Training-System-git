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
        <button
          v-for="exercise in exercises"
          :key="exercise.id"
          class="row-card"
          :class="{ active: selected?.id === exercise.id }"
          @click="selected = exercise"
        >
          <strong>{{ exercise.name }}</strong>
          <span>{{ exercise.alias || exercise.load_profile }}</span>
        </button>
      </div>
      <ExerciseForm :model-value="selected" :tags="tags" @submit="handleSubmit" />
    </div>
  </AppShell>
</template>

<style scoped>
.split-view {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 18px;
}

.list-panel {
  display: grid;
  gap: 12px;
  align-content: start;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
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
</style>
