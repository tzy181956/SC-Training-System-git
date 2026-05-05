<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { fetchTeams, type TeamRead } from '@/api/athletes'
import {
  activateUser,
  createUser,
  deactivateUser,
  fetchUsers,
  resetUserPassword,
  updateUser,
  type UserCreatePayload,
  type UserManagementRead,
} from '@/api/users'
import AppShell from '@/components/layout/AppShell.vue'
import { getUserRoleLabel } from '@/constants/userRoles'
import { useAuthStore } from '@/stores/auth'
import type { UserRoleCode } from '@/types/auth'

const authStore = useAuthStore()

const loading = ref(false)
const saving = ref(false)
const resettingPassword = ref(false)
const updatingStatus = ref(false)
const loadError = ref('')
const notice = ref('')

const users = ref<UserManagementRead[]>([])
const teams = ref<TeamRead[]>([])
const selectedUserId = ref<number | null>(null)
const formMode = ref<'create' | 'edit'>('create')

const form = reactive({
  username: '',
  display_name: '',
  role_code: 'training' as UserRoleCode,
  team_id: null as number | null,
  password: '',
  confirm_password: '',
})

const passwordResetForm = reactive({
  password: '',
  confirm_password: '',
})

const roleOptions: Array<{ value: UserRoleCode; label: string }> = [
  { value: 'admin', label: '系统管理员' },
  { value: 'coach', label: '教练账号' },
  { value: 'training', label: '队伍训练端账号' },
]

const selectedUser = computed(() => users.value.find((user) => user.id === selectedUserId.value) || null)
const requiresTeamBinding = computed(() => form.role_code !== 'admin')
const editingSelf = computed(() => selectedUser.value?.id === authStore.currentUser?.id)
const selectedUserStatusLabel = computed(() => (selectedUser.value?.is_active ? '启用中' : '已停用'))

function formatDateTime(value: string | null | undefined) {
  if (!value) return '—'
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return value
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed)
}

function extractErrorMessage(error: unknown, fallback = '操作失败，请稍后重试。') {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    if (Array.isArray(detail) && detail.length) return detail.join('；')
    if (error.message) return error.message
  }
  return fallback
}

function resetPasswordInputs() {
  passwordResetForm.password = ''
  passwordResetForm.confirm_password = ''
}

function resetCreateForm() {
  formMode.value = 'create'
  selectedUserId.value = null
  notice.value = ''
  Object.assign(form, {
    username: '',
    display_name: '',
    role_code: 'training',
    team_id: null,
    password: '',
    confirm_password: '',
  })
  resetPasswordInputs()
}

function editUser(user: UserManagementRead) {
  formMode.value = 'edit'
  selectedUserId.value = user.id
  notice.value = ''
  Object.assign(form, {
    username: user.username,
    display_name: user.display_name,
    role_code: user.role_code,
    team_id: user.team_id,
    password: '',
    confirm_password: '',
  })
  resetPasswordInputs()
}

watch(
  () => form.role_code,
  (roleCode) => {
    if (roleCode === 'admin') {
      form.team_id = null
    }
  },
)

async function hydrate(preferredUserId?: number | null) {
  loading.value = true
  loadError.value = ''

  try {
    const [userList, teamList] = await Promise.all([fetchUsers(), fetchTeams()])
    users.value = userList
    teams.value = teamList

    if (preferredUserId && users.value.some((user) => user.id === preferredUserId)) {
      const nextUser = users.value.find((user) => user.id === preferredUserId)
      if (nextUser) {
        editUser(nextUser)
        return
      }
    }

    if (formMode.value === 'edit' && selectedUserId.value) {
      const nextUser = users.value.find((user) => user.id === selectedUserId.value)
      if (nextUser) {
        editUser(nextUser)
        return
      }
    }

    resetCreateForm()
  } catch (error) {
    loadError.value = extractErrorMessage(error, '加载账号列表失败。')
  } finally {
    loading.value = false
  }
}

function validatePassword(password: string, confirmation: string) {
  if (password.length < 8) {
    return '密码至少需要 8 位。'
  }
  if (password !== confirmation) {
    return '两次输入的密码不一致。'
  }
  return ''
}

async function submitForm() {
  notice.value = ''

  if (!form.display_name.trim()) {
    loadError.value = '显示名称不能为空。'
    return
  }

  if (!form.username.trim() && formMode.value === 'create') {
    loadError.value = '用户名不能为空。'
    return
  }

  if (requiresTeamBinding.value && form.team_id == null) {
    loadError.value = '教练账号和训练端账号必须绑定队伍。'
    return
  }

  if (formMode.value === 'create') {
    const passwordError = validatePassword(form.password, form.confirm_password)
    if (passwordError) {
      loadError.value = passwordError
      return
    }
  }

  saving.value = true
  loadError.value = ''

  try {
    if (formMode.value === 'create') {
      const payload: UserCreatePayload = {
        username: form.username.trim(),
        display_name: form.display_name.trim(),
        role_code: form.role_code,
        team_id: requiresTeamBinding.value ? form.team_id : null,
        is_active: true,
        password: form.password,
      }
      const created = await createUser(payload)
      notice.value = `账号 ${created.display_name} 已创建。`
      await hydrate(created.id)
      return
    }

    if (!selectedUser.value) return

    const updated = await updateUser(selectedUser.value.id, {
      display_name: form.display_name.trim(),
      role_code: form.role_code,
      team_id: requiresTeamBinding.value ? form.team_id : null,
    })
    notice.value = `账号 ${updated.display_name} 已更新。`
    await hydrate(updated.id)
  } catch (error) {
    loadError.value = extractErrorMessage(error, '保存账号失败。')
  } finally {
    saving.value = false
  }
}

