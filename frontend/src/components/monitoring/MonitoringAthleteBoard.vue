<script setup lang="ts">
import MonitoringAthleteCard from '@/components/monitoring/MonitoringAthleteCard.vue'
import type { MonitoringAthleteCard as MonitoringAthleteCardType } from '@/types/monitoring'

defineProps<{
  athletes: MonitoringAthleteCardType[]
  loading?: boolean
}>()

const emit = defineEmits<{
  selectAthlete: [athlete: MonitoringAthleteCardType]
}>()
</script>

<template>
  <section class="board-section">
    <div class="section-head">
      <div>
        <p class="section-label">运动员看板</p>
        <h3>今日训练状态</h3>
      </div>
      <span>{{ athletes.length }} 人</span>
    </div>

    <div v-if="loading" class="board-state">正在加载监控数据...</div>
    <div v-else-if="!athletes.length" class="board-state">当前筛选范围内暂无运动员。</div>
    <div v-else class="athlete-grid">
      <MonitoringAthleteCard
        v-for="athlete in athletes"
        :key="athlete.athlete_id"
        :athlete="athlete"
        @select="emit('selectAthlete', athlete)"
      />
    </div>
  </section>
</template>

<style scoped>
.board-section {
  display: grid;
  gap: 12px;
}

.section-head {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 12px;
}

.section-head h3,
.section-head p {
  margin: 0;
}

.section-label,
.section-head span {
  color: var(--text-soft);
}

.athlete-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.board-state {
  min-height: 160px;
  display: grid;
  place-items: center;
  border: 1px dashed var(--line);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.72);
  color: var(--text-soft);
}

@media (max-width: 1280px) {
  .athlete-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 1180px) {
  .athlete-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 960px) {
  .athlete-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .athlete-grid {
    grid-template-columns: 1fr;
  }
}
</style>
