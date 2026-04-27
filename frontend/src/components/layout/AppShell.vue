<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AppModeSwitch from '@/components/layout/AppModeSwitch.vue'

const route = useRoute()

const links = [
  { name: 'dashboard', label: '总览' },
  { name: 'athletes', label: '运动员' },
  { name: 'exercises', label: '动作库' },
  { name: 'plans', label: '训练模板' },
  { name: 'assignments', label: '计划分配' },
  { name: 'training-reports', label: '训练数据' },
  { name: 'backups', label: '备份恢复' },
  { name: 'logs', label: '日志' },
  { name: 'tests', label: '测试数据' },
]

const currentLabel = computed(() => links.find((link) => link.name === route.name)?.label || '管理模式')
</script>

<template>
  <div class="shell">
    <aside class="shell-nav">
      <div>
        <p class="eyebrow">管理模式</p>
        <h1>体能训练管理平台</h1>
      </div>
      <nav class="shell-links">
        <RouterLink
          v-for="link in links"
          :key="link.name"
          :to="{ name: link.name }"
          class="shell-link"
          :class="{ active: route.name === link.name }"
        >
          {{ link.label }}
        </RouterLink>
      </nav>
      <div class="shell-user">
        <div>
          <strong>当前模式</strong>
          <p>管理端</p>
        </div>
      </div>
    </aside>
    <main class="shell-main">
      <header class="shell-header">
        <div>
          <p class="eyebrow shell-header-eyebrow">平板横屏优先</p>
          <h2>{{ currentLabel }}</h2>
        </div>
        <div class="shell-header-actions">
          <slot name="header-actions" />
          <AppModeSwitch />
        </div>
      </header>
      <div class="shell-body">
        <slot />
      </div>
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: var(--nav-width) 1fr;
  min-height: 100vh;
  align-items: start;
}

.shell-nav {
  background: linear-gradient(180deg, #0f172a, #153b35);
  color: white;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  position: sticky;
  top: 0;
  max-height: 100vh;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.shell-links {
  display: grid;
  gap: 10px;
}

.shell-link {
  padding: 16px 18px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.08);
  min-height: var(--touch);
  display: flex;
  align-items: center;
  min-width: 0;
  overflow-wrap: anywhere;
}

.shell-link.active {
  background: rgba(255, 255, 255, 0.2);
}

.shell-user {
  margin-top: auto;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 18px;
  padding: 16px;
  display: grid;
  gap: 12px;
  min-width: 0;
}

.shell-user strong {
  display: block;
}

.shell-user p,
.eyebrow {
  margin: 0;
  color: rgba(255, 255, 255, 0.72);
  font-size: 13px;
  letter-spacing: 0.04em;
}

.shell-main {
  padding: 22px;
  display: grid;
  grid-template-rows: auto auto;
  gap: 18px;
  min-width: 0;
  align-content: start;
}

.shell-body {
  min-height: auto;
  overflow: visible;
}

.shell-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}

.shell-header-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
  min-width: 0;
}

.shell-header-eyebrow {
  color: var(--text-soft);
}

.shell-header h2,
.shell-nav h1 {
  margin: 4px 0 0;
}

@media (max-width: 1100px) {
  .shell {
    grid-template-columns: 1fr;
    height: auto;
    overflow: visible;
  }

  .shell-nav {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    position: static;
    max-height: none;
    overflow: visible;
  }
}

@media (max-width: 767px) {
  .shell-header {
    align-items: stretch;
    flex-direction: column;
  }

  .shell-header-actions {
    justify-content: flex-start;
  }
}
</style>
