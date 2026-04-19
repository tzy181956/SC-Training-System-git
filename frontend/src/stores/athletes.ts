import { defineStore } from 'pinia'
import { ref } from 'vue'

import { fetchAthletes, fetchSports, fetchTeams } from '@/api/athletes'

export const useAthletesStore = defineStore('athletes', () => {
  const athletes = ref<any[]>([])
  const sports = ref<any[]>([])
  const teams = ref<any[]>([])

  async function hydrate() {
    ;[athletes.value, sports.value, teams.value] = await Promise.all([fetchAthletes(), fetchSports(), fetchTeams()])
  }

  return { athletes, sports, teams, hydrate }
})
