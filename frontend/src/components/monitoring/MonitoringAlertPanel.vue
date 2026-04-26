<script setup lang="ts">
import { computed } from 'vue'

import {
  getTrainingStatusLabel,
  MONITORING_STATUS_LABEL_OVERRIDES,
} from '@/constants/trainingStatus'
import type { MonitoringAthleteCard } from '@/types/monitoring'

const props = defineProps<{
  athletes: MonitoringAthleteCard[]
  loading?: boolean
}>()

const alertAthletes = computed(() =>
  props.athletes.filter((athlete) => athlete.has_alert || athlete.sync_status !== 'synced'),
)

function alertReason(athlete: MonitoringAthleteCard) {
  if (athlete.sync_status === 'manual_retry_required') return '同步异常待处理'
  if (athlete.sync_status === 'pending') return '本地数据待同步'
  if (athlete.session_status === 'partial_complete') return '已结束未完成'
  if (athlete.session_status === 'absent') return '缺席'
  return getTrainingStatusLabel(athlete.session_status, MONITORING_STATUS_LABEL_OVERRIDES)
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
      <article v-for="athlete in alertAthletes" :key="athlete.athlete_id" class="alert-row">
        <div class="adaptive-card">
          <strong class="adaptive-card-title">{{ athlete.athlete_name }}</strong>
          <span class="adaptive-card-subtitle">{{ athlete.team_name || '未分队' }}</span>
        </div>
        <span>{{ alertReason(athlete) }}</span>
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
  padding: 12px;
  border: 1px solid rgba(185, 28, 28, 0.16);
  border-radius: 12px;
  background: #fff7ed;
}

.alert-row > span {
  flex-shrink: 0;
  padding: 5px 8px;
  border-radius: 999px;
  background: #fee2e2;
  color: #b91c1c;
  font-size: 12px;
  font-weight: 700;
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
