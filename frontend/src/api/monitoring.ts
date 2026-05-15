import type { MonitoringAthleteDetailResponse, MonitoringTodayResponse } from '@/types/monitoring'

import client from './client'

export type FetchMonitoringTodayParams = {
  session_date: string
  sport_id?: number | null
  team_id?: number | null
  include_unassigned?: boolean
  force_refresh?: boolean
}

export type FetchMonitoringAthleteDetailParams = {
  session_date: string
  athlete_id: number
}

export async function fetchMonitoringToday(params: FetchMonitoringTodayParams) {
  const { data } = await client.get<MonitoringTodayResponse>('/monitoring/today', { params })
  return data
}

export async function fetchMonitoringAthleteDetail(params: FetchMonitoringAthleteDetailParams) {
  const { data } = await client.get<MonitoringAthleteDetailResponse>('/monitoring/athlete-detail', { params })
  return data
}
