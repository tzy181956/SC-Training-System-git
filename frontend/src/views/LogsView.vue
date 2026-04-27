<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { fetchLogs, type LogItem } from '@/api/logs'
import { normalizeActorNameFilter, normalizeModeAliasForDisplay } from '@/constants/appModeLabels'
import AppShell from '@/components/layout/AppShell.vue'
import { todayString } from '@/utils/date'

const loading = ref(false)
const loadError = ref('')
const logs = ref<LogItem[]>([])
const objectTypeOptions = ref<string[]>([])

const filters = reactive({
  dateFrom: getDateBefore(29),
  dateTo: todayString(),
  actorName: '',
  objectType: '',
  limit: 200,
})

async function loadLogs() {
  loading.value = true
  loadError.value = ''
  try {
    const response = await fetchLogs({
      date_from: filters.dateFrom || undefined,
      date_to: filters.dateTo || undefined,
      actor_name: normalizeActorNameFilter(filters.actorName) || undefined,
      object_type: filters.objectType || undefined,
      limit: filters.limit,
    })
    logs.value = response.items || []
    objectTypeOptions.value = response.available_object_types || []
  } catch (error: any) {
    logs.value = []
    objectTypeOptions.value = []
    loadError.value = error?.response?.data?.detail || '日志加载失败，请稍后重试。'
  } finally {
    loading.value = false
  }
}

function clearFilters() {
  filters.dateFrom = getDateBefore(29)
  filters.dateTo = todayString()
  filters.actorName = ''
  filters.objectType = ''
  void loadLogs()
}

