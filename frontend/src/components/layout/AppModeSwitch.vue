<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { getAppModeDisplayLabel } from '@/constants/appModeLabels'
import { resolveRouteForMode, useAuthStore } from '@/stores/auth'
import type { AppMode } from '@/types/auth'

const router = useRouter()
const authStore = useAuthStore()

const visibleModes = computed<AppMode[]>(() => (
  authStore.availableModes.length
    ? authStore.availableModes
    : ['training', 'management', 'monitor']
))

const modeButtons = computed(() => (
  visibleModes.value.map((mode) => ({
    mode,
    label: getAppModeDisplayLabel(mode),
  }))
))

async function switchMode(mode: AppMode) {
  if (!authStore.canUseMode(mode) || authStore.currentMode === mode) return
  authStore.setMode(mode)
  await router.push(resolveRouteForMode(mode))
}
</script>

<template>
  <div class="mode-switch" role="tablist" aria-label="模式切换">
    <button
      v-for="button in modeButtons"
      :key="button.mode"
      class="mode-btn"
      :class="{ active: authStore.currentMode === button.mode }"
      :aria-pressed="authStore.currentMode === button.mode"
      type="button"
      @click="switchMode(button.mode)"
    >
      {{ button.label }}
    </button>
  </div>
</template>

<style scoped>
.mode-switch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px;
  border-radius: 999px;
  background: rgba(14, 116, 144, 0.08);
  flex-wrap: nowrap;
  white-space: nowrap;
}

.mode-btn {
  min-height: 36px;
  padding: 0 14px;
  border-radius: 999px;
  border: 0;
  background: transparent;
  color: var(--text-soft);
  font-weight: 700;
  white-space: nowrap;
  transition:
    background-color 0.2s ease,
    color 0.2s ease,
    box-shadow 0.2s ease;
}

.mode-btn.active {
  background: white;
  color: #0f766e;
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.08);
}
</style>
