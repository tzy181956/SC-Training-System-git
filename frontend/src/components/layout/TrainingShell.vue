<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const switchLabel = computed(() => (authStore.isTrainingMode ? '切换到管理模式' : '切换到训练模式'))

function switchMode() {
  const nextMode = authStore.isTrainingMode ? 'management' : 'training'
  authStore.setMode(nextMode)
  router.push(nextMode === 'management' ? { name: 'dashboard' } : { name: 'training-mode' })
}
</script>

<template>
  <div class="training-shell">
    <header class="training-header">
      <div>
        <p class="eyebrow">训练模式</p>
        <h1>训练模式</h1>
      </div>
      <div class="actions">
        <div class="user-pill">
          <strong>当前模式</strong>
          <span>训练模式</span>
        </div>
        <button class="ghost-btn" @click="switchMode">{{ switchLabel }}</button>
      </div>
    </header>
    <main class="training-content">
      <div class="training-body">
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
.training-shell {
  height: 100vh;
  height: 100dvh;
  min-height: 100vh;
  background: linear-gradient(180deg, #f8fafc, #eefbf7);
  padding: 18px;
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 18px;
  overflow: hidden;
}

.training-header {
  background: white;
  border-radius: 24px;
  box-shadow: var(--shadow);
  padding: 18px 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-width: 0;
}

.eyebrow,
.user-pill span {
  margin: 0;
  color: var(--muted);
}

.training-header h1 {
  margin: 4px 0 0;
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.user-pill {
  background: var(--panel-soft);
  border-radius: 16px;
  padding: 12px 14px;
  display: grid;
  gap: 4px;
  min-width: 0;
}

.training-content {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.training-body {
  min-height: 0;
  overflow: hidden;
}
</style>
