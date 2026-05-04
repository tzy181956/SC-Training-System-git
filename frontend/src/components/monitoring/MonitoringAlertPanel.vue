<script setup lang="ts">
import { computed } from 'vue'

import {
  getTrainingStatusLabel,
  MONITORING_STATUS_LABEL_OVERRIDES,
} from '@/constants/trainingStatus'
import type { MonitoringAlertLevel, MonitoringAthleteCard } from '@/types/monitoring'

const props = defineProps<{
  athletes: MonitoringAthleteCard[]
  loading?: boolean
}>()

const alertLevelLabels: Record<MonitoringAlertLevel, string> = {
  none: '正常',
  info: '提示',
  warning: '警告',
  critical: '关键',
}

const alertAthletes = computed(() =>
  props.athletes.filter((athlete) => alertLevel(athlete) !== 'none'),
)

function alertLevel(athlete: MonitoringAthleteCard): MonitoringAlertLevel {
  if (athlete.alert_level && athlete.alert_level !== 'none') return athlete.alert_level
  if (!athlete.has_alert && athlete.sync_status === 'synced') return 'none'
  if (athlete.sync_status === 'manual_retry_required') return 'critical'
  return 'warning'
}

function fallbackAlertReason(athlete: MonitoringAthleteCard) {
  if (athlete.sync_status === 'manual_retry_required') return '同步异常待处理'
  if (athlete.sync_status === 'pending') return '本地数据待同步'
  if (athlete.session_status === 'partial_complete') return '已结束未完成'
  if (athlete.session_status === 'absent') return '缺席'
  return getTrainingStatusLabel(athlete.session_status, MONITORING_STATUS_LABEL_OVERRIDES)
}

function alertReasons(athlete: MonitoringAthleteCard) {
  return athlete.alert_reasons?.length ? athlete.alert_reasons : [fallbackAlertReason(athlete)]
}
</script>

<template>
  <aside class="alert-panel">
    <div class="panel-head">
      <div>
        <p class="section-label">异常提醒</p>
        <h3>需要关注</h3>
      </div>
      <span>{{ alertAthletes.length }} 项</span>
    </div>

    <div v-if="loading" class="alert-state">正在加载...</div>
    <div v-else-if="!alertAthletes.length" class="alert-state">当前没有同步异常或未完成提醒。</div>
    <div v-else class="alert-list">
      <article v-for="athlete in alertAthletes" :key="athlete.athlete_id" class="alert-row" :class="alertLevel(athlete)">
        <div class="adaptive-card">
          <strong class="adaptive-card-title">{{ athlete.athlete_name }}</strong>
          <span class="adaptive-card-subtitle">{{ athlete.team_name || '未分队' }}</span>
        </div>
        <span class="level-pill" :class="alertLevel(athlete)">{{ alertLevelLabels[alertLevel(athlete)] }}</span>
        <div class="reason-list">
          <span v-for="reason in alertReasons(athlete)" :key="reason">{{ reason }}</span>
        </div>
      </article>
    </div>
  </aside>
</template>

<style scoped>
.alert-panel {
  display: grid;
  gap: 12px;
  align-content: start;
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

.alert-state {
  min-height: 96px;
  display: grid;
  place-items: center;
  border: 1px dashed var(--line);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.72);
  text-align: center;
}
</style>
