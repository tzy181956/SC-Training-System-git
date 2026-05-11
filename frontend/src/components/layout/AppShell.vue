<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

import AuthUserBar from '@/components/layout/AuthUserBar.vue'
import AppModeSwitch from '@/components/layout/AppModeSwitch.vue'
import { getAppModeDisplayLabel } from '@/constants/appModeLabels'
import { useAuthStore } from '@/stores/auth'
import type { UserRoleCode } from '@/types/auth'

const route = useRoute()
const authStore = useAuthStore()

const allLinks: Array<{ name: string; label: string; roles: UserRoleCode[] }> = [
  { name: 'dashboard', label: '总览', roles: ['admin', 'coach'] },
  { name: 'athletes', label: '运动员', roles: ['admin', 'coach'] },
  { name: 'exercises', label: '动作库', roles: ['admin', 'coach'] },
  { name: 'plans', label: '训练模板', roles: ['admin', 'coach'] },
  { name: 'assignments', label: '计划分配', roles: ['admin', 'coach'] },
  { name: 'training-reports', label: '训练数据', roles: ['admin', 'coach'] },
  { name: 'tests', label: '测试数据', roles: ['admin', 'coach'] },
  { name: 'users', label: '账号管理', roles: ['admin'] },
  { name: 'backups', label: '备份恢复', roles: ['admin'] },
  { name: 'logs', label: '日志', roles: ['admin'] },
]

const links = computed(() => {
  if (!authStore.roleCode) return []
  return allLinks.filter((link) => link.roles.includes(authStore.roleCode as UserRoleCode))
})

const currentLabel = computed(() => {
  if (route.name === 'dashboard') return '今日管理工作台'
  return links.value.find((link) => link.name === route.name)?.label || getAppModeDisplayLabel('management')
})

const managementModeLabel = getAppModeDisplayLabel('management')
</script>

<template>
  <div class="shell">
    <aside class="shell-nav">
      <div class="shell-nav-inner">
        <div>
          <p class="eyebrow">{{ managementModeLabel }}</p>
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
            <p>{{ managementModeLabel }}</p>
          </div>
          <AuthUserBar variant="dark" />
        </div>
      </div>
    </aside>

    <main class="shell-main">
      <header class="shell-header">
        <div>
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
  align-items: stretch;
}

.shell-nav {
  background: linear-gradient(180deg, #0f172a, #153b35);
  color: white;
  min-height: 100%;
}

.shell-nav-inner {
  position: sticky;
  top: 0;
  min-height: 100vh;
  max-height: 100vh;
  overflow-y: auto;
  scrollbar-gutter: stable;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 24px;
  box-sizing: border-box;
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
    min-height: auto;
  }

  .shell-nav-inner {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    min-height: auto;
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
