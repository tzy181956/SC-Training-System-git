<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  draft: any | null
  open: boolean
  busy?: boolean
}>()

const emit = defineEmits<{
  continueRestore: []
  discardRestore: []
}>()

const modifiedAtLabel = computed(() => {
  if (!props.draft?.last_modified_at) return '未知时间'
  return new Date(props.draft.last_modified_at).toLocaleString('zh-CN')
})

const syncStatusLabel = computed(() => {
  if (props.draft?.sync_status === 'manual_retry_required') return '有未同步数据，需手动处理'
  if (props.draft?.sync_status === 'pending') return '有未同步数据'
  return '未完成草稿'
})
</script>

<template>
  <div v-if="open && draft" class="restore-overlay">
    <section class="restore-dialog panel" role="dialog" aria-modal="true" aria-labelledby="restore-dialog-title">
      <div class="restore-copy">
        <p class="section-title">恢复训练</p>
        <h3 id="restore-dialog-title">检测到本机有未完成训练草稿</h3>
        <div class="restore-meta">
          <span>运动员：{{ draft.athlete_name || `运动员 ${draft.athlete_id}` }}</span>
          <span>计划：{{ draft.template_name || `计划 ${draft.assignment_id}` }}</span>
          <span>日期：{{ draft.session_date }}</span>
          <span>状态：{{ syncStatusLabel }}</span>
          <span>最后保存：{{ modifiedAtLabel }}</span>
        </div>
        <p class="restore-hint">继续会回到原训练课的动作列表；放弃会删除这份本地草稿。</p>
      </div>

      <div class="restore-actions">
        <button class="secondary-btn" type="button" :disabled="busy" @click="emit('discardRestore')">放弃草稿</button>
        <button class="primary-btn" type="button" :disabled="busy" @click="emit('continueRestore')">
          {{ busy ? '正在进入...' : '继续录课' }}
        </button>
      </div>
    </section>
  </div>
</template>

<style scoped>
.restore-overlay {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(15, 23, 42, 0.44);
}

.restore-dialog {
  width: min(560px, 100%);
  display: grid;
  gap: 18px;
}

.restore-copy,
.restore-meta {
  display: grid;
  gap: 10px;
}

.restore-copy h3,
.restore-copy p,
.restore-meta span {
  margin: 0;
}

.restore-meta {
  padding: 14px;
  border-radius: 16px;
  background: var(--panel-soft);
  color: var(--muted);
}

.restore-hint {
  color: var(--muted);
}

.restore-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 720px) {
  .restore-overlay {
    padding: 16px;
    align-items: flex-end;
  }

  .restore-actions {
    flex-direction: column-reverse;
  }
}
</style>
