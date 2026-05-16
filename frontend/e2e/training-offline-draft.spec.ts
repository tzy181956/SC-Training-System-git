import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

const NORMAL_ATHLETE = 'E2E Normal Athlete'
const OFFLINE_ATHLETE = 'E2E Offline Athlete'
const TEMPLATE_NAME = 'E2E Offline Draft Template'
const FIRST_EXERCISE = 'E2E Squat'
const SECOND_EXERCISE = 'E2E Press'
const PASSWORD = 'e2e-password-123'
const backendUrl = process.env.E2E_BACKEND_URL || 'http://127.0.0.1:8011'

test.describe.configure({ mode: 'serial' })

test('normal training entry completes and appears in reports and monitoring', async ({ page, request }) => {
  await login(page)
  await openTrainingSession(page, NORMAL_ATHLETE)

  await submitCurrentSet(page, { weight: 50, reps: 5, rir: 2 })
  await submitCurrentSet(page, { weight: 52.5, reps: 5, rir: 2 })
  await expect(itemCard(page, FIRST_EXERCISE)).toHaveAttribute('data-record-count', '2')

  await itemCard(page, SECOND_EXERCISE).click()
  await submitCurrentSet(page, { weight: 40, reps: 5, rir: 3 })
  await submitCurrentSet(page, { weight: 42.5, reps: 5, rir: 2 })

  await expect(page.getByTestId('training-session-status')).toHaveAttribute('data-session-status', 'completed')
  await expect(page.getByTestId('training-sync-status')).toHaveAttribute('data-sync-status', 'synced')
  await closeRpeModalIfVisible(page)

  const session = await fetchCurrentSession(page, request)
  expect(countSetRecords(session)).toBe(4)

  await page.goto(`/training-reports?athleteId=${session.athlete_id}&dateFrom=${todayString()}&dateTo=${todayString()}`)
  await expect(page.getByTestId('training-report-session-list')).toBeVisible()
  await expect(page.getByTestId('training-report-session-card').first()).toHaveAttribute('data-session-status', 'completed')

  await page.goto('/monitor')
  await page.getByTestId('monitor-refresh-settings-toggle').click()
  await page.getByTestId('monitor-manual-refresh').click()
  const monitorCard = monitoringCard(page, NORMAL_ATHLETE)
  await expect(monitorCard).toBeVisible()
  await expect(monitorCard).toHaveAttribute('data-session-status', 'completed')
})

test('offline pending draft survives refresh without being overwritten by stale remote session', async ({ page, request }) => {
  await login(page)
  await openTrainingSession(page, OFFLINE_ATHLETE)

  await submitCurrentSet(page, { weight: 50, reps: 5, rir: 2 })
  await expect(page.getByTestId('training-sync-status')).toHaveAttribute('data-sync-status', 'synced')
  expect(countSetRecords(await fetchCurrentSession(page, request))).toBe(1)

  await failIncrementalSync(page)
  await submitCurrentSet(page, { weight: 55, reps: 5, rir: 1 }, { waitForRecordCount: false })

  await expect(page.getByTestId('training-sync-status')).toHaveAttribute('data-sync-status', 'pending')
  let draft = await latestPendingDraft(page)
  expect(draft?.sync_status).toBe('pending')
  expect(draft?.recorded_sets).toBeGreaterThanOrEqual(2)
  expect(draft?.pending_operations?.length).toBeGreaterThanOrEqual(1)

  await page.reload()
  await expect(page.getByTestId('training-sync-status')).toHaveAttribute('data-sync-status', 'pending')
  await expect(itemCard(page, FIRST_EXERCISE)).toHaveAttribute('data-record-count', '2')

  draft = await latestPendingDraft(page)
  expect(draft?.sync_status).toBe('pending')
  expect(draft?.recorded_sets).toBeGreaterThanOrEqual(2)
  expect(draft?.pending_operations?.length).toBeGreaterThanOrEqual(1)
  expect(countSetRecords(await fetchCurrentSession(page, request))).toBe(1)
})

test('restored pending draft syncs after network recovery and survives refresh', async ({ page, request }) => {
  await login(page)
  await openTrainingSession(page, OFFLINE_ATHLETE)

  await failIncrementalSync(page)
  await submitCurrentSet(page, { weight: 57.5, reps: 5, rir: 1 }, { waitForRecordCount: false })
  await expect(page.getByTestId('training-sync-status')).toHaveAttribute('data-sync-status', 'pending')
  const draft = await latestPendingDraft(page)
  expect(draft?.recorded_sets).toBeGreaterThanOrEqual(2)

  await page.unroute('**/api/training/session-sync')
  const manualSync = page.getByTestId('manual-full-sync')
  if (await manualSync.isVisible()) {
    await manualSync.click()
  }

  await expect(page.getByTestId('training-sync-status')).toHaveAttribute('data-sync-status', 'synced', { timeout: 10000 })
  expect(countSetRecords(await fetchCurrentSession(page, request))).toBe(2)

  await page.reload()
  await expect(page.getByTestId('training-sync-status')).toHaveAttribute('data-sync-status', 'synced')
  await expect(itemCard(page, FIRST_EXERCISE)).toHaveAttribute('data-record-count', '2')
})

