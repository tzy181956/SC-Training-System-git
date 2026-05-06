<script setup lang="ts">
import axios from 'axios'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import { verifyPassword } from '@/api/auth'
import ManagementModeUnlockModal from '@/components/layout/ManagementModeUnlockModal.vue'
import { getAppModeDisplayLabel } from '@/constants/appModeLabels'
import { resolveRouteForMode, useAuthStore } from '@/stores/auth'
import type { AppMode } from '@/types/auth'

const router = useRouter()
const authStore = useAuthStore()

const unlockDialogOpen = ref(false)
const submitting = ref(false)
const errorMessage = ref('')

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

const currentUsername = computed(() => authStore.currentUser?.username || '')
const currentDisplayName = computed(() => authStore.currentUser?.display_name || '')
const defaultManagementPath = computed(() => router.resolve(resolveRouteForMode('management')).fullPath)

function extractErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    if (error.message) return error.message
  }
  return '密码错误，无法进入管理模式'
}

function requiresManagementPassword(mode: AppMode) {
  if (mode !== 'management') return false
  authStore.refreshManagementUnlock()
  return authStore.isCoach && !authStore.isManagementUnlocked
}

function openUnlockDialog(targetPath: string) {
  authStore.setPendingManagementPath(targetPath)
  errorMessage.value = ''
  unlockDialogOpen.value = true
}

watch(
  () => authStore.pendingManagementPath,
  (pendingPath) => {
    if (!pendingPath || !authStore.isCoach) {
      if (!submitting.value) {
        unlockDialogOpen.value = false
        errorMessage.value = ''
      }
      return
    }

    authStore.refreshManagementUnlock()
    if (authStore.isManagementUnlocked) {
      return
    }

    unlockDialogOpen.value = true
    errorMessage.value = ''
  },
  { immediate: true },
)

async function switchMode(mode: AppMode) {
  if (!authStore.canUseMode(mode) || authStore.currentMode === mode) return

  if (requiresManagementPassword(mode)) {
    openUnlockDialog(defaultManagementPath.value)
    return
  }

  errorMessage.value = ''
  unlockDialogOpen.value = false
  authStore.clearPendingManagementPath()
  authStore.setMode(mode)
  await router.push(resolveRouteForMode(mode))
}

async function handleUnlockConfirm(password: string) {
  if (!authStore.currentUser || submitting.value) return

  submitting.value = true
  errorMessage.value = ''

  try {
    await verifyPassword(password)
    authStore.unlockManagement()
    const targetPath = authStore.consumePendingManagementPath() || defaultManagementPath.value
    unlockDialogOpen.value = false
    authStore.setMode('management')
    await router.push(targetPath)
  } catch (error) {
    errorMessage.value = extractErrorMessage(error)
  } finally {
    submitting.value = false
  }
}

function handleUnlockCancel() {
  if (submitting.value) return
  errorMessage.value = ''
  unlockDialogOpen.value = false
  authStore.clearPendingManagementPath()
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

  <ManagementModeUnlockModal
    :open="unlockDialogOpen"
    :busy="submitting"
    :error="errorMessage"
    :username="currentUsername"
    :display-name="currentDisplayName"
    @confirm="handleUnlockConfirm"
    @cancel="handleUnlockCancel"
  />
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
