import client from './client'

export type TrainingLoadSession = {
  session_id: number
  session_date: string
  status: string
  session_rpe: number | null
  session_duration_minutes: number | null
  session_srpe_load: number | null
}

export type TrainingLoadDaily = {
  load_date: string
  session_count: number
  total_duration_minutes: number
  total_srpe_load: number
}

export type TrainingLoadMetrics = {
  formula_status: 'pending'
  acwr: number | null
  monotony: number | null
  strain: number | null
}

export type AthleteTrainingLoadResponse = {
  athlete: {
    id: number
    full_name: string
  }
  date_range: {
    date_from: string
    date_to: string
  }
  sessions: TrainingLoadSession[]
  daily_loads: TrainingLoadDaily[]
  metrics: TrainingLoadMetrics
}

export async function fetchAthleteTrainingLoads(params: {
  athlete_id: number
  date_from?: string
  date_to?: string
}) {
  const { athlete_id, ...query } = params
  const { data } = await client.get<AthleteTrainingLoadResponse>(`/training-loads/athletes/${athlete_id}`, {
    params: query,
  })
  return data
}