async function handleDeactivate() {
  if (!selectedUser.value || !selectedUser.value.is_active) return

  const confirmed = window.confirm(`确认停用账号“${selectedUser.value.display_name}”吗？停用后该账号将无法登录。`)
  if (!confirmed) return

  updatingStatus.value = true
  loadError.value = ''

  try {
    const updated = await deactivateUser(selectedUser.value.id)
    notice.value = `账号 ${updated.display_name} 已停用。`
    await hydrate(updated.id)
  } catch (error) {
    loadError.value = extractErrorMessage(error, '停用账号失败。')
  } finally {
    updatingStatus.value = false
  }
}

async function handleActivate() {
  if (!selectedUser.value || selectedUser.value.is_active) return

  updatingStatus.value = true
  loadError.value = ''

  try {
    const updated = await activateUser(selectedUser.value.id)
    notice.value = `账号 ${updated.display_name} 已启用。`
    await hydrate(updated.id)
  } catch (error) {
    loadError.value = extractErrorMessage(error, '启用账号失败。')
  } finally {
    updatingStatus.value = false
  }
}

async function submitPasswordReset() {
  if (!selectedUser.value) return

  const passwordError = validatePassword(passwordResetForm.password, passwordResetForm.confirm_password)
  if (passwordError) {
    loadError.value = passwordError
    return
  }

  resettingPassword.value = true
  loadError.value = ''

  try {
    const updated = await resetUserPassword(selectedUser.value.id, { password: passwordResetForm.password })
    notice.value = `账号 ${updated.display_name} 的密码已重置。`
    resetPasswordInputs()
    await hydrate(updated.id)
  } catch (error) {
    loadError.value = extractErrorMessage(error, '重置密码失败。')
  } finally {
    resettingPassword.value = false
  }
}

onMounted(async () => {
  await hydrate()
})
</script>

