import { computed, ref, type Ref } from 'vue'

export type TeamFilterAthlete = {
  id: number
  team?: {
    id?: number | null
    name?: string | null
  } | null
}

export type TeamFilterOption = {
  id: string
  name: string
}

export const ALL_TEAMS_VALUE = '__all__'
export const UNASSIGNED_TEAM_VALUE = '__unassigned__'

export function useTeamFilter<T extends TeamFilterAthlete>(params: {
  athletes: () => T[]
  selectedAthleteId?: Ref<number>
}) {
  const selectedTeamFilter = ref(ALL_TEAMS_VALUE)
  const athleteList = computed(() => params.athletes() || [])

  const teamOptions = computed<TeamFilterOption[]>(() => {
    const teams = athleteList.value
      .filter((athlete) => athlete.team?.id)
      .map((athlete) => ({
        id: String(athlete.team?.id),
        name: athlete.team?.name || '未命名队伍',
      }))

    const uniqueTeams = teams.filter((team, index, source) => source.findIndex((current) => current.id === team.id) === index)
    const hasUnassignedAthletes = athleteList.value.some((athlete) => !athlete.team?.id)
    const options = [...uniqueTeams]

    if (hasUnassignedAthletes) {
      options.push({ id: UNASSIGNED_TEAM_VALUE, name: '未分队' })
    }

    if (options.length <= 1) {
      return options
    }

    return [{ id: ALL_TEAMS_VALUE, name: '全部队伍' }, ...options]
  })

  const selectedTeamLabel = computed(() => {
    const matched = teamOptions.value.find((team) => team.id === selectedTeamFilter.value)
    return matched?.name || '队伍'
  })

  const filteredAthletes = computed(() => {
    if (selectedTeamFilter.value === ALL_TEAMS_VALUE) {
      return athleteList.value
    }

    if (selectedTeamFilter.value === UNASSIGNED_TEAM_VALUE) {
      return athleteList.value.filter((athlete) => !athlete.team?.id)
    }

    return athleteList.value.filter((athlete) => String(athlete.team?.id || '') === selectedTeamFilter.value)
  })

  function syncTeamFilter() {
    const options = teamOptions.value
    if (!options.length) {
      selectedTeamFilter.value = ALL_TEAMS_VALUE
      return
    }

    const currentExists = options.some((option) => option.id === selectedTeamFilter.value)
    if (currentExists) return

    selectedTeamFilter.value = options.length === 1 ? options[0].id : ALL_TEAMS_VALUE
  }

  function syncSelectedAthleteForFilter(onEmpty?: () => void) {
    if (!params.selectedAthleteId) return

    const visibleAthletes = filteredAthletes.value
    if (!visibleAthletes.length) {
      onEmpty?.()
      return
    }

    const selectedStillVisible = visibleAthletes.some((athlete) => athlete.id === params.selectedAthleteId?.value)
    if (!selectedStillVisible) {
      params.selectedAthleteId.value = visibleAthletes[0].id
    }
  }

  return {
    selectedTeamFilter,
    teamOptions,
    selectedTeamLabel,
    filteredAthletes,
    syncTeamFilter,
    syncSelectedAthleteForFilter,
  }
}
