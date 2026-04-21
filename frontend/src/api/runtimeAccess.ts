export interface RuntimeAccessInfo {
  accessUrl: string
  host: string
  port: number
  generatedAt: string
  source: 'startup-script' | 'fallback'
}

function buildFallback(): RuntimeAccessInfo {
  return {
    accessUrl: window.location.origin,
    host: window.location.hostname,
    port: Number(window.location.port || (window.location.protocol === 'https:' ? 443 : 80)),
    generatedAt: '',
    source: 'fallback',
  }
}

export async function fetchRuntimeAccessInfo(): Promise<RuntimeAccessInfo> {
  const fallback = buildFallback()

  try {
    const response = await fetch(`/runtime-access.json?t=${Date.now()}`, { cache: 'no-store' })
    if (!response.ok) return fallback
    const data = (await response.json()) as Partial<RuntimeAccessInfo>
    if (!data.accessUrl || !data.host || !data.port) return fallback
    return {
      accessUrl: data.accessUrl,
      host: data.host,
      port: data.port,
      generatedAt: data.generatedAt || '',
      source: data.source === 'startup-script' ? 'startup-script' : 'fallback',
    }
  } catch {
    return fallback
  }
}