function formatDateTime(value: string | null) {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatObjectType(value: string) {
  return (
    {
      training_plan_template: '模板',
      training_plan_template_item: '模板动作',
      exercise: '动作',
      exercise_library: '动作库',
      set_record: '训练组记录',
      sync_issue: '同步异常',
      sync_conflict: '同步冲突',
      test_record: '测试记录',
      test_records: '测试数据',
      training_records: '训练数据',
      database: '数据库',
    }[value] || value
  )
}

function formatSourceType(value: string) {
  return (
    {
      content_change: '内容修改',
      training_edit: '课后修改',
      sync_issue: '同步异常',
      sync_conflict: '同步冲突',
      dangerous_operation: '危险操作',
    }[value] || value
  )
}

function formatActorName(value: string | null) {
  return normalizeModeAliasForDisplay(value)
}

function snapshotEntries(snapshot: Record<string, unknown> | null): Array<{ key: string; value: string }> {
  if (!snapshot) return []
  return Object.entries(snapshot).map(([key, value]) => ({
    key,
    value: formatSnapshotValue(value),
  }))
}

function formatSnapshotValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (Array.isArray(value)) return value.map((item) => formatSnapshotValue(item)).join('、')
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

function hasSnapshot(log: LogItem) {
  return snapshotEntries(log.before_snapshot).length > 0 || snapshotEntries(log.after_snapshot).length > 0
}

function getDateBefore(days: number) {
  const current = new Date()
  current.setDate(current.getDate() - days)
  const year = current.getFullYear()
  const month = String(current.getMonth() + 1).padStart(2, '0')
  const day = String(current.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

onMounted(() => {
  void loadLogs()
})
</script>

<template>
  <AppShell>
    <div class="logs-layout">
      <aside class="panel filter-panel">
        <div>
          <p class="eyebrow">查询条件</p>
          <h3>操作日志</h3>
        </div>

        <label class="field">
          <span>开始日期</span>
          <input v-model="filters.dateFrom" type="date" class="text-input" />
        </label>

        <label class="field">
          <span>结束日期</span>
          <input v-model="filters.dateTo" type="date" class="text-input" />
        </label>

        <label class="field">
          <span>操作人</span>
          <input v-model="filters.actorName" class="text-input" placeholder="按姓名或角色关键词筛选" />
        </label>

        <label class="field">
          <span>对象类型</span>
          <select v-model="filters.objectType" class="text-input">
            <option value="">全部对象</option>
            <option v-for="option in objectTypeOptions" :key="option" :value="option">
              {{ formatObjectType(option) }}
            </option>
          </select>
        </label>

        <div class="filter-actions">
          <button class="primary-btn" type="button" :disabled="loading" @click="loadLogs">
            {{ loading ? '加载中...' : '查询日志' }}
          </button>
          <button class="ghost-btn" type="button" :disabled="loading" @click="clearFilters">重置筛选</button>
        </div>
      </aside>

      <section class="panel list-panel">
        <div class="list-head">
          <div>
            <p class="eyebrow">日志列表</p>
            <h3>共 {{ logs.length }} 条</h3>
          </div>
          <span class="muted">数据直接来自后端统一日志接口</span>
        </div>

        <p v-if="loadError" class="error-banner">{{ loadError }}</p>
        <div v-if="!loading && !logs.length && !loadError" class="empty-state">当前筛选条件下没有日志。</div>

        <div v-else class="log-list">
          <article v-for="log in logs" :key="`${log.source_type}-${log.id}`" class="log-card">
            <div class="log-card-head">
              <div class="log-card-title">
                <strong>{{ log.summary }}</strong>
                <div class="badge-row">
                  <span class="pill source-pill">{{ formatSourceType(log.source_type) }}</span>
                  <span class="pill object-pill">{{ formatObjectType(log.object_type) }}</span>
                  <span v-if="log.status" class="pill status-pill">{{ log.status }}</span>
                </div>
              </div>
              <span class="log-time">{{ formatDateTime(log.occurred_at) }}</span>
            </div>

            <div class="meta-grid">
              <div><span class="meta-label">操作人</span><span>{{ formatActorName(log.actor_name) || '—' }}</span></div>
              <div><span class="meta-label">影响对象</span><span>{{ log.object_label || '—' }}</span></div>
              <div><span class="meta-label">队伍</span><span>{{ log.team_name || '全局 / 未绑定' }}</span></div>
              <div><span class="meta-label">运动员</span><span>{{ log.athlete_name || '—' }}</span></div>
              <div><span class="meta-label">训练课</span><span>{{ log.session_id ? `#${log.session_id}` : '—' }}</span></div>
              <div><span class="meta-label">训练日期</span><span>{{ log.session_date || '—' }}</span></div>
            </div>

            <details v-if="hasSnapshot(log)" class="detail-block">
              <summary>查看关键前后变更</summary>
              <div class="snapshot-grid">
                <section class="snapshot-card">
                  <h4>变更前</h4>
                  <div v-if="snapshotEntries(log.before_snapshot).length" class="snapshot-list">
                    <div v-for="entry in snapshotEntries(log.before_snapshot)" :key="`before-${entry.key}`" class="snapshot-row">
                      <span class="snapshot-key">{{ entry.key }}</span>
                      <pre class="snapshot-value">{{ entry.value }}</pre>
                    </div>
                  </div>
                  <div v-else class="snapshot-empty">无</div>
                </section>

                <section class="snapshot-card">
                  <h4>变更后</h4>
                  <div v-if="snapshotEntries(log.after_snapshot).length" class="snapshot-list">
                    <div v-for="entry in snapshotEntries(log.after_snapshot)" :key="`after-${entry.key}`" class="snapshot-row">
                      <span class="snapshot-key">{{ entry.key }}</span>
                      <pre class="snapshot-value">{{ entry.value }}</pre>
                    </div>
                  </div>
                  <div v-else class="snapshot-empty">无</div>
                </section>
              </div>
            </details>
          </article>
        </div>
      </section>
    </div>
  </AppShell>
</template>

<style scoped>
.logs-layout {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 18px;
  min-height: 0;
}

.filter-panel,
.list-panel {
  min-height: 0;
}

.filter-panel {
  display: grid;
  align-content: start;
  gap: 14px;
}

.list-panel {
  display: grid;
  gap: 14px;
  align-content: start;
}

.list-head,
.filter-actions,
.log-card-head,
.badge-row {
  display: flex;
  gap: 10px;
}

.list-head,
.log-card-head {
  align-items: start;
  justify-content: space-between;
}

.filter-actions,
.badge-row {
  flex-wrap: wrap;
}

.field {
  display: grid;
  gap: 8px;
}

.log-list {
  display: grid;
  gap: 14px;
}

.log-card {
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  padding: 16px;
  display: grid;
  gap: 14px;
  background: var(--panel-soft);
}

.log-card-title {
  display: grid;
  gap: 8px;
}

.log-time,
.muted,
.eyebrow,
.meta-label,
.snapshot-empty {
  color: var(--text-soft);
  font-size: 13px;
}

.eyebrow {
  margin: 0;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.meta-grid > div {
  display: grid;
  gap: 4px;
}

.pill {
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 600;
}

.source-pill {
  background: rgba(15, 118, 110, 0.12);
  color: #0f766e;
}

.object-pill {
  background: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
}

.status-pill {
  background: rgba(245, 158, 11, 0.16);
  color: #92400e;
}

.detail-block {
  border-top: 1px dashed rgba(148, 163, 184, 0.3);
  padding-top: 12px;
}

.detail-block summary {
  cursor: pointer;
  font-weight: 600;
}

.snapshot-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.snapshot-card {
  background: white;
  border-radius: 14px;
  padding: 12px;
  border: 1px solid rgba(148, 163, 184, 0.16);
  display: grid;
  gap: 10px;
}

.snapshot-card h4 {
  margin: 0;
}

.snapshot-list {
  display: grid;
  gap: 8px;
}

.snapshot-row {
  display: grid;
  gap: 4px;
}

.snapshot-key {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-soft);
}

.snapshot-value {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
  background: rgba(148, 163, 184, 0.08);
  border-radius: 10px;
  padding: 8px 10px;
}

.empty-state,
.error-banner {
  padding: 16px;
  border-radius: 14px;
}

.empty-state {
  border: 1px dashed var(--line);
  color: var(--text-soft);
}

.error-banner {
  background: #fee2e2;
  color: #b91c1c;
}

@media (max-width: 1200px) {
  .logs-layout,
  .meta-grid,
  .snapshot-grid {
    grid-template-columns: 1fr;
  }
}
</style>
