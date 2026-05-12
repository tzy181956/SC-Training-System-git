export type ScopedSportSource = number | null | undefined

export type TeamWithSport = {
  id: number
  sport_id?: number | null
}

export type AthleteWithScope = {
  sport_id?: number | null
  team_id?: number | null
}

export function resolveScopedSportId(source: ScopedSportSource) {
  return typeof source === 'number' && source > 0 ? source : null
}

export function isSportScoped(source: ScopedSportSource) {
  return resolveScopedSportId(source) !== null
}

export function resolveInitialSportFilterValue(source: ScopedSportSource) {
  return resolveScopedSportId(source) ?? 0
}

export function filterTeamsBySport<T extends TeamWithSport>(teams: T[], sportId: number | null | undefined) {
  if (!sportId) return [] as T[]
  return teams.filter((team) => team.sport_id === sportId)
}

export function retainVisibleTeamId<T extends { id: number }>(teamId: number | null | undefined, teams: T[]) {
  if (!teamId) return 0
  return teams.some((team) => team.id === teamId) ? teamId : 0
}

export function filterAthletesBySportAndTeam<T extends AthleteWithScope>(
  athletes: T[],
  sportId: number | null | undefined,
  teamId: number | null | undefined,
) {
  return athletes.filter((athlete) => {
    if (sportId && athlete.sport_id !== sportId) return false
    if (teamId && athlete.team_id !== teamId) return false
    return true
  })
}
