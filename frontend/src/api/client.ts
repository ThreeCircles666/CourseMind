const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export interface RequestOptions extends RequestInit {
  skipAuthRefresh?: boolean
}

let accessToken: string | null = null
let refreshPromise: Promise<boolean> | null = null
let onUnauthorized: (() => void) | null = null

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function setUnauthorizedHandler(handler: (() => void) | null) {
  onUnauthorized = handler
}

async function refreshAccessToken(): Promise<boolean> {
  if (!refreshPromise) {
    refreshPromise = fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
      headers: { Accept: 'application/json' },
    })
      .then(async (response) => {
        if (!response.ok) return false
        const data = (await response.json()) as { access_token: string }
        accessToken = data.access_token
        return true
      })
      .catch(() => false)
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

export async function authenticatedFetch(
  path: string,
  options: RequestInit = {},
  retry = true,
): Promise<Response> {
  const headers = new Headers(options.headers)
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  })
  if (response.status === 401 && retry && (await refreshAccessToken())) {
    return authenticatedFetch(path, options, false)
  }
  if (response.status === 401) onUnauthorized?.()
  return response
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
  retry = true,
): Promise<T> {
  const headers = new Headers(options.headers)
  if (options.body) headers.set('Content-Type', 'application/json')
  headers.set('Accept', 'application/json')
  if (accessToken) headers.set('Authorization', `Bearer ${accessToken}`)
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers,
    credentials: 'include',
  })
  if (
    response.status === 401 &&
    retry &&
    !options.skipAuthRefresh &&
    (await refreshAccessToken())
  ) {
    return apiRequest<T>(path, { ...options, skipAuthRefresh: true }, false)
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { detail?: string }
    if (response.status === 401) onUnauthorized?.()
    throw new Error(body.detail ?? `请求失败：HTTP ${response.status}`)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export async function apiGet<T>(path: string, options: Pick<RequestOptions, 'signal'> = {}) {
  return apiRequest<T>(path, { method: 'GET', ...options })
}
