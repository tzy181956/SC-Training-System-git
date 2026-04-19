<script setup lang="ts">
defineProps<{
  athletes: any[]
  selectedAthleteId: number
  sessionDate: string
  teamOptions: { id: string; name: string }[]
  selectedTeamFilter: string
  assignments: any[]
  previewAssignmentId: number
}>()

const emit = defineEmits<{
  updateAthlete: [athleteId: number]
  updateDate: [value: string]
  updateTeamFilter: [value: string]
  openPlan: [assignmentId: number]
}>()

function handleDateInput(event: Event) { emit('updateDate', (event.target as HTMLInputElement).value) }
function handleTeamFilterInput(event: Event) { emit('updateTeamFilter', (event.target as HTMLSelectElement).value) }

function statusLabel(status?: string) {
  if (status === 'completed') return '已完成'
  if (status === 'in_progress') return '进行中'
  if (status === 'not_started') return '未开始'
  return '无计划'
}

function openAthletePlan(athleteId: number, assignmentId: number) {
  emit('updateAthlete', athleteId)
  emit('openPlan', assignmentId)
}
</script>

<template>
  <aside class="panel sidebar">
    <div class="block">
      <p class="section-title">1. 选择日期和队伍</p>
      <div class="filters-row">
        <input :value="sessionDate" class="text-input date-input" type="date" @input="handleDateInput" />
        <select :value="selectedTeamFilter" class="text-input team-select" @input="handleTeamFilterInput">
          <option v-for="team in teamOptions" :key="team.id" :value="team.id">{{ team.name }}</option>
        </select>
      </div>
    </div>

    <div class="block">
      <p class="section-title">2. 选择队员</p>
      <div class="athlete-list">
        <div v-for="athlete in athletes" :key="athlete.id" class="athlete-card adaptive-card" :class="{ active: athlete.id === selectedAthleteId }">
          <button class="athlete-main" type="button" @click="emit('updateAthlete', athlete.id)">
            <div class="athlete-header">
              <strong class="adaptive-card-title">{{ athlete.full_name }}</strong>
              <span class="status-pill" :class="athlete.training_status">{{ statusLabel(athlete.training_status) }}</span>
            </div>
            <span class="adaptive-card-subtitle adaptive-card-clamp-2">{{ athlete.team?.name || '未分队' }}</span>
          </button>

          <div v-if="athlete.assignments?.length" class="inline-plans">
            <button
              v-for="assignment in athlete.assignments"
              :key="assignment.id"
              class="inline-plan adaptive-card"
              :class="[assignment.training_status, { active: assignment.id === previewAssignmentId }]"
              type="button"
              @click="openAthletePlan(athlete.id, assignment.id)"
            >
              <span class="plan-dot" />
              <span class="adaptive-card-subtitle adaptive-card-clamp-2">{{ assignment.template.name }}</span>
            </button>
          </div>

          <p v-else class="empty-plan-hint adaptive-card-meta adaptive-card-clamp-2">当天没有可录入的训练计划</p>
        </div>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar,.block{display:grid;gap:18px;min-height:0}
.sidebar{grid-template-rows:auto minmax(0,1fr);overflow:hidden}
.block{gap:12px}
.filters-row{display:grid;gap:10px}
.athlete-list{display:grid;gap:10px;min-height:0;overflow-y:auto;padding-right:6px;scrollbar-gutter:stable}
.athlete-card{background:var(--panel-soft);border-radius:16px;padding:14px;display:grid;gap:10px;min-height:108px}
.athlete-card.active{background:#d1fae5}
.athlete-main{display:grid;gap:6px;text-align:left;background:transparent;padding:0}
.athlete-header{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;min-width:0}
.athlete-header strong{flex:1}
.empty-plan-hint{margin:0;font-size:14px}
.status-pill{padding:4px 8px;border-radius:999px;font-size:12px;font-weight:700;flex-shrink:0}
.status-pill.completed{background:#dcfce7;color:#166534}.status-pill.in_progress{background:#fef3c7;color:#92400e}.status-pill.not_started{background:#fee2e2;color:#b91c1c}.status-pill.no_plan{background:#e5e7eb;color:#4b5563}
.inline-plans{display:grid;gap:6px;padding-left:12px}
.inline-plan{display:flex;align-items:flex-start;gap:8px;text-align:left;font-size:14px;color:var(--muted);background:rgba(255,255,255,.45);border-radius:12px;padding:8px 10px}
.inline-plan.active{color:#0f766e;background:rgba(255,255,255,.92);font-weight:700}
.plan-dot{width:10px;height:10px;border-radius:999px;background:#9ca3af;flex-shrink:0;margin-top:4px}
.inline-plan.completed .plan-dot{background:#22c55e}.inline-plan.in_progress .plan-dot{background:#f59e0b}.inline-plan.not_started .plan-dot{background:#ef4444}
.date-input,.team-select{min-height:56px}.team-select{appearance:none}.section-title{margin:0;color:var(--muted)}
</style>
