import type {
  PaginatedResponse,
  ProjectSummary,
  ProjectDetail,
  ProjectCreatedData,
  ProjectOperationData,
  CreateProjectBody,
  StopProjectBody,
  DeleteProjectBody,
} from '@/contracts'
import { apiGet, apiPost, apiDelete } from '@/services/http/client'

export interface ProjectListParams {
  page?: number
  page_size?: number
  project_status?: string
  source_type?: string
  keyword?: string
  sort?: string
}

export function listProjects(
  params?: ProjectListParams,
): Promise<PaginatedResponse<ProjectSummary>> {
  return apiGet<PaginatedResponse<ProjectSummary>>('/projects', {
    ...params,
  } as Record<string, unknown>)
}

export function getProjectDetail(
  projectId: string,
): Promise<ProjectDetail> {
  return apiGet<ProjectDetail>(`/projects/${projectId}`)
}

export function createProject(
  data: CreateProjectBody,
): Promise<ProjectCreatedData> {
  return apiPost<ProjectCreatedData>('/projects', data)
}

export function startProject(
  projectId: string,
): Promise<ProjectOperationData> {
  return apiPost<ProjectOperationData>(`/projects/${projectId}/start`, {})
}

export function stopProject(
  projectId: string,
  reason: string | null,
): Promise<ProjectOperationData> {
  const body: StopProjectBody = {}
  if (reason) body.reason = reason
  return apiPost<ProjectOperationData>(`/projects/${projectId}/stop`, body)
}

export function deleteProject(
  projectId: string,
  confirmName: string,
): Promise<ProjectOperationData> {
  const body: DeleteProjectBody = { confirm_project_name: confirmName }
  return apiDelete<ProjectOperationData>(`/projects/${projectId}`, body)
}
