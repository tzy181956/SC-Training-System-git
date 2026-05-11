<script setup lang="ts">
import { computed, ref } from 'vue'

import MonitoringAthleteCard from '@/components/monitoring/MonitoringAthleteCard.vue'
import type { MonitoringAthleteCard as MonitoringAthleteCardType } from '@/types/monitoring'

const props = defineProps<{
  athletes: MonitoringAthleteCardType[]
  sessionDate: string
  dismissedAlertKeys: string[]
  loading?: boolean
}>()

const emit = defineEmits<{
  selectAthlete: [athlete: MonitoringAthleteCardType]
}>()

const plannedExpanded = ref(true)
const noPlanExpanded = ref(false)

const plannedAthletes = computed(() => props.athletes.filter((athlete) => athlete.session_status !== 'no_plan'))
const noPlanAthletes = computed(() => props.athletes.filter((athlete) => athlete.session_status === 'no_plan'))
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
    <div v-else class="board-groups">
      <section class="board-group">
        <button class="group-toggle" type="button" @click="plannedExpanded = !plannedExpanded">
          <div class="group-copy">
            <strong>当日有训练计划的运动员</strong>
            <span>{{ plannedAthletes.length }} 人</span>
          </div>
          <span class="group-toggle-text">{{ plannedExpanded ? '收起' : '展开' }}</span>
        </button>
        <div v-if="plannedExpanded">
          <div v-if="plannedAthletes.length" class="athlete-grid">
            <MonitoringAthleteCard
              v-for="athlete in plannedAthletes"
              :key="athlete.athlete_id"
              :athlete="athlete"
              :session-date="sessionDate"
              :dismissed-alert-keys="dismissedAlertKeys"
              @select="emit('selectAthlete', athlete)"
            />
          </div>
          <div v-else class="group-empty">当前筛选范围内暂无已命中计划的运动员。</div>
        </div>
      </section>

      <section class="board-group">
        <button class="group-toggle" type="button" @click="noPlanExpanded = !noPlanExpanded">
          <div class="group-copy">
            <strong>当日没有训练计划的运动员</strong>
            <span>{{ noPlanAthletes.length }} 人</span>
          </div>
          <span class="group-toggle-text">{{ noPlanExpanded ? '收起' : '展开' }}</span>
        </button>
        <div v-if="noPlanExpanded">
          <div v-if="noPlanAthletes.length" class="athlete-grid">
            <MonitoringAthleteCard
              v-for="athlete in noPlanAthletes"
              :key="athlete.athlete_id"
              :athlete="athlete"
              :session-date="sessionDate"
              :dismissed-alert-keys="dismissedAlertKeys"
              @select="emit('selectAthlete', athlete)"
            />
          </div>
          <div v-else class="group-empty">当前筛选范围内所有运动员今天都已命中训练计划。</div>
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.board-section {
  display: grid;
  gap: 12px;
  align-content: start;
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

.board-groups {
  display: grid;
  gap: 14px;
}

.board-group {
  display: grid;
  gap: 12px;
}

.group-toggle {
  min-height: 52px;
  padding: 0 14px;
  border-radius: 14px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  background: rgba(255, 255, 255, 0.82);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  text-align: left;
  color: var(--text);
  cursor: pointer;
}

.group-copy {
  display: grid;
  gap: 4px;
}

.group-copy span,
.group-toggle-text,
.group-empty {
  color: var(--text-soft);
}

.group-toggle-text {
  font-size: 13px;
  font-weight: 800;
  white-space: nowrap;
}

.athlete-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.group-empty,
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
  .group-toggle {
    align-items: flex-start;
    flex-direction: column;
    padding: 12px 14px;
  }

  .athlete-grid {
    grid-template-columns: 1fr;
  }
}
</style>
