<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'

import { getUserRoleLabel } from '@/constants/userRoles'
import { useAuthStore } from '@/stores/auth'

const props = withDefaults(defineProps<{
  variant?: 'light' | 'dark'
}>(), {
  variant: 'light',
})

const router = useRouter()
const authStore = useAuthStore()

const roleLabel = computed(() => getUserRoleLabel(authStore.roleCode))
const secondaryIdentity = computed(() => {
  if (!authStore.currentUser) return ''
  if (authStore.currentUser.display_name === authStore.currentUser.username) {
    return authStore.currentUser.username
  }
  return `${authStore.currentUser.username}`
})
const scopeLabel = computed(() => {
  if (!authStore.currentUser) return roleLabel.value
  return authStore.currentUser.sport_name
    ? `${roleLabel.value} · ${authStore.currentUser.sport_name}`
    : roleLabel.value
})

async function handleLogout() {
  authStore.logout()
  await router.replace({ name: 'login' })
}
</script>

<template>
  <div v-if="authStore.currentUser" class="auth-user-bar" :class="`auth-user-bar--${props.variant}`">
    <div class="user-copy">
      <strong>{{ authStore.currentUser.display_name }}</strong>
      <span>{{ secondaryIdentity }}</span>
      <small>{{ scopeLabel }}</small>
    </div>
    <button class="ghost-btn slim logout-btn" type="button" @click="handleLogout">退出登录</button>
  </div>
</template>

<style scoped>
.auth-user-bar {
  display: grid;
  gap: 12px;
  min-width: 0;
  width: 100%;
  padding: 8px 12px;
  border-radius: 16px;
}

.auth-user-bar--light {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.28);
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
}

.auth-user-bar--dark {
  background: rgba(255, 255, 255, 0.1);
  grid-template-columns: 1fr;
}

.user-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.user-copy strong,
.user-copy span,
.user-copy small {
  min-width: 0;
  overflow-wrap: anywhere;
}

.auth-user-bar--light .user-copy span,
.auth-user-bar--light .user-copy small {
  color: var(--text-soft);
}

.auth-user-bar--dark .user-copy span,
.auth-user-bar--dark .user-copy small {
  color: rgba(255, 255, 255, 0.72);
}

.auth-user-bar--dark .user-copy strong,
.auth-user-bar--dark .user-copy span,
.auth-user-bar--dark .user-copy small {
  white-space: normal;
}

.logout-btn {
  white-space: nowrap;
  justify-self: start;
}

.auth-user-bar--light .logout-btn {
  justify-self: end;
}
</style>
