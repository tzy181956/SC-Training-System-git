import client from './client'

export async function fetchTags() {
  const { data } = await client.get('/tags')
  return data
}

export async function fetchGroupedTags() {
  const { data } = await client.get('/tags/grouped')
  return data
}

export async function createTag(payload: Record<string, unknown>) {
  const { data } = await client.post('/tags', payload)
  return data
}

export async function fetchExercises() {
  const { data } = await client.get('/exercises')
  return data
}

export async function createExercise(payload: Record<string, unknown>) {
  const { data } = await client.post('/exercises', payload)
  return data
}

export async function updateExercise(id: number, payload: Record<string, unknown>) {
  const { data } = await client.patch(`/exercises/${id}`, payload)
  return data
}
