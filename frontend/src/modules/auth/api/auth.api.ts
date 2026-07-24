import type { SystemStatusData, LoginData, UserSummary } from '@/contracts'
import { apiGet, apiPost } from '@/services/http/client'

export function getSystemStatus(): Promise<SystemStatusData> {
  return apiGet<SystemStatusData>('/system/status')
}

export function initSystem(
  username: string,
  password: string,
): Promise<{ admin: UserSummary }> {
  return apiPost<{ admin: UserSummary }>('/system/init', { username, password })
}

export function login(
  username: string,
  password: string,
): Promise<LoginData> {
  return apiPost<LoginData>('/system/login', { username, password })
}

export function logout(): Promise<null> {
  return apiPost<null>('/system/logout')
}
