import client from './client'

type DangerousActionPayload = {
  confirmed: true
  actor_name?: string | null
  confirmation_text?: string | null
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

export async function fetchTestRecords() {
  const { data } = await client.get('/test-records')
  return data
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
