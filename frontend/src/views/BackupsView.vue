<script setup lang="ts">
import axios from 'axios'
import { computed, onMounted, ref } from 'vue'

import { fetchBackups, restoreBackup, type BackupItem, type RestoreScope } from '@/api/backups'
import AppShell from '@/components/layout/AppShell.vue'
import { confirmDangerousAction } from '@/utils/dangerousAction'

const loading = ref(false)
const restoring = ref(false)
const loadError = ref('')
const actionMessage = ref('')
const actionTone = ref<'success' | 'warning' | 'error'>('success')
const backups = ref<BackupItem[]>([])
const restoreScopes = ref<RestoreScope[]>([])
const backupDirectory = ref('')
const filenamePattern = ref('')
const keepRecentDays = ref(0)
const keepRecentWeeks = ref(0)
const selectedBackupFilename = ref('')
const selectedScopeKey = ref<'full_database' | 'training_records' | 'test_records'>('full_database')

const selectedBackup = computed(() => backups.value.find((item) => item.filename === selectedBackupFilename.value) || null)
const selectedScope = computed(() => restoreScopes.value.find((item) => item.key === selectedScopeKey.value) || null)
const totalBackupSizeBytes = computed(() =>
  backups.value.reduce((total, item) => total + Math.max(item.size_bytes || 0, 0), 0),
)

async function loadBackupList() {
  loading.value = true
  loadError.value = ''
  try {
    const response = await fetchBackups()
    backups.value = response.items || []
    restoreScopes.value = response.available_restore_scopes || []
    backupDirectory.value = response.backup_directory || ''
    filenamePattern.value = response.filename_pattern || ''
    keepRecentDays.value = response.keep_recent_days || 0
    keepRecentWeeks.value = response.keep_recent_weeks || 0

    if (!selectedBackupFilename.value && backups.value[0]) {
      selectedBackupFilename.value = backups.value[0].filename
    }
    if (selectedBackupFilename.value && !backups.value.some((item) => item.filename === selectedBackupFilename.value)) {
      selectedBackupFilename.value = backups.value[0]?.filename || ''
    }
    if (!restoreScopes.value.some((item) => item.key === selectedScopeKey.value)) {
      selectedScopeKey.value = (restoreScopes.value[0]?.key || 'full_database') as typeof selectedScopeKey.value
    }
  } catch (error) {
    loadError.value = extractErrorMessage(error, '备份列表加载失败，请稍后重试。')
    backups.value = []
    restoreScopes.value = []
  } finally {
    loading.value = false
  }
}

function selectBackup(filename: string) {
  selectedBackupFilename.value = filename
}

function selectScope(scopeKey: RestoreScope['key']) {
  selectedScopeKey.value = scopeKey
}

async function handleRestore() {
  if (!selectedBackup.value || !selectedScope.value) return

  const confirmed = confirmDangerousAction({
    title: `恢复备份：${selectedScope.value.label}`,
    impactLines: [
      `备份文件：${selectedBackup.value.filename}`,
      `恢复时间点：${formatDateTime(selectedBackup.value.restore_point_at)}`,
      ...selectedScope.value.impact_summary,
    ],
    recommendation: '系统会先自动为当前正式数据库做一份兜底备份；建议在无人录课时执行恢复。',
    confirmationKeyword: 'RESTORE_BACKUP',
  })
  if (!confirmed) return

  restoring.value = true
  actionMessage.value = ''
  try {
    const result = await restoreBackup({
      confirmed: true,
      actor_name: '管理端',
      confirmation_text: 'RESTORE_BACKUP',
      backup_filename: selectedBackup.value.filename,
      restore_scope: selectedScope.value.key,
    })
    actionTone.value = 'success'
    actionMessage.value = [
      result.message,
      result.pre_restore_backup_path ? `恢复前兜底备份：${result.pre_restore_backup_path}` : '',
    ]
      .filter(Boolean)
      .join('；')
    await loadBackupList()
    selectedBackupFilename.value = result.backup_filename
  } catch (error) {
    actionTone.value = 'error'
    actionMessage.value = extractErrorMessage(error, '恢复失败，请先确认影响范围和确认词是否正确。')
  } finally {
    restoring.value = false
  }
}

