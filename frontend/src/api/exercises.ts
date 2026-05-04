import client from './client'

type DangerousActionPayload = {
  confirmed: true
  actor_name?: string | null
  confirmation_text?: string | null
}

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

export async function fetchExerciseFacets() {
  const { data } = await client.get('/exercises/facets')
  return data
}

export async function fetchExerciseCategoriesTree() {
  const { data } = await client.get('/exercise-categories/tree')
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

export async function deleteExercise(id: number, payload: DangerousActionPayload) {
  await client.delete(`/exercises/${id}`, { data: payload })
}
