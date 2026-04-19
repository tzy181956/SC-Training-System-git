<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

onMounted(() => {
  router.replace(authStore.homeRoute)
})
</script>

<template>
  <div class="redirect-page">
    <div class="redirect-card">
      <p class="eyebrow">系统已改为免登录</p>
      <h1>正在进入系统</h1>
      <p class="hint">页面会根据你上次使用的模式自动跳转。</p>
    </div>
  </div>
</template>

<style scoped>
.redirect-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: radial-gradient(circle at top left, #d1fae5, #f8fafc 45%, #e2e8f0);
}

.redirect-card {
  width: min(480px, 100%);
  background: rgba(255, 255, 255, 0.92);
  border-radius: 28px;
  padding: 28px;
  box-shadow: var(--shadow);
  display: grid;
  gap: 12px;
  text-align: center;
}

.eyebrow,
.hint {
  margin: 0;
  color: var(--muted);
}

.redirect-card h1 {
  margin: 0;
}
</style>
