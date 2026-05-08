<script setup lang="ts">
import { computed, useSlots } from 'vue'

import AuthUserBar from '@/components/layout/AuthUserBar.vue'
import AppModeSwitch from '@/components/layout/AppModeSwitch.vue'
import '@/components/training/trainingLayout.css'
import { getAppModeDisplayLabel } from '@/constants/appModeLabels'

const slots = useSlots()

const hasHeaderFilters = computed(() => Boolean(slots['header-filters']))
const trainingModeLabel = getAppModeDisplayLabel('training')
</script>

<template>
  <div class="training-shell">
    <header class="training-topbar">
      <div class="topbar-title">
        <div class="header-copy">
          <h1>{{ trainingModeLabel }}</h1>
        </div>
      </div>

      <div class="topbar-filters" :class="{ 'topbar-filters--empty': !hasHeaderFilters }">
        <div v-if="hasHeaderFilters" class="header-filters-slot">
          <slot name="header-filters" />
        </div>
      </div>

      <div class="topbar-actions">
        <AuthUserBar class="topbar-action" />
        <AppModeSwitch class="mode-switcher" />
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
  height: auto;
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
  gap: 8px;
  max-width: 100%;
  min-width: 0;
  flex-wrap: nowrap;
  overflow: visible;
  justify-self: end;
}

.topbar-actions :deep(.auth-user-bar) {
  flex: 0 1 240px;
  min-width: 0;
  max-width: 240px;
}

.topbar-actions :deep(.mode-switch) {
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

  .topbar-actions :deep(.auth-user-bar) {
    flex-basis: 212px;
    max-width: 212px;
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

  .topbar-actions :deep(.auth-user-bar) {
    flex-basis: 192px;
    max-width: 192px;
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
    justify-content: flex-start;
    flex-wrap: wrap;
  }

  .topbar-actions :deep(.auth-user-bar) {
    flex-basis: auto;
    max-width: 100%;
  }

  .topbar-filters {
    overflow: visible;
  }
}
</style>
