<script setup lang="ts">
import AuthUserBar from '@/components/layout/AuthUserBar.vue'
import AppModeSwitch from '@/components/layout/AppModeSwitch.vue'
import AppCopyrightFooter from '@/components/common/AppCopyrightFooter.vue'
import { getAppModeDisplayLabel } from '@/constants/appModeLabels'

const monitorModeLabel = getAppModeDisplayLabel('monitor')
</script>

<template>
  <div class="monitor-shell">
    <header class="monitor-topbar">
      <div class="monitor-copy">
        <p class="monitor-eyebrow">{{ monitorModeLabel }}</p>
        <h1>训练现场监控</h1>
        <p class="monitor-hint">今日训练状态看板，优先显示同步异常、进行中和未开始队员。</p>
      </div>

      <div class="monitor-filters">
        <slot name="header-filters" />
      </div>

      <div class="monitor-actions">
        <slot name="header-actions" />
        <AuthUserBar />
        <AppModeSwitch />
      </div>
    </header>

    <main class="monitor-body">
      <slot />
    </main>

    <AppCopyrightFooter />
  </div>
</template>

<style scoped>
.monitor-shell {
  --training-filter-width: 160px;
  --training-filter-width-triple: 146px;
  --training-filter-height: 34px;
  --training-filter-padding-inline: 12px;
  --training-filter-font-size: 14px;
  --training-filter-gap: 8px;
  min-height: 100vh;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 18px;
  padding: 18px;
  background:
    radial-gradient(circle at top left, rgba(14, 116, 144, 0.16), transparent 34%),
    linear-gradient(180deg, #f6fbff, #eef6fb 52%, #f8fafc);
}

.monitor-topbar {
  display: grid;
  grid-template-columns: minmax(240px, auto) minmax(320px, 1fr) auto;
  align-items: center;
  gap: 16px;
  padding: 14px 16px;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: var(--shadow);
}

.monitor-copy,
.monitor-filters,
.monitor-actions {
  min-width: 0;
}

.monitor-filters {
  display: flex;
  justify-content: flex-end;
  align-items: center;
}

.monitor-filters :deep(.training-header-filters) {
  justify-content: flex-end;
  overflow: visible;
}

.monitor-copy {
  display: grid;
  gap: 6px;
}

.monitor-eyebrow,
.monitor-hint {
  margin: 0;
  color: var(--text-soft);
}

.monitor-copy h1 {
  margin: 0;
  font-size: clamp(1.5rem, 2vw, 2rem);
  line-height: 1.05;
}

.monitor-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.monitor-body {
  min-width: 0;
  min-height: 0;
  display: grid;
}

@media (max-width: 1180px) {
  .monitor-shell {
    --training-filter-width: 155px;
    --training-filter-width-triple: 138px;
    --training-filter-height: 32px;
    --training-filter-padding-inline: 10px;
    padding: 14px;
    gap: 14px;
  }

  .monitor-topbar {
    grid-template-columns: 1fr;
    align-items: stretch;
  }

  .monitor-actions {
    justify-content: flex-start;
  }

  .monitor-filters {
    justify-content: flex-start;
  }

  .monitor-filters :deep(.training-header-filters) {
    justify-content: flex-start;
  }
}
</style>
