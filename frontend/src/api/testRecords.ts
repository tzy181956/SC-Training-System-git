import client from './client'

type DangerousActionPayload = {
  confirmed: true
  actor_name?: string | null
  confirmation_text?: string | null
}

export type TestRecordLibraryQuery = {
  athlete_keyword?: string
  metric_keyword?: string
  test_type?: string
  page?: number
  page_size?: number
}

export type TestRecordLibraryItem = {
  id: number
  athlete_id: number
  test_date: string
  test_type: string
  metric_name: string
  result_value: number
  result_text?: string | null
  unit: string
  notes?: string | null
  athlete?: {
    id: number
    full_name: string
    team?: { id?: number | null; name?: string | null } | null
    sport?: { id?: number | null; name?: string | null } | null
  } | null
}

export type TestRecordLibraryResponse = {
  items: TestRecordLibraryItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type TestMetricDefinitionSummary = {
  id: number
  test_type_id: number
  name: string
  code: string
  default_unit?: string | null
  is_lower_better: boolean
  direction: 'higher' | 'lower'
  notes?: string | null
}

export type TestTypeDefinitionSummary = {
  id: number
  name: string
  code: string
  sport_id?: number | null
  sport_name?: string | null
  is_system: boolean
  notes?: string | null
}

export type TestTypeDefinitionRead = TestTypeDefinitionSummary & {
  metrics: TestMetricDefinitionSummary[]
}

export type TestMetricDefinitionRead = TestMetricDefinitionSummary & {
  test_type?: TestTypeDefinitionSummary | null
}

export type ScoreDimensionMetricWrite = {
  id?: number | null
  test_metric_definition_id: number
  weight: number
  sort_order: number
}

export type ScoreDimensionWrite = {
  id?: number | null
  name: string
  sort_order: number
  weight: number
  metrics: ScoreDimensionMetricWrite[]
}

export type ScoreProfileRead = {
  id: number
  name: string
  sport_id?: number | null
  team_id?: number | null
  notes?: string | null
  is_active: boolean
  dimensions: Array<{
    id: number
    name: string
    sort_order: number
    weight: number
    metrics: Array<{
      id: number
      test_metric_definition_id: number
      weight: number
      sort_order: number
      test_metric_definition: TestMetricDefinitionSummary
    }>
  }>
}

export type ScoreProfilePayload = {
  name: string
  sport_id?: number | null
  team_id?: number | null
  notes?: string | null
  is_active?: boolean
  dimensions: ScoreDimensionWrite[]
}

export type ScoreCalculationPayload = {
  score_profile_id: number
  team_id: number
  date_from: string
  date_to: string
  baseline_mode: 'current_batch' | 'historical_pool'
}

export type ScoreCalculationResponse = {
  score_mode: string
  baseline_mode: 'current_batch' | 'historical_pool'
  baseline_label: string
  score_explanation: string
  profile: ScoreProfileRead
  ranking: Array<{
    athlete_id: number
    athlete_name: string
    team_id?: number | null
    team_name?: string | null
    overall_score?: number | null
    missing_metrics: string[]
    warnings: string[]
    dimension_scores: Array<{
      dimension_id: number
      dimension_name: string
      score?: number | null
      warnings: string[]
      metrics: Array<{
        metric_definition_id: number
        metric_name: string
        test_type_name: string
        is_lower_better: boolean
        raw_value?: number | null
        raw_test_date?: string | null
        mean?: number | null
        sd?: number | null
        z?: number | null
        standard_score?: number | null
        weight?: number | null
        is_missing: boolean
        sample_insufficient: boolean
        zero_variance: boolean
        outlier_warning: boolean
        warnings: string[]
      }>
    }>
  }>
  team_average_dimensions: Array<{
    dimension_id: number
    dimension_name: string
    score?: number | null
  }>
  warnings: string[]
}

type TestTypeDefinitionPayload = {
  name: string
  code: string
  sport_id?: number | null
  notes?: string | null
}

type TestMetricDefinitionPayload = {
  test_type_id: number
  name: string
  code: string
  default_unit?: string | null
  is_lower_better?: boolean
  notes?: string | null
}

export async function fetchTestRecords(params?: TestRecordLibraryQuery): Promise<TestRecordLibraryResponse> {
  const { data } = await client.get('/test-records', { params })
  return data
}

export async function fetchAllTestRecords(pageSize = 100): Promise<TestRecordLibraryItem[]> {
  const firstPage = await fetchTestRecords({ page: 1, page_size: pageSize })
  const items = [...firstPage.items]

  for (let page = 2; page <= firstPage.total_pages; page += 1) {
    const nextPage = await fetchTestRecords({ page, page_size: pageSize })
    items.push(...nextPage.items)
  }

  return items
}

export async function fetchTestDefinitions(): Promise<{ types: TestTypeDefinitionRead[] }> {
  const { data } = await client.get('/test-definitions')
  return data
}

export async function createTestTypeDefinition(payload: TestTypeDefinitionPayload): Promise<TestTypeDefinitionRead> {
  const { data } = await client.post('/test-definitions/types', payload)
  return data
}

export async function updateTestTypeDefinition(
  id: number,
  payload: Partial<TestTypeDefinitionPayload>,
): Promise<TestTypeDefinitionRead> {
  const { data } = await client.patch(`/test-definitions/types/${id}`, payload)
  return data
}

export async function deleteTestTypeDefinition(id: number, payload: DangerousActionPayload) {
  await client.delete(`/test-definitions/types/${id}`, { data: payload })
}

export async function createTestMetricDefinition(payload: TestMetricDefinitionPayload): Promise<TestMetricDefinitionRead> {
  const { data } = await client.post('/test-definitions/metrics', payload)
  return data
}

export async function updateTestMetricDefinition(
  id: number,
  payload: Partial<TestMetricDefinitionPayload>,
): Promise<TestMetricDefinitionRead> {
  const { data } = await client.patch(`/test-definitions/metrics/${id}`, payload)
  return data
}

export async function deleteTestMetricDefinition(id: number, payload: DangerousActionPayload) {
  await client.delete(`/test-definitions/metrics/${id}`, { data: payload })
}

export async function createTestRecord(payload: Record<string, unknown>) {
  const { data } = await client.post('/test-records', payload)
  return data
}

export async function importTestRecords(file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await client.post('/test-records/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function downloadTestRecordTemplate() {
  const { data } = await client.get('/test-records/template', { responseType: 'blob' })
  return data
}

export async function exportTestRecordLibrary() {
  const { data } = await client.get('/test-records/export', { responseType: 'blob' })
  return data
}

export async function deleteTestRecordsBatch(recordIds: number[], payload: DangerousActionPayload) {
  const { data } = await client.post('/test-records/delete-batch', {
    record_ids: recordIds,
    ...payload,
  })
  return data
}

export async function deleteFilteredTestRecords(
  filters: {
    athlete_keyword?: string
    metric_keyword?: string
    test_type?: string
  },
  payload: DangerousActionPayload,
) {
  const { data } = await client.post('/test-records/delete-filtered', {
    ...filters,
    ...payload,
  })
  return data
}

export async function fetchScoreProfiles(): Promise<ScoreProfileRead[]> {
  const { data } = await client.get('/test-scores/profiles')
  return data
}

export async function createScoreProfile(payload: ScoreProfilePayload): Promise<ScoreProfileRead> {
  const { data } = await client.post('/test-scores/profiles', payload)
  return data
}

export async function updateScoreProfile(id: number, payload: Partial<ScoreProfilePayload>): Promise<ScoreProfileRead> {
  const { data } = await client.patch(`/test-scores/profiles/${id}`, payload)
  return data
}

export async function deleteScoreProfile(id: number, payload: DangerousActionPayload) {
  await client.delete(`/test-scores/profiles/${id}`, { data: payload })
}

export async function calculateTestScores(payload: ScoreCalculationPayload): Promise<ScoreCalculationResponse> {
  const { data } = await client.post('/test-scores/calculate', payload)
  return data
}
