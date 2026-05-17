<script setup lang="ts">
import { getTrainingStatusLabel, getTrainingStatusTone } from '@/constants/trainingStatus'

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

function statusLabel(status?: string) {
  return getTrainingStatusLabel(status)
}

function statusTone(status?: string) {
  return getTrainingStatusTone(status)
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
          data-testid="training-athlete-card"
          :data-athlete-name="athlete.full_name"
        >
          <button class="athlete-main" type="button" data-testid="training-athlete-main" @click="handleAthleteClick(athlete)">
            <div class="athlete-header">
              <strong class="adaptive-card-title athlete-name">{{ athlete.full_name }}</strong>
              <span class="status-pill" :class="statusTone(athlete.training_status)">
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
                :class="[statusTone(assignment.training_status), { active: assignment.id === previewAssignmentId }]"
                data-testid="training-plan-card"
                :data-athlete-name="athlete.full_name"
                :data-template-name="assignment.template.name"
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

.status-pill.success {
  background: #dcfce7;
  color: #166534;
}

.status-pill.progress {
  background: #dbeafe;
  color: #1d4ed8;
}

.status-pill.partial {
  background: #ffedd5;
  color: #c2410c;
}

.status-pill.neutral {
  background: #e5e7eb;
  color: #374151;
}

.status-pill.danger {
  background: #fee2e2;
  color: #b91c1c;
}

.status-pill.warning {
  background: #fef3c7;
  color: #92400e;
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

.inline-plan.success .plan-dot {
  background: #22c55e;
}

.inline-plan.progress .plan-dot {
  background: #3b82f6;
}

.inline-plan.partial .plan-dot {
  background: #f97316;
}

.inline-plan.neutral .plan-dot {
  background: #6b7280;
}

.inline-plan.danger .plan-dot {
  background: #ef4444;
}

.inline-plan.warning .plan-dot {
  background: #f59e0b;
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

@media (min-width: 900px) and (max-width: 1199px) and (orientation: landscape) {
  .sidebar,
  .block {
    gap: 12px;
  }

  .athlete-list {
    gap: 9px;
    padding-right: 4px;
  }

  .athlete-card {
    gap: 8px;
    min-height: 90px;
    padding: 10px;
    border-radius: 14px;
  }

  .athlete-main {
    gap: 6px;
  }

  .athlete-header {
    align-items: center;
    gap: 6px;
  }

  .athlete-name {
    font-size: 18px;
    line-height: 1.18;
  }

  .athlete-team {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .status-pill {
    padding: 3px 6px;
    font-size: 11px;
  }

  .plans-shell {
    gap: 6px;
    padding: 8px;
    border-radius: 14px;
  }

  .inline-plan {
    gap: 6px;
    padding: 8px 10px;
    border-radius: 11px;
  }

  .plan-text {
    font-size: 14px;
    line-height: 1.28;
  }

  .empty-plan-hint {
    padding: 10px 12px;
    border-radius: 12px;
  }
}

@media (min-width: 900px) and (max-width: 1050px) and (orientation: landscape) {
  .athlete-card {
    min-height: 84px;
    padding: 9px;
  }

  .athlete-name {
    font-size: 17px;
  }

  .plan-text {
    font-size: 13px;
  }
}

@media (max-width: 899px) {
  .athlete-name {
    font-size: 18px;
  }
}
</style>
