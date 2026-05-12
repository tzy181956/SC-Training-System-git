import { computed, ref, type Ref } from 'vue'

import { useAuthStore } from '@/stores/auth'

export type TeamFilterAthlete = {
  id: number
  sport?: {
    id?: number | null
    name?: string | null
  } | null
  team?: {
    id?: number | null
    name?: string | null
  } | null
}

export type TeamFilterOption = {
  id: string
  name: string
}

export const ALL_SPORTS_VALUE = '__all_sports__'
export const UNASSIGNED_SPORT_VALUE = '__unassigned_sport__'
export const ALL_TEAMS_VALUE = '__all__'
export const UNASSIGNED_TEAM_VALUE = '__unassigned__'

export function useTeamFilter<T extends TeamFilterAthlete>(params: {
  athletes: () => T[]
  selectedAthleteId?: Ref<number>
}) {
  const authStore = useAuthStore()
  const selectedSportFilter = ref(ALL_SPORTS_VALUE)
  const selectedTeamFilter = ref(ALL_TEAMS_VALUE)
  const athleteList = computed(() => params.athletes() || [])
  const scopedSportFilterValue = computed(() => {
    const sportId = authStore.currentUser?.sport_id
    return typeof sportId === 'number' && sportId > 0 ? String(sportId) : ''
  })
  const isSportLocked = computed(() => Boolean(scopedSportFilterValue.value))
  const hasExplicitSportSelection = computed(() => selectedSportFilter.value !== ALL_SPORTS_VALUE)

  const sportOptions = computed<TeamFilterOption[]>(() => {
    const sports = athleteList.value
      .filter((athlete) => athlete.sport?.id)
      .map((athlete) => ({
        id: String(athlete.sport?.id),
        name: athlete.sport?.name || '未命名项目',
      }))

    const uniqueSports = sports.filter((sport, index, source) => source.findIndex((current) => current.id === sport.id) === index)
    const hasUnassignedSports = athleteList.value.some((athlete) => !athlete.sport?.id)
    const options = [...uniqueSports]

    if (hasUnassignedSports) {
      options.push({ id: UNASSIGNED_SPORT_VALUE, name: '未分项目' })
    }

    if (isSportLocked.value) {
      const scopedOption = options.find((option) => option.id === scopedSportFilterValue.value)
      return [scopedOption || { id: scopedSportFilterValue.value, name: '当前项目' }]
    }

    return [{ id: ALL_SPORTS_VALUE, name: '全部项目' }, ...options]
  })

  const selectedSportLabel = computed(() => {
    const matched = sportOptions.value.find((sport) => sport.id === selectedSportFilter.value)
    return matched?.name || '项目'
  })

  const sportFilteredAthletes = computed(() => {
    if (selectedSportFilter.value === ALL_SPORTS_VALUE) {
      return athleteList.value
    }

    if (selectedSportFilter.value === UNASSIGNED_SPORT_VALUE) {
      return athleteList.value.filter((athlete) => !athlete.sport?.id)
    }

    return athleteList.value.filter((athlete) => String(athlete.sport?.id || '') === selectedSportFilter.value)
  })

  const teamOptions = computed<TeamFilterOption[]>(() => {
    if (!hasExplicitSportSelection.value) {
      return [{ id: ALL_TEAMS_VALUE, name: '全部队伍' }]
    }

    const teams = sportFilteredAthletes.value
      .filter((athlete) => athlete.team?.id)
      .map((athlete) => ({
        id: String(athlete.team?.id),
        name: athlete.team?.name || '未命名队伍',
      }))

    const uniqueTeams = teams.filter((team, index, source) => source.findIndex((current) => current.id === team.id) === index)
    const hasUnassignedAthletes = sportFilteredAthletes.value.some((athlete) => !athlete.team?.id)
    const options = [...uniqueTeams]

    if (hasUnassignedAthletes) {
      options.push({ id: UNASSIGNED_TEAM_VALUE, name: '未分队' })
    }

    return [{ id: ALL_TEAMS_VALUE, name: '全部队伍' }, ...options]
  })

  const selectedTeamLabel = computed(() => {
    const matched = teamOptions.value.find((team) => team.id === selectedTeamFilter.value)
    return matched?.name || '队伍'
  })

  const filteredAthletes = computed(() => {
    if (selectedTeamFilter.value === ALL_TEAMS_VALUE) {
      return sportFilteredAthletes.value
    }

    if (selectedTeamFilter.value === UNASSIGNED_TEAM_VALUE) {
      return sportFilteredAthletes.value.filter((athlete) => !athlete.team?.id)
    }

    return sportFilteredAthletes.value.filter((athlete) => String(athlete.team?.id || '') === selectedTeamFilter.value)
  })

  function syncSportFilter() {
    if (isSportLocked.value) {
      selectedSportFilter.value = scopedSportFilterValue.value
      return
    }

    const options = sportOptions.value
    if (!options.length) {
      selectedSportFilter.value = ALL_SPORTS_VALUE
      return
    }

    const currentExists = options.some((option) => option.id === selectedSportFilter.value)
    if (currentExists) return

    selectedSportFilter.value = ALL_SPORTS_VALUE
  }

  function syncTeamFilter() {
    if (!hasExplicitSportSelection.value) {
      selectedTeamFilter.value = ALL_TEAMS_VALUE
      return
    }

    const options = teamOptions.value
    if (!options.length) {
      selectedTeamFilter.value = ALL_TEAMS_VALUE
      return
    }

    const currentExists = options.some((option) => option.id === selectedTeamFilter.value)
    if (currentExists) return

    selectedTeamFilter.value = ALL_TEAMS_VALUE
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
    selectedSportFilter,
    sportOptions,
    selectedSportLabel,
    selectedTeamFilter,
    teamOptions,
    selectedTeamLabel,
    filteredAthletes,
    isSportLocked,
    syncSportFilter,
    syncTeamFilter,
    syncSelectedAthleteForFilter,
  }
}
