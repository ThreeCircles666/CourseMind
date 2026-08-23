const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

export interface RequestOptions {
  signal?: AbortSignal
}

export async function apiGet<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const url = `${API_BASE_URL}${path}`
  const response = await fetch(url, {
    method: 'GET',
    headers: { Accept: 'application/json' },
    signal: options.signal,
  })

  if (!response.ok) {
    throw new Error(`请求失败：HTTP ${response.status}`)
  }

  return (await response.json()) as T
}
