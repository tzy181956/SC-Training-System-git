import client from './client'

export async function fetchSports() {
  const { data } = await client.get('/sports')
  return data
}

export async function fetchTeams() {
  const { data } = await client.get('/teams')
  return data
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