async function login(page: Page) {
  await page.goto('/login')
  await page.locator('input[autocomplete="username"]').fill('e2e_admin')
  await page.locator('input[autocomplete="current-password"]').fill(PASSWORD)
  await page.locator('form button[type="submit"]').click()
  await expect(page).not.toHaveURL(/\/login/)
}

async function openTrainingSession(page: Page, athleteName: string) {
  await page.goto('/training-mode')
  const plan = page.locator(`[data-testid="training-plan-card"][data-athlete-name="${athleteName}"][data-template-name="${TEMPLATE_NAME}"]`)
  await expect(plan).toHaveCount(1)
  await expect(plan).toBeVisible()
  const openSessionResponse = page.waitForResponse((response) => (
    response.request().method() === 'POST'
    && response.url().includes('/api/training/plans/')
    && response.url().includes('/session')
    && response.ok()
  ))
  await plan.click()
  await openSessionResponse
  await expect(page).toHaveURL(/\/training-mode\/session/, { timeout: 10000 })
  await expect(itemCard(page, FIRST_EXERCISE)).toBeVisible()
  if ((await page.getByTestId('training-set-panel').getAttribute('data-current-exercise')) !== FIRST_EXERCISE) {
    await itemCard(page, FIRST_EXERCISE).click()
  }
  await expect(page.getByTestId('training-set-panel')).toHaveAttribute('data-current-exercise', FIRST_EXERCISE, { timeout: 10000 })
}

async function submitCurrentSet(
  page: Page,
  payload: { weight: number; reps: number; rir: number },
  options: { waitForRecordCount?: boolean } = {},
) {
  const waitForRecordCount = options.waitForRecordCount ?? true
  const panel = page.getByTestId('training-set-panel')
  const exerciseName = await panel.getAttribute('data-current-exercise')
  expect(exerciseName).toBeTruthy()
  const activeItemCard = itemCard(page, exerciseName as string)
  const previousCount = Number(await activeItemCard.getAttribute('data-record-count')) || 0
  await page.getByTestId('current-set-weight').fill(String(payload.weight))
  await page.getByTestId('current-set-reps').fill(String(payload.reps))
  await page.locator(`[data-testid="current-set-rir"][data-rir-value="${payload.rir}"]`).click()
  await page.getByTestId('submit-current-set').click()
  if (waitForRecordCount) {
    await expect(activeItemCard).toHaveAttribute('data-record-count', String(previousCount + 1))
  }
}

async function failIncrementalSync(page: Page) {
  await page.route('**/api/training/session-sync', async (route) => {
    await route.abort('failed')
  })
}

function itemCard(page: Page, exerciseName: string) {
  return page.getByTestId('session-item-card').filter({ hasText: exerciseName }).first()
}

function monitoringCard(page: Page, athleteName: string) {
  return page.locator(`[data-testid="monitoring-athlete-card"][data-athlete-name="${athleteName}"]`).first()
}

async function closeRpeModalIfVisible(page: Page) {
  const modal = page.getByTestId('session-rpe-modal')
  if (await modal.isVisible().catch(() => false)) {
    await page.getByTestId('session-rpe-later').click()
  }
}

async function latestPendingDraft(page: Page) {
  return page.evaluate(() => {
    const drafts = []
    for (let index = 0; index < window.localStorage.length; index += 1) {
      const key = window.localStorage.key(index)
      if (!key?.startsWith('training-local-draft:')) continue
      const raw = window.localStorage.getItem(key)
      if (!raw) continue
      drafts.push(JSON.parse(raw))
    }
    return drafts
      .filter((draft) => draft.sync_status === 'pending' || draft.pending_sync)
      .sort((left, right) => String(right.last_modified_at).localeCompare(String(left.last_modified_at)))[0] || null
  })
}

async function fetchCurrentSession(page: Page, request: APIRequestContext) {
  await expect(page).toHaveURL(/\/training-mode\/session\/\d+/)
  const sessionId = Number(new URL(page.url()).pathname.split('/').filter(Boolean).pop())
  expect(Number.isInteger(sessionId)).toBeTruthy()
  const token = await page.evaluate(() => window.localStorage.getItem('training-platform-access-token'))
  expect(token).toBeTruthy()
  const response = await request.get(`${backendUrl}/api/training/sessions/${sessionId}`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  expect(response.ok()).toBeTruthy()
  return response.json()
}

function countSetRecords(session: any) {
  return (session.items || []).reduce((total: number, item: any) => total + (item.records?.length || 0), 0)
}

function todayString() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
