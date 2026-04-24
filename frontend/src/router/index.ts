import { createRouter, createWebHistory } from 'vue-router'

import AthletesView from '@/views/AthletesView.vue'
import BackupsView from '@/views/BackupsView.vue'
import DashboardView from '@/views/DashboardView.vue'
import ExerciseLibraryView from '@/views/ExerciseLibraryView.vue'
import LoginView from '@/views/LoginView.vue'
import LogsView from '@/views/LogsView.vue'
import PlanAssignmentsView from '@/views/PlanAssignmentsView.vue'
import PlanTemplatesView from '@/views/PlanTemplatesView.vue'
import TestRecordsView from '@/views/TestRecordsView.vue'
import TrainingReportsView from '@/views/TrainingReportsView.vue'
import TrainingModeView from '@/views/TrainingModeView.vue'
import TrainingSessionView from '@/views/TrainingSessionView.vue'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: () => useAuthStore().homeRoute },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/management', name: 'dashboard', component: DashboardView },
    { path: '/athletes', name: 'athletes', component: AthletesView },
    { path: '/exercises', name: 'exercises', component: ExerciseLibraryView },
    { path: '/plans', name: 'plans', component: PlanTemplatesView },
    { path: '/assignments', name: 'assignments', component: PlanAssignmentsView },
    { path: '/training-reports', name: 'training-reports', component: TrainingReportsView },
    { path: '/backups', name: 'backups', component: BackupsView },
    { path: '/logs', name: 'logs', component: LogsView },
    { path: '/tests', name: 'tests', component: TestRecordsView },
    { path: '/training-mode', name: 'training-mode', component: TrainingModeView },
    {
      path: '/training-mode/session/:sessionId?',
      name: 'training-session',
      component: TrainingSessionView,
    },
  ],
})

router.beforeEach((to) => {
  const authStore = useAuthStore()

  if (to.name === 'login') {
    return authStore.homeRoute
  }

  return true
})

export default router
