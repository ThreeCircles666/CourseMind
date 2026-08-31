import { apiRequest } from './client'

export interface User {
  id: number
  username: string
  nickname: string
}

interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export function register(username: string, nickname: string, password: string) {
  return apiRequest<AuthResponse>('/api/v1/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, nickname, password }),
  })
}

export function login(username: string, password: string) {
  return apiRequest<AuthResponse>('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

export function refresh() {
  return apiRequest<AuthResponse>('/api/v1/auth/refresh', { method: 'POST', skipAuthRefresh: true })
}

export function fetchMe() {
  return apiRequest<User>('/api/v1/auth/me')
}

export function logout() {
  return apiRequest<void>('/api/v1/auth/logout', { method: 'POST' })
}
