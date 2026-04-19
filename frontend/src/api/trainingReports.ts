import client from './client'

export async function fetchTrainingReport(params: {
  athlete_id: number
  date_from?: string
  date_to?: string
}) {
  const { data } = await client.get('/training-reports', { params })
  return data
}
