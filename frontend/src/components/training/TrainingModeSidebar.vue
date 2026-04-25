<script setup lang="ts">
defineProps<{
  athletes: any[]
  selectedAthleteId: number
  assignments: any[]
  previewAssignmentId: number
}>()

const emit = defineEmits<{
  updateAthlete: [athleteId: number]
  openPlan: [assignmentId: number]
}>()

function getTrainingDisplayStatus(status?: string) {
  return status || 'no_plan'
}

function statusLabel(status?: string) {
  const displayStatus = getTrainingDisplayStatus(status)
  if (displayStatus === 'completed') return '已完成'
  if (displayStatus === 'partial_complete') return '已完成'
  if (displayStatus === 'in_progress') return '进行中'
  if (displayStatus === 'absent') return '缺席'
  if (displayStatus === 'not_started') return '未开始'
  return '无计划'
}

function openAthletePlan(athleteId: number, assignmentId: number) {
  emit('updateAthlete', athleteId)
  emit('openPlan', assignmentId)
}

function handleAthleteClick(athlete: any) {
  const assignments = Array.isArray(athlete.assignments) ? athlete.assignments : []
  if (assignments.length === 1) {
    openAthletePlan(athlete.id, assignments[0].id)
    return
  }

  emit('updateAthlete', athlete.id)
}
</script>

<template>
  <aside class="panel sidebar">
    <div class="block roster-block">
      <p class="section-title">1. 选择队员</p>
      <div class="athlete-list">
        <article
          v-for="athlete in athletes"
          :key="athlete.id"
          class="athlete-card adaptive-card"
          :class="{ active: athlete.id === selectedAthleteId }"
        >
          <button class="athlete-main" type="button" @click="handleAthleteClick(athlete)">
            <div class="athlete-header">
              <strong class="adaptive-card-title athlete-name">{{ athlete.full_name }}</strong>
              <span class="status-pill" :class="getTrainingDisplayStatus(athlete.training_status)">
                {{ statusLabel(athlete.training_status) }}
              </span>
            </div>
            <span class="adaptive-card-subtitle athlete-team">{{ athlete.team?.name || '未分队' }}</span>
          </button>

          <div v-if="athlete.assignments?.length" class="plans-wrap">
            <div class="plans-shell">
              <button
                v-for="assignment in athlete.assignments"
                :key="assignment.id"
                class="inline-plan adaptive-card"
                :class="[getTrainingDisplayStatus(assignment.training_status), { active: assignment.id === previewAssignmentId }]"
                type="button"
                @click="openAthletePlan(athlete.id, assignment.id)"
              >
                <span class="plan-dot" />
                <span class="plan-text adaptive-card-title adaptive-card-clamp-2">{{ assignment.template.name }}</span>
              </button>
            </div>
          </div>

          <div v-else class="empty-plan-wrap">
            <p class="empty-plan-hint adaptive-card-meta">当天没有可录入的训练计划</p>
          </div>
        </article>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar,
.block {
  display: grid;
  gap: 18px;
  min-height: 0;
}

.sidebar {
  grid-template-rows: minmax(0, 1fr);
  overflow: hidden;
}

.roster-block {
  grid-template-rows: auto minmax(0, 1fr);
}

.athlete-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 6px;
  scrollbar-gutter: stable;
}

.athlete-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  flex: 0 0 auto;
  min-width: 0;
  min-height: 108px;
  padding: 14px;
  border-radius: 16px;
  background: var(--panel-soft);
}

.athlete-card.active {
  background: #d1fae5;
}

.athlete-main {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  min-width: 0;
  padding: 0;
  background: transparent;
  text-align: left;
}

.athlete-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 10px;
  min-width: 0;
}

.athlete-name {
  flex: 1;
  font-size: 20px;
  line-height: 1.25;
  font-weight: 800;
}

.athlete-team {
  font-size: 12px;
  line-height: 1.35;
}

.status-pill {
  flex-shrink: 0;
  padding: 4px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.status-pill.completed {
  background: #dcfce7;
  color: #166534;
}

.status-pill.in_progress {
  background: #fef3c7;
  color: #92400e;
}

.status-pill.partial_complete {
  background: #ecf7cf;
  color: #4d7c0f;
}

.status-pill.absent {
  background: #e5e7eb;
  color: #374151;
}

.status-pill.not_started {
  background: #fee2e2;
  color: #b91c1c;
}

.status-pill.no_plan {
  background: #e5e7eb;
  color: #4b5563;
}

.plans-wrap,
.empty-plan-wrap {
  display: block;
  width: 100%;
  flex: 0 0 auto;
  min-width: 0;
}

.plans-shell {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  min-width: 0;
  padding: 10px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.28);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.3);
}

.inline-plan {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  width: 100%;
  min-width: 0;
  padding: 10px 12px;
  border: 1px solid rgba(203, 213, 225, 0.9);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.84);
  color: var(--muted);
  text-align: left;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.inline-plan.active {
  border-color: rgba(15, 118, 110, 0.24);
  background: #ffffff;
  color: #0f766e;
  box-shadow: 0 0 0 1px rgba(15, 118, 110, 0.08), 0 6px 16px rgba(15, 118, 110, 0.08);
  font-weight: 700;
}

.plan-text {
  flex: 1;
  min-width: 0;
  font-size: 15px;
  line-height: 1.35;
  font-weight: 600;
}

.plan-dot {
  width: 10px;
  height: 10px;
  margin-top: 4px;
  border-radius: 999px;
  flex-shrink: 0;
  background: #9ca3af;
}

.inline-plan.completed .plan-dot {
  background: #22c55e;
}

.inline-plan.in_progress .plan-dot {
  background: #f59e0b;
}

.inline-plan.partial_complete .plan-dot {
  background: #84cc16;
}

.inline-plan.absent .plan-dot {
  background: #6b7280;
}

.inline-plan.not_started .plan-dot {
  background: #ef4444;
}

.empty-plan-hint {
  margin: 0;
  padding: 12px 14px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.55);
  line-height: 1.4;
}

.section-title {
  margin: 0;
  color: var(--muted);
}

@media (min-width: 768px) and (max-width: 1199px) {
  .athlete-card {
    gap: 10px;
    min-height: 96px;
    padding: 12px;
  }

  .athlete-name {
    font-size: 18px;
  }
}

@media (max-width: 767px) {
  .athlete-name {
    font-size: 18px;
  }
}
</style>
