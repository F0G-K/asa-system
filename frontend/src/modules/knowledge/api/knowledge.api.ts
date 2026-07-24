import type {
  PaginatedResponse,
  KnowledgeEntrySummary,
  KnowledgeEntryDetail,
  KnowledgeSearchData,
  KnowledgeRetrievalRecord,
  CreateKnowledgeEntryBody,
  UpdateKnowledgeEntryBody,
  KnowledgeSearchBody,
} from '@/contracts'
import { apiGet, apiPost, apiPut, apiDelete } from '@/services/http/client'

// ===== 查询参数 =====

export interface KnowledgeEntryListParams {
  page?: number
  page_size?: number
  knowledge_type?: string
  entry_status?: string
  risk_level?: string
  language?: string
  keyword?: string
  tags?: string[]
  sort?: string
}

export interface KnowledgeRetrievalListParams {
  page?: number
  page_size?: number
  stage_id?: string
  worker_task_id?: string
  retrieval_type?: string
  sort?: string
}

// ===== 知识条目 CRUD =====

export function listKnowledgeEntries(
  params?: KnowledgeEntryListParams,
): Promise<PaginatedResponse<KnowledgeEntrySummary>> {
  return apiGet<PaginatedResponse<KnowledgeEntrySummary>>(
    '/knowledge/entries',
    params as Record<string, unknown>,
  )
}

export function createKnowledgeEntry(
  data: CreateKnowledgeEntryBody,
): Promise<KnowledgeEntryDetail> {
  return apiPost<KnowledgeEntryDetail>('/knowledge/entries', data)
}

export function getKnowledgeEntryDetail(
  entryId: string,
): Promise<KnowledgeEntryDetail> {
  return apiGet<KnowledgeEntryDetail>(`/knowledge/entries/${entryId}`)
}

export function updateKnowledgeEntry(
  entryId: string,
  data: UpdateKnowledgeEntryBody,
): Promise<KnowledgeEntryDetail> {
  return apiPut<KnowledgeEntryDetail>(`/knowledge/entries/${entryId}`, data)
}

export function deleteKnowledgeEntry(entryId: string): Promise<void> {
  return apiDelete<void>(`/knowledge/entries/${entryId}`)
}

// ===== 语义检索 =====

export function semanticSearch(
  data: KnowledgeSearchBody,
): Promise<KnowledgeSearchData> {
  return apiPost<KnowledgeSearchData>('/knowledge/search', data)
}

// ===== 检索历史 =====

export function listKnowledgeRetrievals(
  projectId: string,
  params?: KnowledgeRetrievalListParams,
): Promise<PaginatedResponse<KnowledgeRetrievalRecord>> {
  return apiGet<PaginatedResponse<KnowledgeRetrievalRecord>>(
    `/projects/${projectId}/knowledge/retrievals`,
    params as Record<string, unknown>,
  )
}
