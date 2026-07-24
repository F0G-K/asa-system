import type { SystemConfigData, UpdateConfigBody } from '@asa/contracts'
import { apiGet, apiPut } from '@/services/http/client'

export function getSystemConfig(): Promise<SystemConfigData> {
  return apiGet<SystemConfigData>('/system/config')
}

export function updateSystemConfig(
  data: UpdateConfigBody,
): Promise<SystemConfigData> {
  return apiPut<SystemConfigData>('/system/config', data)
}