function formatDateTime(value: string | null) {
  if (!value) return '—'
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatFileSize(sizeBytes: number) {
  if (sizeBytes >= 1024 * 1024 * 1024) {
    return `${(sizeBytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
  }
  if (sizeBytes >= 1024 * 1024) {
    return `${(sizeBytes / (1024 * 1024)).toFixed(2)} MB`
  }
  if (sizeBytes >= 1024) {
    return `${(sizeBytes / 1024).toFixed(1)} KB`
  }
  return `${sizeBytes} B`
}

function formatTriggerLabel(backup: BackupItem) {
  return backup.trigger_label || backup.trigger || '手动/未知来源'
}

function extractErrorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.join('；')
    if (error.message) return error.message
  }
  return fallback
}

onMounted(() => {
  void loadBackupList()
})
</script>

<template>
  <AppShell>
    <div class="page-grid">
      <section class="panel summary-panel">
        <div>
          <p class="eyebrow">备份恢复</p>
          <h3>恢复页基础版</h3>
        </div>
        <div class="summary-grid">
          <div class="summary-item">
            <span class="summary-label">备份目录</span>
            <strong>{{ backupDirectory || '—' }}</strong>
          </div>
          <div class="summary-item">
            <span class="summary-label">文件命名规则</span>
            <strong>{{ filenamePattern || '—' }}</strong>
          </div>
          <div class="summary-item">
            <span class="summary-label">保留策略</span>
            <strong>最近 {{ keepRecentDays }} 天 + 最近 {{ keepRecentWeeks }} 周</strong>
          </div>
          <div class="summary-item">
            <span class="summary-label">当前备份数</span>
            <strong>{{ backups.length }}</strong>
          </div>
          <div class="summary-item">
            <span class="summary-label">当前占用空间</span>
            <strong>{{ formatFileSize(totalBackupSizeBytes) }}</strong>
          </div>
        </div>
      </section>

      <div class="backup-layout">
        <section class="panel backup-list-panel">
          <div class="section-head">
            <div>
              <p class="eyebrow">备份列表</p>
              <h3>从备份列表恢复</h3>
            </div>
            <button class="ghost-btn" type="button" :disabled="loading" @click="loadBackupList">
              {{ loading ? '刷新中…' : '刷新列表' }}
            </button>
          </div>

          <p v-if="loadError" class="status-banner error">{{ loadError }}</p>
          <div v-else-if="!loading && !backups.length" class="empty-state">当前备份目录还没有可恢复的数据库备份。</div>

          <div v-else class="backup-list">
            <button
              v-for="backup in backups"
              :key="backup.filename"
              type="button"
              class="backup-card"
              :class="{ active: backup.filename === selectedBackupFilename }"
              @click="selectBackup(backup.filename)"
            >
              <div class="backup-card-head">
                <strong>{{ backup.filename }}</strong>
                <span class="pill">{{ formatTriggerLabel(backup) }}</span>
              </div>
              <div class="backup-meta">
                <span>恢复时间点：{{ formatDateTime(backup.restore_point_at) }}</span>
                <span>文件大小：{{ formatFileSize(backup.size_bytes) }}</span>
                <span>文件时间：{{ formatDateTime(backup.file_modified_at) }}</span>
              </div>
            </button>
          </div>
        </section>

        <section class="panel restore-panel">
          <div class="section-head">
            <div>
              <p class="eyebrow">恢复详情</p>
              <h3>{{ selectedBackup ? selectedBackup.filename : '请选择一个备份' }}</h3>
            </div>
          </div>

          <p v-if="actionMessage" class="status-banner" :class="actionTone">{{ actionMessage }}</p>

          <template v-if="selectedBackup">
            <div class="detail-grid">
              <div class="detail-item">
                <span class="summary-label">恢复时间点</span>
                <strong>{{ formatDateTime(selectedBackup.restore_point_at) }}</strong>
              </div>
              <div class="detail-item">
                <span class="summary-label">来源类型</span>
                <strong>{{ formatTriggerLabel(selectedBackup) }}</strong>
              </div>
              <div class="detail-item">
                <span class="summary-label">文件大小</span>
                <strong>{{ formatFileSize(selectedBackup.size_bytes) }}</strong>
              </div>
              <div class="detail-item">
                <span class="summary-label">文件路径</span>
                <strong>{{ selectedBackup.path }}</strong>
              </div>
            </div>

            <div class="scope-section">
              <div>
                <p class="eyebrow">恢复范围</p>
                <h4>整库恢复 / 某类数据恢复</h4>
              </div>
              <div class="scope-grid">
                <button
                  v-for="scope in restoreScopes"
                  :key="scope.key"
                  type="button"
                  class="scope-card"
                  :class="{ active: selectedScopeKey === scope.key }"
                  @click="selectScope(scope.key)"
                >
                  <strong>{{ scope.label }}</strong>
                  <span>{{ scope.description }}</span>
                  <small v-if="scope.affected_tables.length">涉及表：{{ scope.affected_tables.join('、') }}</small>
                </button>
              </div>
            </div>

            <div v-if="selectedScope" class="impact-panel">
              <div>
                <p class="eyebrow">影响范围</p>
                <h4>{{ selectedScope.label }}</h4>
              </div>
              <ul class="impact-list">
                <li v-for="line in selectedScope.impact_summary" :key="line">{{ line }}</li>
              </ul>
              <div class="warning-box">
                恢复前会要求二次确认和确认词；建议在无人录课时执行，并保留系统自动生成的恢复前兜底备份。
              </div>
            </div>

            <div class="restore-actions">
              <button class="primary-btn" type="button" :disabled="restoring || !selectedScope" @click="handleRestore">
                {{ restoring ? '恢复中…' : `执行${selectedScope?.label || '恢复'}` }}
              </button>
            </div>
          </template>
        </section>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.page-grid {
  display: grid;
  gap: 18px;
  align-content: start;
}

.summary-panel,
.backup-list-panel,
.restore-panel {
  display: grid;
  gap: 14px;
  align-content: start;
}

.backup-layout {
  display: grid;
  grid-template-columns: minmax(360px, 420px) 1fr;
  gap: 18px;
  min-height: 0;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 16px;
}

.summary-grid,
.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.summary-item,
.detail-item {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 16px;
  background: var(--panel-soft);
}

.summary-label,
.eyebrow {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
}

.backup-list {
  display: grid;
  gap: 12px;
  max-height: 720px;
  overflow-y: auto;
  padding-right: 8px;
}

.backup-card,
.scope-card {
  display: grid;
  gap: 10px;
  width: 100%;
  text-align: left;
  padding: 16px;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background: var(--panel-soft);
}

.backup-card.active,
.scope-card.active {
  border-color: rgba(15, 118, 110, 0.46);
  background: rgba(15, 118, 110, 0.08);
}

.backup-card-head {
  display: flex;
  justify-content: space-between;
  align-items: start;
  gap: 10px;
}

.backup-meta {
  display: grid;
  gap: 4px;
  color: var(--text-soft);
  font-size: 13px;
}

.pill {
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  font-weight: 600;
  background: rgba(59, 130, 246, 0.12);
  color: #1d4ed8;
}

.scope-section,
.impact-panel {
  display: grid;
  gap: 12px;
}

.scope-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.scope-card span,
.scope-card small {
  color: var(--text-soft);
}

.impact-list {
  margin: 0;
  padding-left: 18px;
  display: grid;
  gap: 8px;
}

.warning-box,
.empty-state,
.status-banner {
  padding: 14px 16px;
  border-radius: 16px;
}

.warning-box {
  background: rgba(245, 158, 11, 0.12);
  color: #92400e;
}

.status-banner.success {
  background: #dcfce7;
  color: #166534;
}

.status-banner.warning {
  background: #fef3c7;
  color: #92400e;
}

.status-banner.error,
.empty-state {
  background: #fee2e2;
  color: #b91c1c;
}

.restore-actions {
  display: flex;
  justify-content: flex-start;
}

@media (max-width: 1200px) {
  .backup-layout,
  .summary-grid,
  .detail-grid,
  .scope-grid {
    grid-template-columns: 1fr;
  }
}
</style>
