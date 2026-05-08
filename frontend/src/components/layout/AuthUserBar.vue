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

async function handleLogout() {
  authStore.logout()
  await router.replace({ name: 'login' })
}
</script>

<template>
  <div v-if="authStore.currentUser" class="auth-user-bar" :class="`auth-user-bar--${props.variant}`">
    <div class="user-copy">
      <strong>{{ authStore.currentUser.display_name }}</strong>
      <span>{{ roleLabel }}</span>
      <small v-if="authStore.currentUser.sport_name">{{ authStore.currentUser.sport_name }}</small>
    </div>
    <button class="ghost-btn slim logout-btn" type="button" @click="handleLogout">退出登录</button>
  </div>
</template>

<style scoped>
.auth-user-bar {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  max-width: 100%;
  padding: 8px 12px;
  border-radius: 16px;
}

.auth-user-bar--light {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.28);
}

.auth-user-bar--dark {
  background: rgba(255, 255, 255, 0.1);
}

.user-copy {
  display: grid;
  gap: 2px;
  min-width: 0;
  flex: 1 1 auto;
}

.user-copy strong,
.user-copy span,
.user-copy small {
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.auth-user-bar--light .user-copy span,
.auth-user-bar--light .user-copy small {
  color: var(--text-soft);
}

.auth-user-bar--dark .user-copy span,
.auth-user-bar--dark .user-copy small {
  color: rgba(255, 255, 255, 0.72);
}

.logout-btn {
  flex: 0 0 auto;
  white-space: nowrap;
}
</style>
