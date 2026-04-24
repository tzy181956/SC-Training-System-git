import client from './client'

export interface LogItem {
  id: number
  source_type: string
  action_type: string
  object_type: string
  object_id: number | null
  object_label: string | null
  summary: string
  actor_name: string
  occurred_at: string
  team_id: number | null
  team_name: string | null
  athlete_id: number | null
  athlete_name: string | null
  session_id: number | null
  session_date: string | null
  status: string | null
  before_snapshot: Record<string, unknown> | null
  after_snapshot: Record<string, unknown> | null
  extra_context: Record<string, unknown> | null
}

export interface LogListResponse {
  items: LogItem[]
  available_object_types: string[]
}

export async function fetchLogs(params: {
  date_from?: string
  date_to?: string
  actor_name?: string
  object_type?: string
  limit?: number
}) {
  const { data } = await client.get<LogListResponse>('/logs', { params })
  return data
}
