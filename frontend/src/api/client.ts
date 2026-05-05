import axios from 'axios'

import { clearStoredAuthState, getStoredAccessToken } from '@/utils/authStorage'

const apiBaseUrl =
  import.meta.env.VITE_API_BASE_URL ||
  '/api'

function buildLoginPath() {
  const basePath = (import.meta.env.BASE_URL || '/').replace(/\/+$/, '')
  return `${basePath || ''}/login`
}

const client = axios.create({
  baseURL: apiBaseUrl,
})

client.interceptors.request.use((config) => {
  const token = getStoredAccessToken()
  if (!token) return config

  config.headers = config.headers || {}
  config.headers.Authorization = `Bearer ${token}`
  return config
})

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const statusCode = error.response?.status
    const requestUrl = String(error.config?.url || '')
    const isAuthRequest = requestUrl.includes('/auth/login') || requestUrl.includes('/auth/me')

    if (statusCode === 401 && !isAuthRequest) {
      clearStoredAuthState()
      if (window.location.pathname !== buildLoginPath()) {
        window.location.replace(buildLoginPath())
      }
    }

    return Promise.reject(error)
  },
)

export default client
