import client from './client'

export async function fetchPlanTemplates() {
  const { data } = await client.get('/plan-templates')
  return data
}

export async function createPlanTemplate(payload: Record<string, unknown>) {
  const { data } = await client.post('/plan-templates', payload)
  return data
}

export async function updatePlanTemplate(id: number, payload: Record<string, unknown>) {
  const { data } = await client.patch(`/plan-templates/${id}`, payload)
  return data
}

export async function deletePlanTemplate(id: number) {
  const { data } = await client.delete(`/plan-templates/${id}`)
  return data
}

export async function addPlanTemplateItem(templateId: number, payload: Record<string, unknown>) {
  const { data } = await client.post(`/plan-templates/${templateId}/items`, payload)
  return data
}

export async function updatePlanTemplateItem(itemId: number, payload: Record<string, unknown>) {
  const { data } = await client.patch(`/plan-templates/items/${itemId}`, payload)
  return data
}

export async function deletePlanTemplateItem(itemId: number) {
  const { data } = await client.delete(`/plan-templates/items/${itemId}`)
  return data
}

export async function fetchAssignments() {
  const { data } = await client.get('/assignments')
  return data
}

export async function previewBatchAssignments(payload: Record<string, unknown>) {
  const { data } = await client.post('/assignments/preview', payload)
  return data
}

export async function createBatchAssignments(payload: Record<string, unknown>) {
  const { data } = await client.post('/assignments/batch', payload)
  return data
}

export async function cancelBatchAssignments(assignmentIds: number[]) {
  const { data } = await client.post('/assignments/cancel-batch', { assignment_ids: assignmentIds })
  return data
}

export async function fetchAssignmentOverview(targetDate: string) {
  const { data } = await client.get('/assignments/overview', { params: { target_date: targetDate } })
  return data
}
