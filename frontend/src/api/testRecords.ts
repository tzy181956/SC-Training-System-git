import client from './client'

type DangerousActionPayload = {
  confirmed: true
  actor_name?: string | null
  confirmation_text?: string | null
}

export async function fetchTestRecords() {
  const { data } = await client.get('/test-records')
  return data
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
