import { defineStore } from 'pinia'
import { ref } from 'vue'

import { fetchAthletes, fetchSports, fetchTeams, type AthleteRead, type SportRead, type TeamRead } from '@/api/athletes'

export const useAthletesStore = defineStore('athletes', () => {
  const athletes = ref<AthleteRead[]>([])
  const sports = ref<SportRead[]>([])
  const teams = ref<TeamRead[]>([])

  async function hydrate() {
    ;[athletes.value, sports.value, teams.value] = await Promise.all([fetchAthletes(), fetchSports(), fetchTeams()])
  }

  return { athletes, sports, teams, hydrate }
})
