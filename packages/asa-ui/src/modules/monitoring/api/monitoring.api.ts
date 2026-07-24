import type {
  PaginatedResponse,
  CursorResponse,
  StageItem,
  WorkerTask,
  ChatMessage,
  RuntimeLog,
  ResourceResponse,
} from '@asa/contracts'
import { apiGet } from '@/services/http/client'

export function getStages(projectId: string): Promise<{ items: StageItem[] }> {
  return apiGet<{ items: StageItem[] }>(`/projects/${projectId}/stages`)
}

export interface WorkerListParams {
  page?: number
  page_size?: number
  stage_id?: string
  worker_role?: string
  task_status?: string
  sort?: string
}

export function getWorkers(
  projectId: string,
  params?: WorkerListParams,
): Promise<PaginatedResponse<WorkerTask>> {
  return apiGet<PaginatedResponse<WorkerTask>>(
    `/projects/${projectId}/workers`,
    params as Record<string, unknown>,
  )
}

export interface MessageCursorParams {
  cursor?: number
  limit?: number
  stage_id?: string
  worker_role?: string
  message_type?: string
}

export function getMessages(
  projectId: string,
  params?: MessageCursorParams,
): Promise<CursorResponse<ChatMessage>> {
  return apiGet<CursorResponse<ChatMessage>>(
    `/projects/${projectId}/messages`,
    params as Record<string, unknown>,
  )
}

export interface LogCursorParams {
  cursor?: number
  limit?: number
  log_level?: string
  stage_id?: string
  order?: 'asc' | 'desc'
}

export function getLogs(
  projectId: string,
  params?: LogCursorParams,
): Promise<CursorResponse<RuntimeLog>> {
  return apiGet<CursorResponse<RuntimeLog>>(
    `/projects/${projectId}/logs`,
    params as Record<string, unknown>,
  )
}

export interface ResourceCursorParams {
  cursor?: number
  limit?: number
}

export function getResources(
  projectId: string,
  params?: ResourceCursorParams,
): Promise<ResourceResponse> {
  return apiGet<ResourceResponse>(
    `/projects/${projectId}/resources`,
    params as Record<string, unknown>,
  )
}
