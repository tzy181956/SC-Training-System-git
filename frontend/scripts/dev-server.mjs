import { mkdir, readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

import { createServer } from 'vite'

const scriptDir = path.dirname(fileURLToPath(import.meta.url))
const rootDir = path.resolve(scriptDir, '..')
const runtimeAccessFile = path.join(rootDir, 'public', 'runtime-access.json')
const runtimeAccessRoute = '/runtime-access.json'
const runtimeAccessContentType = 'application/json; charset=utf-8'
let latestRuntimeAccessPayload = ''

function getArgValue(name) {
  const flag = `--${name}`
  for (let index = 0; index < process.argv.length; index += 1) {
    const value = process.argv[index]
    if (value === flag) {
      return process.argv[index + 1]
    }
    if (value.startsWith(`${flag}=`)) {
      return value.slice(flag.length + 1)
    }
  }
  return undefined
}

function formatTimestamp(date = new Date()) {
  const parts = {
    year: date.getFullYear(),
    month: String(date.getMonth() + 1).padStart(2, '0'),
    day: String(date.getDate()).padStart(2, '0'),
    hour: String(date.getHours()).padStart(2, '0'),
    minute: String(date.getMinutes()).padStart(2, '0'),
    second: String(date.getSeconds()).padStart(2, '0'),
  }
  return `${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}:${parts.second}`
}

async function writeRuntimeAccess(accessUrl) {
  const resolvedUrl = new URL(accessUrl)
  const payload = {
    accessUrl,
    host: resolvedUrl.hostname,
    port: Number(resolvedUrl.port || (resolvedUrl.protocol === 'https:' ? 443 : 80)),
    generatedAt: formatTimestamp(),
    source: 'vite-dev-server',
  }
  latestRuntimeAccessPayload = `${JSON.stringify(payload, null, 2)}\n`

  await mkdir(path.dirname(runtimeAccessFile), { recursive: true })
  await writeFile(runtimeAccessFile, latestRuntimeAccessPayload, 'utf-8')
}

async function readRuntimeAccessPayload() {
  if (latestRuntimeAccessPayload) {
    return latestRuntimeAccessPayload
  }

  try {
    const payload = await readFile(runtimeAccessFile, 'utf-8')
    latestRuntimeAccessPayload = payload
    return payload
  } catch {
    return JSON.stringify(
      {
        accessUrl: '',
        host: '',
        port: 0,
        generatedAt: '',
        source: 'fallback',
      },
      null,
      2,
    )
  }
}

const runtimeAccessPlugin = {
  name: 'runtime-access-endpoint',
  configureServer(devServer) {
    devServer.middlewares.use(runtimeAccessRoute, async (_req, res, next) => {
      try {
        const payload = await readRuntimeAccessPayload()
        res.statusCode = 200
        res.setHeader('Content-Type', runtimeAccessContentType)
        res.setHeader('Cache-Control', 'no-store')
        res.end(payload)
      } catch (error) {
        next(error)
      }
    })
  },
}

const host = getArgValue('host') || process.env.FRONTEND_HOST || '0.0.0.0'
const port = Number(getArgValue('port') || process.env.FRONTEND_PORT || 5173)
const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000'

const server = await createServer({
  plugins: [runtimeAccessPlugin],
  root: rootDir,
  clearScreen: false,
  server: {
    host,
    port,
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
      },
    },
  },
})

await server.listen()

const accessUrl =
  server.resolvedUrls?.network?.[0]
  || server.resolvedUrls?.local?.[0]
  || `http://127.0.0.1:${port}/`

try {
  await writeRuntimeAccess(accessUrl)
  console.log(`[runtime-access] synced ${accessUrl}`)
} catch (error) {
  console.error('[runtime-access] failed to write runtime-access.json')
  console.error(error)
}

server.printUrls()