<template>
  <AppShell>
    <div class="users-layout">
      <section class="panel user-list-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">管理员</p>
            <h3>账号列表</h3>
          </div>
          <button class="primary-btn slim" type="button" @click="resetCreateForm">新建账号</button>
        </div>

        <p v-if="loadError" class="error-banner">{{ loadError }}</p>
        <p v-if="notice" class="notice-banner">{{ notice }}</p>

        <div v-if="loading" class="empty-state">正在加载账号列表...</div>
        <div v-else class="user-list">
          <button
            v-for="user in users"
            :key="user.id"
            class="user-row"
            :class="{ active: user.id === selectedUserId }"
            type="button"
            @click="editUser(user)"
          >
            <div class="user-row-head">
              <strong>{{ user.display_name }}</strong>
              <span class="status-badge" :class="{ inactive: !user.is_active }">{{ user.is_active ? '启用中' : '已停用' }}</span>
            </div>
            <span>{{ user.username }}</span>
            <small>{{ getUserRoleLabel(user.role_code) }} · {{ user.team_name || '未绑定队伍' }}</small>
          </button>
          <div v-if="!users.length" class="empty-state">当前还没有账号。</div>
        </div>
      </section>

      <section class="panel user-form-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">编辑</p>
            <h3>{{ formMode === 'create' ? '新建账号' : '编辑账号' }}</h3>
          </div>
        </div>

        <div class="form-grid">
          <label class="field">
            <span class="field-label">用户名</span>
            <input v-model="form.username" class="text-input" :disabled="formMode === 'edit'" placeholder="登录用户名" />
          </label>

          <label class="field">
            <span class="field-label">显示名称</span>
            <input v-model="form.display_name" class="text-input" placeholder="页面显示名称" />
          </label>

          <div class="grid two">
            <label class="field">
              <span class="field-label">角色</span>
              <select v-model="form.role_code" class="text-input" :disabled="editingSelf">
                <option v-for="option in roleOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
              </select>
            </label>

            <div class="field">
              <span class="field-label">账号状态</span>
              <div class="status-display" :class="{ inactive: selectedUser && !selectedUser.is_active }">
                {{ formMode === 'create' ? '新账号默认启用' : selectedUserStatusLabel }}
              </div>
            </div>
          </div>

          <label v-if="requiresTeamBinding" class="field">
            <span class="field-label">绑定队伍</span>
            <select v-model="form.team_id" class="text-input">
              <option :value="null">请选择队伍</option>
              <option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option>
            </select>
          </label>

          <div v-if="formMode === 'create'" class="grid two">
            <label class="field">
              <span class="field-label">初始密码</span>
              <input v-model="form.password" class="text-input" type="password" autocomplete="new-password" placeholder="至少 8 位" />
            </label>
            <label class="field">
              <span class="field-label">确认密码</span>
              <input v-model="form.confirm_password" class="text-input" type="password" autocomplete="new-password" placeholder="再次输入密码" />
            </label>
          </div>

          <div class="form-actions">
            <button class="ghost-btn" type="button" @click="resetCreateForm">清空</button>
            <button class="primary-btn" type="button" :disabled="saving" @click="submitForm">
              {{ saving ? '保存中...' : formMode === 'create' ? '创建账号' : '保存修改' }}
            </button>
          </div>

          <div v-if="selectedUser" class="account-meta">
            <span>创建时间：{{ formatDateTime(selectedUser.created_at) }}</span>
            <span>最近更新：{{ formatDateTime(selectedUser.updated_at) }}</span>
          </div>

          <div v-if="selectedUser" class="status-actions">
            <button
              v-if="selectedUser.is_active"
              class="ghost-btn danger-btn"
              type="button"
              :disabled="updatingStatus"
              @click="handleDeactivate"
            >
              {{ updatingStatus ? '停用中...' : '停用账号' }}
            </button>
            <button
              v-else
              class="secondary-btn"
              type="button"
              :disabled="updatingStatus"
              @click="handleActivate"
            >
              {{ updatingStatus ? '启用中...' : '启用账号' }}
            </button>
            <p class="helper-copy">停用前会二次确认。当前登录管理员不能停用自己，最后一个启用中的管理员也不能停用。</p>
          </div>
        </div>
      </section>

      <section class="panel password-panel">
        <div class="panel-head">
          <div>
            <p class="eyebrow">密码</p>
            <h3>重置密码</h3>
          </div>
        </div>

        <div v-if="selectedUser" class="form-grid">
          <p class="helper-copy">当前目标：{{ selectedUser.display_name }}（{{ selectedUser.username }}）。系统不会回显旧密码或任何明文密码。</p>

          <div class="grid two">
            <label class="field">
              <span class="field-label">新密码</span>
              <input v-model="passwordResetForm.password" class="text-input" type="password" autocomplete="new-password" placeholder="至少 8 位" />
            </label>
            <label class="field">
              <span class="field-label">确认新密码</span>
              <input v-model="passwordResetForm.confirm_password" class="text-input" type="password" autocomplete="new-password" placeholder="再次输入密码" />
            </label>
          </div>

          <div class="form-actions">
            <button class="primary-btn" type="button" :disabled="resettingPassword" @click="submitPasswordReset">
              {{ resettingPassword ? '重置中...' : '重置密码' }}
            </button>
          </div>
        </div>

        <div v-else class="empty-state">先从左侧选中一个已有账号，再执行密码重置。</div>
      </section>
    </div>
  </AppShell>
</template>

<style scoped>
.users-layout {
  display: grid;
  grid-template-columns: minmax(280px, 360px) minmax(360px, 1fr);
  gap: 18px;
  align-items: start;
}

.user-list-panel,
.user-form-panel,
.password-panel,
.user-list,
.form-grid {
  display: grid;
  gap: 14px;
}

.password-panel {
  grid-column: 1 / -1;
}

.panel-head,
.user-row-head,
.grid.two,
.form-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.user-list {
  align-content: start;
}

.user-row {
  width: 100%;
  text-align: left;
  background: var(--panel-soft);
  border-radius: 18px;
  padding: 16px;
  display: grid;
  gap: 6px;
  border: 1px solid transparent;
}

.user-row.active {
  border-color: rgba(15, 118, 110, 0.2);
  background: #d1fae5;
}

.user-row span,
.user-row small,
.helper-copy,
.eyebrow {
  margin: 0;
  color: var(--text-soft);
}

.status-badge {
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.14);
  color: #166534;
  font-size: 12px;
  font-weight: 700;
}

.status-badge.inactive {
  background: rgba(148, 163, 184, 0.18);
  color: #475569;
}

.field {
  display: grid;
  gap: 8px;
}

.status-display,
.account-meta {
  border-radius: 14px;
  background: var(--panel-soft);
}

.status-display {
  min-height: 46px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  font-weight: 700;
  color: #166534;
}

.status-display.inactive {
  color: #475569;
}

.account-meta,
.status-actions {
  display: grid;
  gap: 10px;
}

.account-meta {
  padding: 12px 14px;
  color: var(--text-soft);
  font-size: 14px;
}

.danger-btn {
  color: #b91c1c;
  border-color: rgba(185, 28, 28, 0.24);
}

.error-banner,
.notice-banner {
  margin: 0;
  padding: 10px 12px;
  border-radius: 14px;
  font-weight: 600;
}

.error-banner {
  background: #fee2e2;
  color: #b91c1c;
}

.notice-banner {
  background: #dcfce7;
  color: #166534;
}

.empty-state {
  color: var(--text-soft);
}

@media (max-width: 1200px) {
  .users-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .grid.two,
  .panel-head,
  .user-row-head,
  .form-actions {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
