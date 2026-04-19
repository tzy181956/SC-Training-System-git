import client from './client'

export async function fetchTrainingAthletes(sessionDate?: string) {
  const { data } = await client.get('/training/athletes', { params: { session_date: sessionDate } })
  return data
}

export async function fetchTrainingPlans(athleteId: number, sessionDate?: string) {
  const { data } = await client.get('/training/plans', { params: { athlete_id: athleteId, session_date: sessionDate } })
  return data
}

export async function startTrainingSession(assignmentId: number, sessionDate?: string) {
  const { data } = await client.post(`/training/plans/${assignmentId}/session`, null, { params: { session_date: sessionDate } })
  return data
}

export async function fetchSession(sessionId: number) {
  const { data } = await client.get(`/training/sessions/${sessionId}`)
  return data
}

export async function submitSet(itemId: number, payload: Record<string, unknown>) {
  const { data } = await client.post(`/training/session-items/${itemId}/sets`, payload)
  return data
}

export async function updateSetRecord(recordId: number, payload: Record<string, unknown>) {
  const { data } = await client.patch(`/training/set-records/${recordId}`, payload)
  return data
}
