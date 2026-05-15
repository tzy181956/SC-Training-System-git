<script setup lang="ts">
import { computed, ref } from 'vue'

import type { MonitoringAlertLevel, MonitoringAthleteCard } from '@/types/monitoring'
import {
  buildMonitoringAlertKey,
  resolveMonitoringAlertLevel,
  resolveMonitoringAlertReasons,
} from '@/utils/monitoringAlerts'

const props = defineProps<{
  athletes: MonitoringAthleteCard[]
  sessionDate: string
  dismissedAlertKeys: string[]
  deletedAlertKeys: string[]
  loading?: boolean
}>()

const emit = defineEmits<{
  dismissAlert: [key: string]
  restoreAlert: [key: string]
  deleteAlert: [key: string]
}>()

const alertLevelLabels: Record<MonitoringAlertLevel, string> = {
  none: '正常',
  info: '提示',
  warning: '警告',
  critical: '关键',
}

type AlertEntry = {
  key: string
  athlete: MonitoringAthleteCard
  level: MonitoringAlertLevel
  reasons: string[]
  generatedAt: string | null
}

const archivedExpanded = ref(false)

function formatGeneratedAt(value: string | null | undefined) {
  if (!value) return '时间待确认'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '时间待确认'
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

const alertEntries = computed<AlertEntry[]>(() =>
  props.athletes.reduce<AlertEntry[]>((entries, athlete) => {
    const level = resolveMonitoringAlertLevel(athlete)
    if (level === 'none') return entries
    const reasons = resolveMonitoringAlertReasons(athlete)
    entries.push({
      key: buildMonitoringAlertKey(props.sessionDate, athlete),
      athlete,
      level,
      reasons,
      generatedAt: athlete.alert_generated_at || null,
    })
    return entries
  }, []),
)

const dismissedKeySet = computed(() => new Set(props.dismissedAlertKeys))
const deletedKeySet = computed(() => new Set(props.deletedAlertKeys))
const activeAlerts = computed(() =>
  alertEntries.value.filter((entry) => !dismissedKeySet.value.has(entry.key) && !deletedKeySet.value.has(entry.key)),
)
const archivedAlerts = computed(() =>
  alertEntries.value.filter((entry) => dismissedKeySet.value.has(entry.key) && !deletedKeySet.value.has(entry.key)),
)
</script>

<template>
  <aside class="alert-panel">
    <div class="panel-head">
      <div>
        <p class="section-label">异常提醒</p>
        <h3>需要关注</h3>
      </div>
      <span>{{ activeAlerts.length }} 项</span>
    </div>

    <div v-if="loading" class="alert-state">正在加载...</div>
    <template v-else>
      <div v-if="!activeAlerts.length" class="alert-state">当前没有未收起的提醒。</div>
      <div v-else class="alert-list">
        <article v-for="entry in activeAlerts" :key="entry.key" class="alert-row" :class="entry.level">
          <div class="adaptive-card">
            <div class="row-head">
              <strong class="adaptive-card-title">{{ entry.athlete.athlete_name }}</strong>
              <button class="ghost-btn slim-btn alert-action" type="button" @click="emit('dismissAlert', entry.key)">收起提醒</button>
            </div>
            <span class="adaptive-card-subtitle">{{ entry.athlete.team_name || '未分队' }}</span>
            <span class="generated-at">产生时间：{{ formatGeneratedAt(entry.generatedAt) }}</span>
          </div>
          <span class="level-pill" :class="entry.level">{{ alertLevelLabels[entry.level] }}</span>
          <div class="reason-list">
            <span v-for="reason in entry.reasons" :key="reason">{{ reason }}</span>
          </div>
        </article>
      </div>

      <section v-if="archivedAlerts.length" class="archived-panel">
        <button class="archived-toggle" type="button" @click="archivedExpanded = !archivedExpanded">
          <span>已收起提醒 {{ archivedAlerts.length }} 项</span>
          <span>{{ archivedExpanded ? '收起' : '展开' }}</span>
        </button>
        <div v-if="archivedExpanded" class="archived-list">
          <article v-for="entry in archivedAlerts" :key="entry.key" class="alert-row archived" :class="entry.level">
            <div class="adaptive-card">
              <div class="row-head">
                <strong class="adaptive-card-title">{{ entry.athlete.athlete_name }}</strong>
                <div class="archived-actions">
                  <button class="ghost-btn slim-btn alert-action" type="button" @click="emit('restoreAlert', entry.key)">恢复提醒</button>
                  <button class="ghost-btn slim-btn danger alert-action" type="button" @click="emit('deleteAlert', entry.key)">删除提醒</button>
                </div>
              </div>
              <span class="adaptive-card-subtitle">{{ entry.athlete.team_name || '未分队' }}</span>
              <span class="generated-at">产生时间：{{ formatGeneratedAt(entry.generatedAt) }}</span>
            </div>
            <span class="level-pill" :class="entry.level">{{ alertLevelLabels[entry.level] }}</span>
            <div class="reason-list">
              <span v-for="reason in entry.reasons" :key="reason">{{ reason }}</span>
            </div>
          </article>
        </div>
      </section>
    </template>
  </aside>
</template>

<style scoped>
.alert-panel {
  display: grid;
  grid-template-rows: auto minmax(0, 1fr) auto;
  gap: 12px;
  align-content: stretch;
  height: 100%;
  min-height: 0;
  padding: 14px;
  border: 1px solid rgba(185, 28, 28, 0.18);
  border-radius: 14px;
  background: rgba(255, 247, 237, 0.72);
}

.panel-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}

