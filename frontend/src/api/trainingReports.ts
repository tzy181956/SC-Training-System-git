import client from './client'

type DangerousActionPayload = {
  confirmed: true
  actor_name?: string | null
  confirmation_text?: string | null
}

export async function fetchTrainingReport(params: {
  athlete_id: number
  date_from?: string
  date_to?: string
}) {
  const { data } = await client.get('/training-reports', { params })
  return data
}

export async function coachUpdateTrainingReportSetRecord(
  recordId: number,
  payload: {
    actual_weight: number
    actual_reps: number
    actual_rir: number
    notes?: string | null
    actor_name?: string | null
  },
) {
  const { data } = await client.patch(`/training-reports/set-records/${recordId}`, payload)
  return data
}

export async function coachAddTrainingReportSet(
  itemId: number,
  payload: {
    actual_weight: number
    actual_reps: number
    actual_rir: number
    notes?: string | null
    actor_name?: string | null
  },
) {
  const { data } = await client.post(`/training-reports/session-items/${itemId}/sets`, payload)
  return data
}

export async function coachDeleteTrainingReportSetRecord(recordId: number, payload: DangerousActionPayload) {
  const { data } = await client.delete(`/training-reports/set-records/${recordId}`, { data: payload })
  return data
}
