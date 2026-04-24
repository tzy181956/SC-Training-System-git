import client from './client'

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
