import { apiGet, type RequestOptions } from './client'

export interface HealthResponse {
  status: string
  service: string
  version: string
}

export function fetchHealth(options?: RequestOptions): Promise<HealthResponse> {
  return apiGet<HealthResponse>('/api/v1/health', options)
}
