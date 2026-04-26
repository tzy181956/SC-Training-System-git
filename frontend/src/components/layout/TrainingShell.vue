<script setup lang="ts">
import { computed, onMounted, ref, useSlots } from 'vue'
import { useRouter } from 'vue-router'

import { fetchRuntimeAccessInfo, type RuntimeAccessInfo } from '@/api/runtimeAccess'
import RuntimeAccessCard from '@/components/layout/RuntimeAccessCard.vue'
import TrainingViewportDebug from '@/components/layout/TrainingViewportDebug.vue'
import '@/components/training/trainingLayout.css'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const slots = useSlots()
const authStore = useAuthStore()
const isDev = import.meta.env.DEV
const runtimeAccess = ref<RuntimeAccessInfo>({
  accessUrl: new URL('/', window.location.origin).toString(),
  host: window.location.hostname,
  port: Number(window.location.port || (window.location.protocol === 'https:' ? 443 : 80)),
  generatedAt: '',
  source: 'fallback',
})

const hasHeaderFilters = computed(() => !!slots['header-filters'])
const switchLabel = computed(() => (authStore.isTrainingMode ? '切到管理' : '切到训练'))
const modeLabel = computed(() => (authStore.isTrainingMode ? '训练模式' : '管理模式'))

function switchMode() {
  const nextMode = authStore.isTrainingMode ? 'management' : 'training'
  authStore.setMode(nextMode)
  router.push(nextMode === 'management' ? { name: 'dashboard' } : { name: 'training-mode' })
}

onMounted(async () => {
  runtimeAccess.value = await fetchRuntimeAccessInfo()
})
</script>

<template>
  <div class="training-shell">
    <header class="training-topbar">
      <div class="topbar-title">
        <div class="header-copy">
          <h1>训练模式</h1>
        </div>
      </div>

      <div class="topbar-filters" :class="{ 'topbar-filters--empty': !hasHeaderFilters }">
        <div v-if="hasHeaderFilters" class="header-filters-slot">
          <slot name="header-filters" />
        </div>
      </div>

      <div class="topbar-actions">
        <RuntimeAccessCard class="topbar-action secondary-action" :info="runtimeAccess" />
        <span class="mode-pill secondary-action">{{ modeLabel }}</span>
        <button class="primary-btn switch-btn topbar-primary-action" type="button" @click="switchMode">{{ switchLabel }}</button>
      </div>
    </header>

    <main class="training-content">
      <div class="training-body">
        <slot />
      </div>
    </main>

    <TrainingViewportDebug v-if="isDev" />
  </div>
</template>

<style scoped>
.training-shell {
  height: 100vh;
  height: 100dvh;
  min-height: 100vh;
  background: linear-gradient(180deg, #f8fafc, #eefbf7);
  padding: var(--training-shell-padding);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: var(--training-shell-gap);
  overflow: hidden;
}

.training-topbar {
  width: 100%;
  max-width: 100%;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  column-gap: 12px;
  min-width: 0;
  min-height: var(--training-topbar-height);
  height: var(--training-topbar-height);
  padding: 8px 12px;
  border-radius: var(--training-topbar-radius);
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--shadow);
  overflow: visible;
  box-sizing: border-box;
}

.topbar-title,
.topbar-filters,
.topbar-actions,
.header-copy,
.header-filters-slot {
  min-width: 0;
}

.topbar-title {
  display: flex;
  align-items: center;
  flex: none;
}

.header-copy {
  display: flex;
  align-items: center;
  min-height: 100%;
}

.header-copy h1 {
  margin: 0;
  font-size: 1.5rem;
  line-height: 1;
  white-space: nowrap;
}

.topbar-filters {
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}

.topbar-filters--empty {
  display: block;
}

.header-filters-slot {
  width: 100%;
}

.topbar-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  max-width: 100%;
  min-width: 0;
  flex-wrap: nowrap;
  overflow: visible;
  justify-self: end;
}

.mode-pill {
  display: inline-flex;
  align-items: center;
  min-height: 34px;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--panel-soft);
  color: var(--text);
  font-size: 0.82rem;
  font-weight: 700;
  white-space: nowrap;
  flex: 0 0 auto;
}

.switch-btn {
  min-height: 34px;
  padding: 0 10px;
  font-size: 0.82rem;
  font-weight: 700;
  white-space: nowrap;
  flex: 0 0 auto;
}

.training-content {
  display: grid;
  grid-template-rows: minmax(0, 1fr);
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

.training-body {
  display: grid;
  min-width: 0;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

@media (min-width: 768px) and (max-width: 1199px) {
  .training-topbar {
    grid-template-columns: auto minmax(320px, 1fr) auto;
    column-gap: 10px;
    padding: 8px 10px;
  }

  .header-copy h1 {
    font-size: 1.31rem;
  }

  .topbar-actions {
    gap: 6px;
  }

  .mode-pill {
    min-height: 32px;
    max-width: 64px;
    padding: 0 10px;
    font-size: 0.78rem;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .switch-btn {
    min-height: 32px;
    padding: 0 8px;
    font-size: 0.8rem;
  }
}

@media (min-width: 768px) and (max-width: 1120px) {
  .topbar-actions .mode-pill {
    display: none;
  }
}

@media (min-width: 768px) and (max-width: 1050px) {
  .training-topbar {
    grid-template-columns: auto minmax(308px, 1fr) auto;
    column-gap: 8px;
  }

  .topbar-actions {
    gap: 4px;
  }

  .topbar-actions :deep(.access-trigger) {
    max-width: 56px;
    min-height: 32px;
    padding: 0 8px;
    font-size: 0.78rem;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .switch-btn {
    max-width: 58px;
    padding: 0 8px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

@media (min-width: 768px) and (max-width: 1080px) {
  .topbar-actions .secondary-action {
    display: none;
  }

  .training-topbar {
    grid-template-columns: auto minmax(308px, 1fr) auto;
  }
}

@media (max-width: 767px) {
  .training-shell {
    padding: 12px;
    gap: 12px;
  }

  .training-topbar {
    height: auto;
    min-height: auto;
    grid-template-columns: 1fr;
    align-items: stretch;
    gap: 10px;
    padding: 12px 14px;
  }

  .header-copy h1 {
    font-size: 1.6rem;
  }

  .topbar-actions {
    justify-content: space-between;
    flex-wrap: wrap;
  }

  .topbar-filters {
    overflow: visible;
  }
}

</style>
