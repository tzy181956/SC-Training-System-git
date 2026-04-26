import type { MonitoringTodayResponse } from '@/types/monitoring'

import client from './client'

export type FetchMonitoringTodayParams = {
  session_date: string
  team_id?: number | null
  include_unassigned?: boolean
}

export async function fetchMonitoringToday(params: FetchMonitoringTodayParams) {
  const { data } = await client.get<MonitoringTodayResponse>('/monitoring/today', { params })
  return data
}
