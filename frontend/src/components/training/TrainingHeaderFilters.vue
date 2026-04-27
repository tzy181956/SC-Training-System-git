<script setup lang="ts">
import { computed } from 'vue'

type TeamOption = {
  id: string
  name: string
}

const props = withDefaults(
  defineProps<{
    sessionDate: string
    sessionDateLabel: string
    selectedSportValue?: string
    selectedSportLabel?: string
    sportOptions?: TeamOption[]
    sportFieldLabel?: string
    sportAriaLabel?: string
    selectedTeamValue: string
    selectedTeamLabel: string
    teamOptions: TeamOption[]
    teamFieldLabel?: string
    teamAriaLabel?: string
  }>(),
  {
    selectedSportValue: undefined,
    selectedSportLabel: '项目',
    sportOptions: () => [],
    sportFieldLabel: '项目',
    sportAriaLabel: '项目筛选',
    teamFieldLabel: '队伍',
    teamAriaLabel: '队伍筛选',
  },
)

const emit = defineEmits<{
  'update:sessionDate': [value: string]
  'update:sportValue': [value: string]
  'update:teamValue': [value: string]
}>()

const hasSportFilter = computed(() => props.selectedSportValue !== undefined)

function handleDateInput(event: Event) {
  emit('update:sessionDate', (event.target as HTMLInputElement).value)
}

function handleSportInput(event: Event) {
  emit('update:sportValue', (event.target as HTMLSelectElement).value)
}

function handleTeamInput(event: Event) {
  emit('update:teamValue', (event.target as HTMLSelectElement).value)
}
</script>

<template>
  <div class="training-header-filters" :class="{ 'training-header-filters--triple': hasSportFilter }">
    <div class="training-header-filter">
      <span class="training-header-filter-label">训练日期</span>
      <div class="training-header-filter-shell">
        <button class="training-header-filter-pill" type="button" tabindex="-1" aria-hidden="true">
          <span class="training-header-filter-pill-text">{{ sessionDateLabel }}</span>
        </button>
        <input
          :value="sessionDate"
          class="training-header-filter-control training-header-filter-native"
          type="date"
          aria-label="训练日期"
          title="训练日期"
          @input="handleDateInput"
        />
      </div>
    </div>

    <div v-if="hasSportFilter" class="training-header-filter">
      <span class="training-header-filter-label">{{ sportFieldLabel }}</span>
      <div class="training-header-filter-shell">
        <button class="training-header-filter-pill" type="button" tabindex="-1" aria-hidden="true">
          <span class="training-header-filter-pill-text">{{ selectedSportLabel }}</span>
        </button>
        <select
          :value="selectedSportValue"
          class="training-header-filter-control training-header-filter-native"
          :aria-label="sportAriaLabel"
          :title="sportAriaLabel"
          @change="handleSportInput"
        >
          <option v-for="sport in props.sportOptions" :key="sport.id" :value="sport.id">{{ sport.name }}</option>
        </select>
      </div>
    </div>

    <div class="training-header-filter">
      <span class="training-header-filter-label">{{ teamFieldLabel }}</span>
      <div class="training-header-filter-shell">
        <button class="training-header-filter-pill" type="button" tabindex="-1" aria-hidden="true">
          <span class="training-header-filter-pill-text">{{ selectedTeamLabel }}</span>
        </button>
        <select
          :value="selectedTeamValue"
          class="training-header-filter-control training-header-filter-native"
          :aria-label="teamAriaLabel"
          :title="teamAriaLabel"
          @change="handleTeamInput"
        >
          <option v-for="team in props.teamOptions" :key="team.id" :value="team.id">{{ team.name }}</option>
        </select>
      </div>
    </div>
  </div>
</template>

<style scoped>
.training-header-filters {
  --training-header-filter-current-width: var(--training-filter-width);
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: var(--training-filter-gap);
  min-width: 0;
  max-width: 100%;
  overflow: hidden;
}

.training-header-filter {
  display: block;
  flex: 0 0 auto;
  width: var(--training-header-filter-current-width);
  min-width: 0;
  max-width: 100%;
}

.training-header-filters--triple {
  --training-header-filter-current-width: var(--training-filter-width-triple, 146px);
}

.training-header-filter-shell {
  position: relative;
  width: 100%;
}

.training-header-filter-label {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.training-header-filter-control {
  display: inline-block;
  width: 100%;
  min-width: 0;
  max-width: 100%;
}

.training-header-filter-native {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  min-height: 100%;
  margin: 0;
  border: 0;
  opacity: 0;
  cursor: pointer;
  appearance: none;
  -webkit-appearance: none;
}

.training-header-filter-pill {
  width: 100%;
  min-width: 0;
  max-width: 100%;
  height: var(--training-filter-height);
  min-height: var(--training-filter-height);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 var(--training-filter-padding-inline);
  border: 1px solid var(--line);
  border-radius: 14px;
  background: white;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  box-sizing: border-box;
  color: var(--text);
  pointer-events: none;
}

.training-header-filter-pill-text {
  display: block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: var(--training-filter-font-size);
  font-weight: 500;
  line-height: 1;
  text-align: center;
  white-space: nowrap;
}

.training-header-filter-shell:focus-within .training-header-filter-pill {
  border-color: rgba(15, 118, 110, 0.42);
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.12);
}

@media (max-width: 767px) {
  .training-header-filters {
    flex-direction: column;
    align-items: stretch;
    overflow: visible;
  }

  .training-header-filter {
    display: grid;
    gap: 4px;
    width: 100%;
    flex-basis: auto;
  }

  .training-header-filter-label {
    position: static;
    width: auto;
    height: auto;
    padding: 0;
    margin: 0;
    overflow: visible;
    clip: auto;
    white-space: normal;
    font-size: 12px;
    line-height: 1.1;
    color: var(--text-soft);
  }
}
</style>
