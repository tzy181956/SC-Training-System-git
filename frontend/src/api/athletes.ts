import client from './client'

type DangerousActionPayload = {
  confirmed: true
  actor_name?: string | null
  confirmation_text?: string | null
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

export async function fetchSports() {
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

export async function fetchTeams() {
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

export async function fetchAthletes() {
  const { data } = await client.get('/athletes')
  return data
}

export async function createAthlete(payload: Record<string, unknown>) {
  const { data } = await client.post('/athletes', payload)
  return data
}

export async function updateAthlete(id: number, payload: Record<string, unknown>) {
  const { data } = await client.patch(`/athletes/${id}`, payload)
  return data
}

export async function deleteAthlete(id: number, payload: DangerousActionPayload) {
  await client.delete(`/athletes/${id}`, { data: payload })
}
