<script setup lang="ts">
import { computed } from 'vue'

import type { MonitoringAthleteCard } from '@/types/monitoring'

const props = defineProps<{
  athletes: MonitoringAthleteCard[]
  loading?: boolean
}>()

const summary = computed(() => {
  const athletes = props.athletes
  const totalSets = athletes.reduce((sum, athlete) => sum + athlete.total_sets, 0)
  const completedSets = athletes.reduce((sum, athlete) => sum + athlete.completed_sets, 0)

  return {
    totalAthletes: athletes.length,
    inProgress: athletes.filter((athlete) => athlete.session_status === 'in_progress').length,
    completed: athletes.filter((athlete) => athlete.session_status === 'completed').length,
    partialComplete: athletes.filter((athlete) => athlete.session_status === 'partial_complete').length,
    notStarted: athletes.filter((athlete) => athlete.session_status === 'not_started').length,
    absent: athletes.filter((athlete) => athlete.session_status === 'absent').length,
    noPlan: athletes.filter((athlete) => athlete.session_status === 'no_plan').length,
    alerts: athletes.filter((athlete) => athlete.has_alert || athlete.sync_status !== 'synced').length,
    completedSets,
    totalSets,
    completionRate: totalSets ? Math.round((completedSets / totalSets) * 100) : 0,
  }
})
</script>

<template>
  <section class="summary-grid" :class="{ muted: loading }">
    <article class="summary-card">
      <span>队员</span>
      <strong>{{ summary.totalAthletes }}</strong>
      <p>当前筛选范围</p>
    </article>
    <article class="summary-card progress">
      <span>进行中</span>
      <strong>{{ summary.inProgress }}</strong>
      <p>正在训练</p>
    </article>
    <article class="summary-card success">
      <span>已完成</span>
      <strong>{{ summary.completed }}</strong>
      <p>{{ summary.totalSets ? `总组进度 ${summary.completedSets}/${summary.totalSets} · ${summary.completionRate}%` : '暂无组计划' }}</p>
    </article>
    <article class="summary-card partial">
      <span>已结束未完成</span>
      <strong>{{ summary.partialComplete }}</strong>
      <p>需要课后确认</p>
    </article>
    <article class="summary-card danger">
      <span>异常</span>
      <strong>{{ summary.alerts }}</strong>
      <p>同步或状态需关注</p>
    </article>
    <article class="summary-card neutral">
      <span>未开始 / 缺席 / 无计划</span>
      <strong>{{ summary.notStarted + summary.absent + summary.noPlan }}</strong>
      <p>尚未进入训练</p>
    </article>
  </section>
</template>

<style scoped>
.summary-grid {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 12px;
}

.summary-grid.muted {
  opacity: 0.72;
}

.summary-card {
  display: grid;
  gap: 4px;
  min-height: 108px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: white;
}

.summary-card span,
.summary-card p {
  margin: 0;
  color: var(--text-soft);
  font-size: 13px;
}

.summary-card strong {
  font-size: 2rem;
  line-height: 1;
}

.summary-card.progress {
  border-color: rgba(37, 99, 235, 0.22);
}

.summary-card.success {
  border-color: rgba(22, 101, 52, 0.22);
}

.summary-card.partial {
  border-color: rgba(194, 65, 12, 0.24);
}

.summary-card.danger {
  border-color: rgba(185, 28, 28, 0.24);
}

.summary-card.neutral {
  border-color: rgba(100, 116, 139, 0.26);
}

@media (max-width: 1180px) {
  .summary-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .summary-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 720px) {
  .summary-grid {
    grid-template-columns: 1fr;
  }
}
</style>
