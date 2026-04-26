import { createRouter, createWebHistory } from 'vue-router'

import AthletesView from '@/views/AthletesView.vue'
import BackupsView from '@/views/BackupsView.vue'
import DashboardView from '@/views/DashboardView.vue'
import ExerciseLibraryView from '@/views/ExerciseLibraryView.vue'
import LoginView from '@/views/LoginView.vue'
import LogsView from '@/views/LogsView.vue'
import PlanAssignmentsView from '@/views/PlanAssignmentsView.vue'
import PlanTemplatesView from '@/views/PlanTemplatesView.vue'
import MonitorDashboardView from '@/views/MonitorDashboardView.vue'
import TestRecordsView from '@/views/TestRecordsView.vue'
import TrainingReportsView from '@/views/TrainingReportsView.vue'
import TrainingModeView from '@/views/TrainingModeView.vue'
import TrainingSessionView from '@/views/TrainingSessionView.vue'
import { useAuthStore } from '@/stores/auth'

const TRAINING_ROUTE_NAMES = new Set(['training-mode', 'training-session'])
const MANAGEMENT_ROUTE_NAMES = new Set([
  'dashboard',
  'athletes',
  'exercises',
  'plans',
  'assignments',
  'training-reports',
  'backups',
  'logs',
  'tests',
])
const MONITOR_ROUTE_NAMES = new Set(['monitor-dashboard'])

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
    { path: '/monitor', name: 'monitor-dashboard', component: MonitorDashboardView },
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

  const routeName = typeof to.name === 'string' ? to.name : ''
  if (TRAINING_ROUTE_NAMES.has(routeName) && authStore.currentMode !== 'training') {
    authStore.setMode('training')
  } else if (MANAGEMENT_ROUTE_NAMES.has(routeName) && authStore.currentMode !== 'management') {
    authStore.setMode('management')
  } else if (MONITOR_ROUTE_NAMES.has(routeName) && authStore.currentMode !== 'monitor') {
    authStore.setMode('monitor')
  }

  return true
})

export default router
