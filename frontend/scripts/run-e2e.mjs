import { spawn } from 'node:child_process'
import { existsSync, rmSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontendDir = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const repoDir = resolve(frontendDir, '..')
const backendDir = join(repoDir, 'backend')
const dbBaseName = 'tmp_e2e_training_offline_draft.db'
const dbPath = join(backendDir, dbBaseName)
const backendPort = process.env.E2E_BACKEND_PORT || '8011'
const frontendPort = process.env.E2E_FRONTEND_PORT || '5174'
const backendUrl = `http://127.0.0.1:${backendPort}`
const frontendUrl = `http://127.0.0.1:${frontendPort}`
const pythonExe = join(backendDir, '.venv', 'Scripts', 'python.exe')
const nodeExe = process.execPath
const viteCli = join(frontendDir, 'node_modules', 'vite', 'bin', 'vite.js')
const playwrightCli = join(frontendDir, 'node_modules', 'playwright', 'cli.js')
const playwrightArtifactDirs = [
  join(frontendDir, 'test-results'),
  join(frontendDir, 'playwright-report'),
  join(frontendDir, 'blob-report'),
]

const e2eEnv = {
  ...process.env,
  APP_ENV: 'development',
  SECRET_KEY: 'e2e-training-secret',
  DATABASE_URL: `sqlite:///./${dbBaseName}`,
  ALEMBIC_DATABASE_URL: `sqlite:///./${dbBaseName}`,
  PYTHONIOENCODING: 'utf-8',
}

const children = []

function cleanupDatabase() {
  for (const suffix of ['', '-wal', '-shm']) {
    const target = `${dbPath}${suffix}`
    if (existsSync(target)) {
      rmSync(target, { force: true })
    }
  }
}

function cleanupPlaywrightArtifacts() {
  for (const target of playwrightArtifactDirs) {
    if (existsSync(target)) {
      rmSync(target, { recursive: true, force: true })
    }
  }
}

function cleanupRuntimeFiles() {
  cleanupDatabase()
  cleanupPlaywrightArtifacts()
}

function run(command, args, options = {}) {
  return new Promise((resolvePromise, rejectPromise) => {
    const child = spawn(command, args, {
      cwd: options.cwd || repoDir,
      env: options.env || process.env,
      stdio: options.stdio || 'inherit',
      shell: false,
    })
    child.on('exit', (code) => {
      if (code === 0) {
        resolvePromise()
        return
      }
      rejectPromise(new Error(`${command} ${args.join(' ')} exited with ${code}`))
    })
    child.on('error', rejectPromise)
  })
}

function start(command, args, options = {}) {
  const child = spawn(command, args, {
    cwd: options.cwd || repoDir,
    env: options.env || process.env,
    stdio: 'inherit',
    shell: false,
  })
  children.push(child)
  return child
}

async function waitFor(url, label) {
  const deadline = Date.now() + 30000
  let lastError = null
  while (Date.now() < deadline) {
    try {
      const response = await fetch(url)
      if (response.ok) return
      lastError = new Error(`${label} returned ${response.status}`)
    } catch (error) {
      lastError = error
    }
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 500))
  }
  throw new Error(`Timed out waiting for ${label}: ${lastError?.message || 'no response'}`)
}

async function stopChildren() {
  for (const child of [...children].reverse()) {
    if (!child.killed && child.exitCode === null) {
      child.kill()
    }
  }
  await new Promise((resolvePromise) => setTimeout(resolvePromise, 1200))
}

async function main() {
  cleanupRuntimeFiles()
  try {
    await run(pythonExe, ['scripts/migrate_db.py', 'ensure'], { cwd: backendDir, env: e2eEnv })
    await run(pythonExe, ['scripts/seed_e2e_training_offline_draft.py'], { cwd: backendDir, env: e2eEnv })

    start(pythonExe, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', backendPort], {
      cwd: backendDir,
      env: e2eEnv,
    })
    await waitFor(`${backendUrl}/ready/deep`, 'backend ready/deep')

    start(nodeExe, [viteCli, '--host', '127.0.0.1', '--port', frontendPort, '--strictPort'], {
      cwd: frontendDir,
      env: {
        ...process.env,
        VITE_API_PROXY_TARGET: backendUrl,
      },
    })
    await waitFor(frontendUrl, 'frontend dev server')

    await run(nodeExe, [playwrightCli, 'test', '--config', 'playwright.config.ts'], {
      cwd: frontendDir,
      env: {
        ...process.env,
        E2E_BASE_URL: frontendUrl,
        E2E_BACKEND_URL: backendUrl,
      },
    })
  } finally {
    await stopChildren()
    cleanupRuntimeFiles()
  }
}

main().catch((error) => {
  console.error(error)
  process.exitCode = 1
})
