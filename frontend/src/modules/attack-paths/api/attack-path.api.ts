import type { PaginatedResponse, AttackPathSummary, AttackPathDetail } from '@/contracts'
import { apiGet } from '@/services/http/client'

export interface PathListParams {
  page?: number
  page_size?: number
  keyword?: string
  sort?: string
}

export function listAttackPaths(
  projectId: string,
  params?: PathListParams,
): Promise<PaginatedResponse<AttackPathSummary>> {
  return apiGet<PaginatedResponse<AttackPathSummary>>(
    `/projects/${projectId}/attack-paths`,
    params as Record<string, unknown>,
  )
}

export function getAttackPathDetail(
  projectId: string,
  pathId: string,
): Promise<AttackPathDetail> {
  return apiGet<AttackPathDetail>(
    `/projects/${projectId}/attack-paths/${pathId}`,
  )
}
