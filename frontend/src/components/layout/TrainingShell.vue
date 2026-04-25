<script setup lang="ts">
import { computed, onMounted, ref, useSlots } from 'vue'
import { useRouter } from 'vue-router'

import { fetchRuntimeAccessInfo, type RuntimeAccessInfo } from '@/api/runtimeAccess'
import RuntimeAccessCard from '@/components/layout/RuntimeAccessCard.vue'
import TrainingViewportDebug from '@/components/layout/TrainingViewportDebug.vue'
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
    <header class="training-header">
      <div class="header-copy">
        <h1>训练模式</h1>
      </div>

      <div class="header-middle" :class="{ 'header-middle--empty': !hasHeaderFilters }">
        <div v-if="hasHeaderFilters" class="header-filters">
          <slot name="header-filters" />
        </div>
      </div>

      <div class="actions">
        <RuntimeAccessCard :info="runtimeAccess" />
        <span class="mode-pill">{{ modeLabel }}</span>
        <button class="primary-btn switch-btn" type="button" @click="switchMode">{{ switchLabel }}</button>
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
  padding: 14px;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: 12px;
  overflow: hidden;
}

.training-header {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  min-width: 0;
  min-height: 76px;
  padding: 10px 16px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: var(--shadow);
}

.header-copy,
.header-middle,
.header-filters {
  min-width: 0;
}

.header-copy h1 {
  margin: 0;
  font-size: 1.8rem;
  line-height: 1.02;
}

.header-middle {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  min-height: 0;
}

.header-middle--empty {
  justify-content: flex-end;
}

.header-filters {
  display: flex;
  align-items: center;
  min-width: 0;
}

.actions {
  display: inline-flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  min-width: 0;
  justify-self: end;
}

.mode-pill {
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  padding: 0 12px;
  border-radius: 999px;
  background: var(--panel-soft);
  color: var(--text);
  font-size: 0.92rem;
  font-weight: 700;
  white-space: nowrap;
}

.switch-btn {
  min-height: 40px;
  padding: 0 16px;
  font-size: 0.94rem;
  font-weight: 700;
  white-space: nowrap;
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
  .training-shell {
    padding: 12px;
    gap: 10px;
  }

  .training-header {
    min-height: 72px;
    padding: 8px 12px;
    gap: 10px;
    border-radius: 18px;
  }

  .header-copy h1 {
    font-size: 1.45rem;
  }

  .actions {
    gap: 6px;
  }

  .mode-pill {
    min-height: 38px;
    padding: 0 10px;
    font-size: 0.84rem;
  }

  .switch-btn {
    min-height: 38px;
    padding: 0 12px;
    font-size: 0.84rem;
  }
}

@media (max-width: 767px) {
  .training-shell {
    padding: 12px;
    gap: 12px;
  }

  .training-header {
    grid-template-columns: 1fr;
    align-items: stretch;
    gap: 10px;
    min-height: auto;
    padding: 12px 14px;
  }

  .header-copy h1 {
    font-size: 1.6rem;
  }

  .header-middle,
  .actions {
    justify-self: stretch;
  }

  .header-filters,
  .actions {
    flex-wrap: wrap;
  }

  .actions {
    justify-content: space-between;
  }
}
</style>
