import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

const NORMAL_ATHLETE = 'E2E Normal Athlete'
const OFFLINE_ATHLETE = 'E2E Offline Athlete'
const TEMPLATE_NAME = 'E2E Offline Draft Template'
const FIRST_EXERCISE = 'E2E Squat'
const SECOND_EXERCISE = 'E2E Press'
const PASSWORD = 'e2e-password-123'
const backendUrl = process.env.E2E_BACKEND_URL || 'http://127.0.0.1:8011'

test.describe.configure({ mode: 'serial' })

test('training mode tablet viewports keep the recording panel usable', async ({ page }) => {
  const consoleErrors: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') {
      consoleErrors.push(message.text())
    }
  })

  await page.setViewportSize({ width: 1366, height: 1024 })
  await login(page)
  await openTrainingSession(page, NORMAL_ATHLETE)

  for (const viewport of [
    { width: 1366, height: 1024 },
    { width: 1180, height: 820 },
    { width: 1024, height: 768 },
    { width: 820, height: 1180 },
  ]) {
    await page.setViewportSize(viewport)
    await expectTrainingViewport(page, viewport)
  }

  expect(consoleErrors).toEqual([])
})

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

test('提交当前组后不等待后台同步即可继续录入下一组', async ({ page, request }) => {
  await login(page)
  await openTrainingSession(page, OFFLINE_ATHLETE)
  await itemCard(page, SECOND_EXERCISE).click()
  await expect(page.getByTestId('training-set-panel')).toHaveAttribute('data-current-exercise', SECOND_EXERCISE)

  let delayedSyncRequests = 0
  let delayedSyncResponses = 0
  await page.route('**/api/training/session-sync', async (route) => {
    delayedSyncRequests += 1
    await new Promise((resolve) => setTimeout(resolve, 3000))
    const response = await route.fetch()
    delayedSyncResponses += 1
    await route.fulfill({ response })
  })

  const secondExerciseCard = itemCard(page, SECOND_EXERCISE)
  const panel = page.getByTestId('training-set-panel')
  const submitButton = page.getByTestId('submit-current-set')

  await submitCurrentSet(page, { weight: 50, reps: 5, rir: 2 })
  expect(delayedSyncResponses).toBe(0)
  await expect(panel).not.toContainText('正在保存')
  await expect(secondExerciseCard).toHaveAttribute('data-record-count', '1')
  await expect(panel).toContainText('第 2 组 / 共 2 组')
  await expect(page.getByTestId('current-set-weight')).toBeEditable()
  await expect(page.getByTestId('current-set-reps')).toBeEditable()

  await page.getByTestId('current-set-weight').fill('52.5')
  await page.getByTestId('current-set-reps').fill('5')
  await page.locator('[data-testid="current-set-rir"][data-rir-value="3"]').click()
  await expect(page.locator('[data-testid="current-set-rir"][data-rir-value="3"]')).toHaveClass(/active/)
  await expect(submitButton).toBeEnabled()
  await submitButton.click()
  await expect(secondExerciseCard).toHaveAttribute('data-record-count', '2')

  await expect(page.getByTestId('training-sync-status')).toHaveAttribute('data-sync-status', 'synced', { timeout: 20000 })
  expect(delayedSyncRequests).toBeGreaterThanOrEqual(1)
  expect(delayedSyncResponses).toBe(delayedSyncRequests)
  await page.unroute('**/api/training/session-sync')
  await closeRpeModalIfVisible(page)

  await page.reload()
  await expect(page.getByTestId('training-sync-status')).toHaveAttribute('data-sync-status', 'synced')
  await expect(itemCard(page, SECOND_EXERCISE)).toHaveAttribute('data-record-count', '2')

  const session = await fetchCurrentSession(page, request)
  expect(countSetRecords(session)).toBe(4)
  expect(countSetRecordsForExercise(session, SECOND_EXERCISE)).toBe(2)
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

async function expectTrainingViewport(page: Page, viewport: { width: number; height: number }) {
  await expect(page).toHaveURL(/\/training-mode\/session/)
  await expect(page.locator('.training-topbar .auth-user-bar')).toHaveCount(0)
  await expect(page.getByTestId('training-set-panel')).toBeVisible()
  await expect(page.locator('[data-testid="current-set-rir"][data-rir-value="0"]')).toBeVisible()
  await expect(page.getByTestId('submit-current-set')).toBeVisible()
  await expect(page.getByTestId('current-set-weight-decrement')).toHaveText('-2.5')
  await expect(page.getByTestId('current-set-weight-increment')).toHaveText('+2.5')
  await expect(page.getByTestId('current-set-reps-decrement')).toHaveText('-1')
  await expect(page.getByTestId('current-set-reps-increment')).toHaveText('+1')

  await page.getByTestId('current-set-weight').fill('50')
  await page.getByTestId('current-set-weight-decrement').click()
  await expect(page.getByTestId('current-set-weight')).toHaveValue('47.5')
  await page.getByTestId('current-set-weight-increment').click()
  await expect(page.getByTestId('current-set-weight')).toHaveValue('50')
  await page.getByTestId('current-set-reps').fill('5')
  await page.getByTestId('current-set-reps-decrement').click()
  await expect(page.getByTestId('current-set-reps')).toHaveValue('4')
  await page.getByTestId('current-set-reps-increment').click()
  await expect(page.getByTestId('current-set-reps')).toHaveValue('5')

  const hasHorizontalOverflow = await page.evaluate(() => {
    const root = document.documentElement
    const body = document.body
    const shell = document.querySelector('.training-shell') as HTMLElement | null
    return (
      root.scrollWidth > root.clientWidth + 1
      || body.scrollWidth > body.clientWidth + 1
      || Boolean(shell && shell.scrollWidth > shell.clientWidth + 1)
    )
  })
  expect(hasHorizontalOverflow, `${viewport.width}x${viewport.height} should not overflow horizontally`).toBe(false)

  const boxes = await page.locator('.layout-sidebar, .layout-center, .layout-panel').evaluateAll((elements) => (
    elements.map((element) => {
      const rect = element.getBoundingClientRect()
      return {
        className: element.className,
        left: rect.left,
        top: rect.top,
        right: rect.right,
        bottom: rect.bottom,
        width: rect.width,
        height: rect.height,
      }
    })
  ))
  expect(boxes).toHaveLength(3)
  for (const box of boxes) {
    expect(box.width, `${viewport.width}x${viewport.height} ${box.className} width`).toBeGreaterThan(0)
    expect(box.height, `${viewport.width}x${viewport.height} ${box.className} height`).toBeGreaterThan(0)
    expect(box.left, `${viewport.width}x${viewport.height} ${box.className} left edge`).toBeGreaterThanOrEqual(0)
    expect(box.right, `${viewport.width}x${viewport.height} ${box.className} right edge`).toBeLessThanOrEqual(viewport.width + 1)
  }

  for (let leftIndex = 0; leftIndex < boxes.length; leftIndex += 1) {
    for (let rightIndex = leftIndex + 1; rightIndex < boxes.length; rightIndex += 1) {
      const first = boxes[leftIndex]
      const second = boxes[rightIndex]
      const xOverlap = Math.max(0, Math.min(first.right, second.right) - Math.max(first.left, second.left))
      const yOverlap = Math.max(0, Math.min(first.bottom, second.bottom) - Math.max(first.top, second.top))
      expect(
        xOverlap * yOverlap,
        `${viewport.width}x${viewport.height} ${first.className} overlaps ${second.className}`,
      ).toBeLessThanOrEqual(1)
    }
  }
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

function countSetRecordsForExercise(session: any, exerciseName: string) {
  const item = (session.items || []).find((current: any) => current.exercise?.name === exerciseName)
  return item?.records?.length || 0
}

function todayString() {
  const now = new Date()
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
