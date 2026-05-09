<script setup lang="ts">
import { computed } from 'vue'

const FINAL_SESSION_STATUSES = new Set(['completed', 'absent', 'partial_complete'])

const props = defineProps<{
  draft: any | null
  open: boolean
  busy?: boolean
}>()

const emit = defineEmits<{
  continueRestore: []
  discardRestore: []
}>()

function formatDateTime(value: string | null | undefined) {
  if (!value) return '未知时间'
  return new Date(value).toLocaleString('zh-CN')
}

function buildSessionStatusLabel(status: string | null | undefined) {
  if (status === 'completed') return '已完成'
  if (status === 'partial_complete') return '未完全完成'
  if (status === 'absent') return '缺席'
  if (status === 'in_progress') return '进行中'
  if (status === 'not_started') return '未开始'
  return '未结束'
}

const modifiedAtLabel = computed(() => formatDateTime(props.draft?.last_modified_at))
const serverUpdatedAtLabel = computed(() => formatDateTime(props.draft?.last_server_updated_at))

const syncStatusLabel = computed(() => {
  if (props.draft?.sync_status === 'manual_retry_required') return '自动重试已停，需要手动补传'
  if (props.draft?.sync_status === 'pending') return '本地有未同步内容'
  return '本地草稿已同步'
})

const sessionSnapshot = computed(() => props.draft?.session_snapshot || null)
const sessionItems = computed(() => sessionSnapshot.value?.items || [])
const totalItemCount = computed(() => sessionItems.value.length)
const completedItemCount = computed(() => sessionItems.value.filter((item: any) => item.status === 'completed').length)
const sessionStatusLabel = computed(() => buildSessionStatusLabel(sessionSnapshot.value?.status))

const currentItem = computed(() => {
  if (!props.draft?.current_item_id) return null
  return sessionItems.value.find((item: any) => item.id === props.draft.current_item_id) || null
})

const currentItemLabel = computed(() => {
  if (!currentItem.value?.exercise?.name) return '未定位到当前动作'
  const prefix = currentItem.value.display_code ? `${currentItem.value.display_code} ` : ''
  return `${prefix}${currentItem.value.exercise.name}`
})

const pendingOperationSummary = computed(() => {
  const operations = Array.isArray(props.draft?.pending_operations) ? props.draft.pending_operations : []
  return operations.reduce(
    (summary: { total: number; create: number; update: number; complete: number }, operation: any) => {
      summary.total += 1
      if (operation?.operation_type === 'create_set') summary.create += 1
      else if (operation?.operation_type === 'update_set') summary.update += 1
      else if (operation?.operation_type === 'complete_session') summary.complete += 1
      return summary
    },
    { total: 0, create: 0, update: 0, complete: 0 },
  )
})

const differenceHeadline = computed(() => {
  if (pendingOperationSummary.value.total > 0) {
    return `本地草稿比服务器至少多出 ${pendingOperationSummary.value.total} 条待同步操作。`
  }
  if (!FINAL_SESSION_STATUSES.has(sessionSnapshot.value?.status || '')) {
    return '当前草稿没有待同步操作，但这堂课还没有正式结束。'
  }
  return '当前草稿与服务器没有明显待处理差异。'
})

const differenceDetails = computed(() => {
  const details: string[] = []
  if (pendingOperationSummary.value.create > 0) {
    details.push(`新增组记录 ${pendingOperationSummary.value.create} 条`)
  }
  if (pendingOperationSummary.value.update > 0) {
    details.push(`修改组记录 ${pendingOperationSummary.value.update} 条`)
  }
  if (pendingOperationSummary.value.complete > 0) {
    details.push(`待补传结束训练 ${pendingOperationSummary.value.complete} 条`)
  }
  if (!details.length && !FINAL_SESSION_STATUSES.has(sessionSnapshot.value?.status || '')) {
    details.push('草稿主要用于继续未完成课程')
  }
  return details
})

const decisionHint = computed(() => {
  if (pendingOperationSummary.value.total > 0) {
    return '继续录课：保留本地未同步内容并继续补传。放弃草稿：丢掉这些本地修改，只保留服务器当前记录。'
  }
  return '继续录课：从本地停留位置继续。放弃草稿：删除本地恢复点，后续仅按服务器当前状态进入。'
})
</script>

<template>
  <div v-if="open && draft" class="restore-overlay">
    <section class="restore-dialog panel" role="dialog" aria-modal="true" aria-labelledby="restore-dialog-title">
      <div class="restore-copy">
        <p class="section-title">恢复训练</p>
        <h3 id="restore-dialog-title">检测到本机有未结束训练草稿</h3>

        <div class="restore-meta">
          <span>运动员：{{ draft.athlete_name || `运动员 ${draft.athlete_id}` }}</span>
          <span>计划：{{ draft.template_name || `计划 ${draft.assignment_id}` }}</span>
          <span>日期：{{ draft.session_date }}</span>
          <span>同步状态：{{ syncStatusLabel }}</span>
        </div>

        <div class="restore-grid">
          <section class="restore-card">
            <p class="restore-card-title">本地草稿内容</p>
            <div class="restore-card-body">
              <span>已记录 {{ draft.recorded_sets || 0 }} 组</span>
              <span>已完成 {{ completedItemCount }}/{{ totalItemCount || 0 }} 个动作</span>
              <span>课程状态：{{ sessionStatusLabel }}</span>
              <span>当前停在：{{ currentItemLabel }}</span>
              <span>本地最后修改：{{ modifiedAtLabel }}</span>
            </div>
          </section>

          <section class="restore-card restore-card--diff">
            <p class="restore-card-title">与服务器的差异</p>
            <div class="restore-card-body">
              <strong class="difference-headline">{{ differenceHeadline }}</strong>
              <span v-if="draft.last_server_updated_at">服务器最后同步：{{ serverUpdatedAtLabel }}</span>
              <span v-else>服务器最后同步：暂无记录</span>
              <span v-for="detail in differenceDetails" :key="detail">{{ detail }}</span>
            </div>
          </section>
        </div>

        <p class="restore-hint">{{ decisionHint }}</p>
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
  width: min(720px, 100%);
  display: grid;
  gap: 18px;
}

.restore-copy,
.restore-meta,
.restore-grid,
.restore-card,
.restore-card-body {
  display: grid;
  gap: 10px;
}

.restore-copy h3,
.restore-copy p,
.restore-meta span,
.restore-card-body span,
.restore-card-body strong {
  margin: 0;
}

.restore-meta {
  padding: 14px;
  border-radius: 16px;
  background: var(--panel-soft);
  color: var(--muted);
}

.restore-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.restore-card {
  padding: 14px;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: rgba(248, 250, 252, 0.82);
}

.restore-card--diff {
  background: rgba(239, 246, 255, 0.88);
  border-color: rgba(96, 165, 250, 0.2);
}

.restore-card-title {
  margin: 0;
  color: var(--text);
  font-size: 0.95rem;
  font-weight: 800;
}

.restore-card-body {
  color: var(--muted);
  font-size: 0.94rem;
}

.difference-headline {
  color: var(--text);
  font-size: 0.98rem;
  line-height: 1.4;
}

.restore-hint {
  color: var(--muted);
  line-height: 1.6;
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

  .restore-grid {
    grid-template-columns: 1fr;
  }

  .restore-actions {
    flex-direction: column-reverse;
  }
}
</style>
