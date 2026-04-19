import { defineStore } from 'pinia'
import { ref } from 'vue'

import { fetchAssignments, fetchPlanTemplates } from '@/api/plans'

export const usePlansStore = defineStore('plans', () => {
  const templates = ref<any[]>([])
  const assignments = ref<any[]>([])

  async function hydrate() {
    ;[templates.value, assignments.value] = await Promise.all([fetchPlanTemplates(), fetchAssignments()])
  }

  return { templates, assignments, hydrate }
})
