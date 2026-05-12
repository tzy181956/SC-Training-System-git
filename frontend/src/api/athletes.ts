import client from './client'

type DangerousActionPayload = {
  confirmed: true
  actor_name?: string | null
  confirmation_text?: string | null
}

export type SportRead = {
  id: number
  name: string
  code: string
  notes?: string | null
}

export type TeamRead = {
  id: number
  sport_id: number
  name: string
  code: string
  notes?: string | null
  sport?: SportRead | null
}

export type AthleteRead = {
  id: number
  code: string
  user_id?: number | null
  sport_id?: number | null
  team_id?: number | null
  full_name: string
  birth_date?: string | null
  age?: number | null
  gender?: string | null
  position?: string | null
  height?: number | null
  weight?: number | null
  body_fat_percentage?: number | null
  wingspan?: number | null
  standing_reach?: number | null
  notes?: string | null
  is_active?: boolean
  sport?: SportRead | null
  team?: TeamRead | null
}

export type AthletePayload = {
  code?: string | null
  user_id?: number | null
  sport_id?: number | null
  team_id?: number | null
  full_name: string
  birth_date?: string | null
  gender?: string | null
  position?: string | null
  height?: number | null
  weight?: number | null
  body_fat_percentage?: number | null
  wingspan?: number | null
  standing_reach?: number | null
  notes?: string | null
  is_active?: boolean
}

type SportPayload = {
  name: string
  code: string
  notes?: string | null
}

type TeamPayload = {
  sport_id: number
  name: string
  code: string
  notes?: string | null
}

export async function fetchSports(): Promise<SportRead[]> {
  const { data } = await client.get('/sports')
  return data
}

export async function createSport(payload: SportPayload) {
  const { data } = await client.post('/sports', payload)
  return data
}

export async function deleteSport(id: number, payload: DangerousActionPayload) {
  await client.delete(`/sports/${id}`, { data: payload })
}

export async function fetchTeams(): Promise<TeamRead[]> {
  const { data } = await client.get('/teams')
  return data
}

export async function createTeam(payload: TeamPayload) {
  const { data } = await client.post('/teams', payload)
  return data
}

export async function deleteTeam(id: number, payload: DangerousActionPayload) {
  await client.delete(`/teams/${id}`, { data: payload })
}

export async function fetchAthletes(): Promise<AthleteRead[]> {
  const { data } = await client.get('/athletes')
  return data
}

export async function createAthlete(payload: AthletePayload): Promise<AthleteRead> {
  const { data } = await client.post('/athletes', payload)
  return data
}

export async function updateAthlete(id: number, payload: Partial<AthletePayload>): Promise<AthleteRead> {
  const { data } = await client.patch(`/athletes/${id}`, payload)
  return data
}

export async function deleteAthlete(id: number, payload: DangerousActionPayload) {
  await client.delete(`/athletes/${id}`, { data: payload })
}
