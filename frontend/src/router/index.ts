import { createRouter, createWebHistory } from 'vue-router'

import AthletesView from '@/views/AthletesView.vue'
import BackupsView from '@/views/BackupsView.vue'
import DashboardView from '@/views/DashboardView.vue'
import ExerciseLibraryView from '@/views/ExerciseLibraryView.vue'
import LoginView from '@/views/LoginView.vue'
import LogsView from '@/views/LogsView.vue'
import MonitorDashboardView from '@/views/MonitorDashboardView.vue'
import PlanAssignmentsView from '@/views/PlanAssignmentsView.vue'
import PlanTemplatesView from '@/views/PlanTemplatesView.vue'
import TestRecordsView from '@/views/TestRecordsView.vue'
import TrainingModeView from '@/views/TrainingModeView.vue'
import TrainingReportsView from '@/views/TrainingReportsView.vue'
import TrainingSessionView from '@/views/TrainingSessionView.vue'
import UsersView from '@/views/UsersView.vue'
import pinia from '@/stores/pinia'
import { resolveRouteForMode, useAuthStore } from '@/stores/auth'
import type { AppMode, UserRoleCode } from '@/types/auth'

const ADMIN_ONLY_ROLES: UserRoleCode[] = ['admin']
const COACH_AND_ADMIN_ROLES: UserRoleCode[] = ['admin', 'coach']
const TRAINING_ACCESS_ROLES: UserRoleCode[] = ['admin', 'coach', 'training']

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: { name: 'login' } },
    {
      path: '/login',
      name: 'login',
      component: LoginView,
      meta: { publicOnly: true },
    },
    {
      path: '/management',
      name: 'dashboard',
      component: DashboardView,
      meta: { requiresAuth: true, mode: 'management', allowedRoles: COACH_AND_ADMIN_ROLES },
    },
    {
      path: '/athletes',
      name: 'athletes',
      component: AthletesView,
      meta: { requiresAuth: true, mode: 'management', allowedRoles: COACH_AND_ADMIN_ROLES },
    },
    {
      path: '/exercises',
      name: 'exercises',
      component: ExerciseLibraryView,
      meta: { requiresAuth: true, mode: 'management', allowedRoles: COACH_AND_ADMIN_ROLES },
    },
    {
      path: '/plans',
      name: 'plans',
      component: PlanTemplatesView,
      meta: { requiresAuth: true, mode: 'management', allowedRoles: COACH_AND_ADMIN_ROLES },
    },
    {
      path: '/assignments',
      name: 'assignments',
      component: PlanAssignmentsView,
      meta: { requiresAuth: true, mode: 'management', allowedRoles: COACH_AND_ADMIN_ROLES },
    },
    {
      path: '/training-reports',
      name: 'training-reports',
      component: TrainingReportsView,
      meta: { requiresAuth: true, mode: 'management', allowedRoles: COACH_AND_ADMIN_ROLES },
    },
    {
      path: '/backups',
      name: 'backups',
      component: BackupsView,
      meta: { requiresAuth: true, mode: 'management', allowedRoles: ADMIN_ONLY_ROLES },
    },
    {
      path: '/logs',
      name: 'logs',
      component: LogsView,
      meta: { requiresAuth: true, mode: 'management', allowedRoles: ADMIN_ONLY_ROLES },
    },
    {
      path: '/tests',
      name: 'tests',
      component: TestRecordsView,
      meta: { requiresAuth: true, mode: 'management', allowedRoles: COACH_AND_ADMIN_ROLES },
    },
    {
      path: '/users',
      name: 'users',
      component: UsersView,
      meta: { requiresAuth: true, mode: 'management', allowedRoles: ADMIN_ONLY_ROLES },
    },
    {
      path: '/monitor',
      name: 'monitor-dashboard',
      component: MonitorDashboardView,
      meta: { requiresAuth: true, mode: 'monitor', allowedRoles: COACH_AND_ADMIN_ROLES },
    },
    {
      path: '/training-mode',
      name: 'training-mode',
      component: TrainingModeView,
      meta: { requiresAuth: true, mode: 'training', allowedRoles: TRAINING_ACCESS_ROLES },
    },
    {
      path: '/training-mode/session/:sessionId?',
      name: 'training-session',
      component: TrainingSessionView,
      meta: { requiresAuth: true, mode: 'training', allowedRoles: TRAINING_ACCESS_ROLES },
    },
  ],
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore(pinia)
  await authStore.bootstrap()

  if (to.meta.publicOnly) {
    if (authStore.isAuthenticated) {
      return authStore.homeRoute
    }
    return true
  }

  if (!to.meta.requiresAuth) {
    return true
  }

  if (!authStore.isAuthenticated) {
    return {
      name: 'login',
      query: to.fullPath && to.fullPath !== '/' ? { redirect: to.fullPath } : undefined,
    }
  }

  const allowedRoles = (to.meta.allowedRoles || []) as UserRoleCode[]
  if (allowedRoles.length && (!authStore.roleCode || !allowedRoles.includes(authStore.roleCode))) {
    return authStore.homeRoute
  }

  const routeMode = to.meta.mode as AppMode | undefined
  if (routeMode === 'management' && authStore.roleCode === 'coach') {
    authStore.refreshManagementUnlock()
    if (!authStore.isManagementUnlocked) {
      authStore.setPendingManagementPath(to.fullPath)
      const safeMode = (
        authStore.currentMode !== 'management'
        && authStore.canUseMode(authStore.currentMode)
      )
        ? authStore.currentMode
        : 'training'
      return resolveRouteForMode(safeMode)
    }
  }

  if (routeMode) {
    authStore.syncModeFromRoute(routeMode)
  }

  return true
})

export default router
