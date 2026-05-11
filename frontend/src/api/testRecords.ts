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
