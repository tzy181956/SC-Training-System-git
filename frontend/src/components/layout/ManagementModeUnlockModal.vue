<script setup lang="ts">
import { computed, ref, watch } from 'vue'

const props = defineProps<{
  open: boolean
  busy?: boolean
  error?: string
  username: string
  displayName?: string | null
}>()

const emit = defineEmits<{
  confirm: [password: string]
  cancel: []
}>()

const password = ref('')

const accountLabel = computed(() => {
  if (props.displayName?.trim()) {
    return `${props.displayName} (${props.username})`
  }
  return props.username
})

watch(
  () => props.open,
  (open) => {
    if (open) {
      password.value = ''
      return
    }
    password.value = ''
  },
  { immediate: true },
)

function submit() {
  if (!password.value || props.busy) return
  emit('confirm', password.value)
}

function cancel() {
  password.value = ''
  emit('cancel')
}
</script>

<template>
  <div v-if="open" class="unlock-overlay" role="presentation">
    <section
      class="unlock-dialog panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="management-unlock-title"
      @click.stop
    >
      <div class="unlock-copy">
        <p class="section-title">管理模式验证</p>
        <h3 id="management-unlock-title">进入管理模式前，请再次输入当前账号密码</h3>
        <p class="unlock-hint">训练模式和实时模式可直接使用，管理模式需要本地二次解锁。</p>
      </div>

      <div class="unlock-fields">
        <label class="field">
          <span class="field-label">当前账号</span>
          <input class="text-input" type="text" :value="accountLabel" readonly />
        </label>

        <label class="field">
          <span class="field-label">当前密码</span>
          <input
            v-model="password"
            class="text-input"
            type="password"
            autocomplete="current-password"
            placeholder="请输入当前账号密码"
            @keyup.enter="submit"
          />
        </label>
      </div>

      <p v-if="error" class="error-message">{{ error }}</p>

      <div class="unlock-actions">
        <button class="secondary-btn" type="button" :disabled="busy" @click="cancel">取消</button>
        <button class="primary-btn" type="button" :disabled="busy || !password" @click="submit">
          {{ busy ? '验证中...' : '确认进入管理模式' }}
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.unlock-overlay {
  position: fixed;
  inset: 0;
  z-index: 90;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.46);
}

.unlock-dialog,
.unlock-copy,
.unlock-fields {
  display: grid;
  gap: 16px;
}

.unlock-dialog {
  width: min(560px, 100%);
}

.unlock-copy h3,
.unlock-copy p {
  margin: 0;
}

.unlock-hint,
.field-label {
  color: var(--text-soft);
}

.unlock-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  flex-wrap: wrap;
}

.error-message {
  margin: 0;
  padding: 10px 12px;
  border-radius: 14px;
  background: #fee2e2;
  color: #b91c1c;
  font-weight: 600;
}

@media (max-width: 720px) {
  .unlock-overlay {
    padding: 16px;
    align-items: flex-end;
  }

  .unlock-actions {
    flex-direction: column-reverse;
  }
}
</style>