.panel-head h3,
.panel-head p {
  margin: 0;
}

.section-label,
.panel-head span,
.alert-state {
  color: var(--text-soft);
}

.alert-list {
  display: grid;
  gap: 10px;
  align-content: start;
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 4px;
  scrollbar-gutter: stable;
}

.alert-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 12px;
  min-width: 0;
  padding: 12px;
  border: 1px solid rgba(185, 28, 28, 0.16);
  border-radius: 12px;
  background: #fff7ed;
}

.row-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.generated-at {
  margin-top: 4px;
  color: var(--text-soft);
  font-size: 12px;
  font-weight: 700;
}

.alert-action {
  flex-shrink: 0;
}

.archived-actions {
  display: inline-flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 8px;
}

.level-pill {
  flex-shrink: 0;
  padding: 5px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
}

.level-pill.info {
  background: #dbeafe;
  color: #1d4ed8;
}

.level-pill.warning {
  background: #fef3c7;
  color: #92400e;
}

.level-pill.critical {
  background: #fee2e2;
  color: #b91c1c;
}

.reason-list {
  grid-column: 1 / -1;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.reason-list span {
  flex-shrink: 0;
  padding: 5px 8px;
  border-radius: 999px;
  background: #fef3c7;
  color: #92400e;
  font-size: 12px;
  font-weight: 700;
}

.alert-row.info .reason-list span {
  background: #dbeafe;
  color: #1d4ed8;
}

.alert-row.critical .reason-list span {
  background: #fee2e2;
  color: #b91c1c;
}

.archived-panel {
  display: grid;
  gap: 10px;
  padding-top: 4px;
  border-top: 1px dashed rgba(15, 23, 42, 0.1);
}

.archived-toggle {
  min-height: 42px;
  padding: 0 12px;
  border-radius: 12px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.76);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  color: var(--text);
  font-size: 13px;
  font-weight: 800;
}

.archived-list {
  display: grid;
  gap: 10px;
  align-content: start;
  max-height: min(36vh, 360px);
  overflow-y: auto;
  overscroll-behavior: contain;
  padding-right: 4px;
  scrollbar-gutter: stable;
}

.alert-row.archived {
  background: rgba(255, 255, 255, 0.82);
  border-style: dashed;
}

.alert-state {
  min-height: 96px;
  display: grid;
  place-items: center;
  border: 1px dashed var(--line);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
  text-align: center;
}

@media (max-width: 1180px) {
  .alert-panel {
    height: auto;
  }

  .alert-list {
    max-height: min(70vh, 760px);
  }
}
</style>
