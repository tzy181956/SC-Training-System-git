import client from './client'

export async function fetchTestRecords() {
  const { data } = await client.get('/test-records')
  return data
}

export async function createTestRecord(payload: Record<string, unknown>) {
  const { data } = await client.post('/test-records', payload)
  return data
}
