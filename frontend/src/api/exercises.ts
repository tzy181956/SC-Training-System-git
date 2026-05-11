import client from './client'
import type { ExerciseListResponse } from '@/types/exerciseLibrary'

type DangerousActionPayload = {
  confirmed: true
  actor_name?: string | null
  confirmation_text?: string | null
}

export type FetchExercisesParams = {
  keyword?: string
  level1?: string
  level2?: string
  page?: number
  page_size?: number
  [key: string]: string | number | string[] | undefined
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

export async function fetchExercises(params: FetchExercisesParams = {}): Promise<ExerciseListResponse> {
  const { data } = await client.get('/exercises', { params })
  return data
}

export async function fetchAllExerciseListItems(pageSize = 100) {
  const firstPage = await fetchExercises({ page: 1, page_size: pageSize })
  const items = [...firstPage.items]

  for (let page = 2; page <= firstPage.total_pages; page += 1) {
    const nextPage = await fetchExercises({ page, page_size: pageSize })
    items.push(...nextPage.items)
  }

  return items
}

export async function fetchExercise(id: number) {
  const { data } = await client.get(`/exercises/${id}`)
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
