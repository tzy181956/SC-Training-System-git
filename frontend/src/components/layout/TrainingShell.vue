<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { fetchRuntimeAccessInfo, type RuntimeAccessInfo } from '@/api/runtimeAccess'
import RuntimeAccessCard from '@/components/layout/RuntimeAccessCard.vue'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const runtimeAccess = ref<RuntimeAccessInfo>({
  accessUrl: new URL('/', window.location.origin).toString(),
  host: window.location.hostname,
  port: Number(window.location.port || (window.location.protocol === 'https:' ? 443 : 80)),
  generatedAt: '',
  source: 'fallback',
})

const switchLabel = computed(() => (authStore.isTrainingMode ? '切换到管理模式' : '切换到训练模式'))
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
        <p class="eyebrow">训练系统</p>
        <h1>训练模式</h1>
      </div>

      <div class="header-middle">
        <div v-if="$slots['header-filters']" class="header-filters">
          <slot name="header-filters" />
        </div>
        <div class="header-access">
          <RuntimeAccessCard :info="runtimeAccess" />
        </div>
      </div>

      <div class="actions">
        <div class="user-pill">
          <strong>当前模式</strong>
          <span>{{ modeLabel }}</span>
        </div>
        <button class="primary-btn switch-btn" type="button" @click="switchMode">{{ switchLabel }}</button>
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
  padding: 14px 18px;
  display: grid;
  grid-template-columns: auto minmax(380px, 1fr) auto;
  align-items: center;
  gap: 18px;
  min-width: 0;
}

.header-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.header-middle {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.header-filters {
  min-width: 0;
}

.header-access {
  width: min(100%, 420px);
  min-width: 320px;
}

.eyebrow,
.user-pill span {
  margin: 0;
  color: var(--muted);
}

.eyebrow {
  font-size: 0.95rem;
  font-weight: 700;
  letter-spacing: 0.04em;
}

.training-header h1 {
  margin: 0;
  font-size: 2rem;
  line-height: 1.05;
}

.actions {
  display: flex;
  align-items: center;
  gap: 12px;
  justify-content: flex-end;
  justify-self: end;
  min-width: max-content;
  flex-wrap: nowrap;
}

.user-pill {
  background: var(--panel-soft);
  border-radius: 16px;
  padding: 10px 14px;
  display: grid;
  gap: 2px;
  min-width: 0;
}

.user-pill strong {
  font-size: 1rem;
  line-height: 1.1;
}

.user-pill span {
  font-size: 1.15rem;
  font-weight: 700;
}

.switch-btn {
  min-height: 48px;
  padding: 0 20px;
  font-size: 1rem;
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

@media (max-width: 1440px) {
  .training-header {
    grid-template-columns: auto minmax(320px, 1fr) auto;
  }

  .header-middle {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 12px;
  }

  .header-filters {
    min-width: 0;
  }

  .header-access {
    width: min(100%, 380px);
    min-width: 280px;
  }
}

@media (max-width: 1180px) {
  .training-header {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .header-middle,
  .actions {
    justify-self: stretch;
  }

  .header-middle {
    grid-template-columns: 1fr;
  }

  .header-filters,
  .header-access {
    min-width: 0;
    width: 100%;
  }

  .actions {
    justify-content: space-between;
    flex-wrap: wrap;
  }
}

@media (max-width: 720px) {
  .training-header {
    padding: 14px;
  }

  .training-header h1 {
    font-size: 1.7rem;
  }

  .header-middle,
  .actions {
    gap: 10px;
  }
}
</style>
