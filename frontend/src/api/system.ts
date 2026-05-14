import client from './client'

export type ServerTimeResponse = {
  server_time: string
  timezone: string
  utc_offset_minutes: number
}

export type DashboardMemoResponse = {
  content: string
  updated_at: string | null
}

export async function fetchServerTime() {
  const { data } = await client.get<ServerTimeResponse>('/system/server-time')
  return data
}

export async function fetchDashboardMemo() {
  const { data } = await client.get<DashboardMemoResponse>('/system/dashboard-memo')
  return data
}

export async function updateDashboardMemo(content: string) {
  const { data } = await client.put<DashboardMemoResponse>('/system/dashboard-memo', { content })
  return data
}
