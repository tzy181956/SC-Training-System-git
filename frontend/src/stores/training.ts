import { defineStore } from 'pinia'
import { ref } from 'vue'

import {
  fetchSession,
  fetchTrainingAthletes,
  fetchTrainingPlans,
  startTrainingSession,
  submitSet,
  updateSetRecord,
} from '@/api/sessions'

export const useTrainingStore = defineStore('training', () => {
  const athletes = ref<any[]>([])
  const selectedAthleteId = ref<number>(0)
  const sessionDate = ref<string>('')
  const assignments = ref<any[]>([])
  const previewAssignmentId = ref<number>(0)
  const session = ref<any | null>(null)

  async function hydrateAthletes(targetDate = sessionDate.value) {
    athletes.value = await fetchTrainingAthletes(targetDate)
    const selectedStillExists = athletes.value.some((athlete) => athlete.id === selectedAthleteId.value)
    if (!selectedStillExists) {
      const preferredAthlete =
        athletes.value.find((athlete) => athlete.training_status !== 'no_plan') || athletes.value[0] || null
      selectedAthleteId.value = preferredAthlete?.id || 0
    }
  }

  async function loadPlans(athleteId: number, targetDate: string) {
    selectedAthleteId.value = athleteId
    sessionDate.value = targetDate
    const response = await fetchTrainingPlans(athleteId, targetDate)
    assignments.value = response.assignments
    previewAssignmentId.value = response.assignments[0]?.id || 0
    return response
  }

  async function openPlanSession(assignmentId: number, targetDate: string) {
    previewAssignmentId.value = assignmentId
    sessionDate.value = targetDate
    session.value = await startTrainingSession(assignmentId, targetDate)
    return session.value
  }

  async function loadSession(sessionId: number) {
    session.value = await fetchSession(sessionId)
    return session.value
  }

  async function recordSet(itemId: number, payload: Record<string, unknown>) {
    const response = await submitSet(itemId, payload)
    _replaceSession(response.session)
    await hydrateAthletes(sessionDate.value)
    return response
  }

  async function reviseSetRecord(recordId: number, payload: Record<string, unknown>) {
    const response = await updateSetRecord(recordId, payload)
    _replaceSession(response.session)
    await hydrateAthletes(sessionDate.value)
    return response
  }

  function setPreviewAssignment(assignmentId: number) {
    previewAssignmentId.value = assignmentId
  }

  function _replaceSession(nextSession: any) {
    session.value = nextSession
  }

  return {
    athletes,
    selectedAthleteId,
    sessionDate,
    assignments,
    previewAssignmentId,
    session,
    hydrateAthletes,
    loadPlans,
    openPlanSession,
    loadSession,
    recordSet,
    reviseSetRecord,
    setPreviewAssignment,
  }
})
