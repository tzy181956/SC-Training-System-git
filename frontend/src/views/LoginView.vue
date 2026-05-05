<script setup lang="ts">
import axios from 'axios'
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const form = reactive({
  username: '',
  password: '',
})

const submitting = ref(false)
const errorMessage = ref('')

function extractErrorMessage(error: unknown) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && detail.trim()) return detail
    if (error.message) return error.message
  }
  return '登录失败，请稍后重试。'
}

async function handleSubmit() {
  if (!form.username.trim() || !form.password) {
    errorMessage.value = '请输入用户名和密码。'
    return
  }

  submitting.value = true
  errorMessage.value = ''

  try {
    await authStore.login(form.username, form.password)
    const redirectTarget = typeof route.query.redirect === 'string' && route.query.redirect.trim()
      ? route.query.redirect
      : null
    await router.replace(redirectTarget || authStore.homeRoute)
  } catch (error) {
    errorMessage.value = extractErrorMessage(error)
    form.password = ''
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <section class="login-card">
      <div class="hero-copy">
        <p class="eyebrow">训练现场稳定优先</p>
        <h1>体能训练管理平台</h1>
        <p class="hint">请输入管理员、教练或训练端账号登录。系统不开放自助注册。</p>
      </div>

      <form class="login-form" @submit.prevent="handleSubmit">
        <label class="field">
          <span class="field-label">用户名</span>
          <input
            v-model="form.username"
            class="text-input"
            type="text"
            autocomplete="username"
            placeholder="请输入用户名"
          />
        </label>

        <label class="field">
          <span class="field-label">密码</span>
          <input
            v-model="form.password"
            class="text-input"
            type="password"
            autocomplete="current-password"
            placeholder="请输入密码"
          />
        </label>

        <p v-if="errorMessage" class="error-message">{{ errorMessage }}</p>

        <button class="primary-btn submit-btn" type="submit" :disabled="submitting">
          {{ submitting ? '登录中...' : '登录系统' }}
        </button>
      </form>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background:
    radial-gradient(circle at top left, rgba(20, 184, 166, 0.22), transparent 30%),
    linear-gradient(180deg, #f8fafc, #e6f4ef 52%, #eef2ff);
}

.login-card {
  width: min(460px, 100%);
  padding: 32px;
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.95);
  box-shadow: var(--shadow);
  display: grid;
  gap: 24px;
}

.hero-copy,
.login-form,
.field {
  display: grid;
  gap: 10px;
}

.eyebrow,
.hint,
.field-label {
  margin: 0;
  color: var(--text-soft);
}

.hero-copy h1 {
  margin: 0;
  font-size: clamp(2rem, 4vw, 2.4rem);
  line-height: 1.05;
}

.error-message {
  margin: 0;
  padding: 10px 12px;
  border-radius: 14px;
  background: #fee2e2;
  color: #b91c1c;
  font-weight: 600;
}

.submit-btn {
  min-height: 52px;
}
</style>
