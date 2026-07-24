import type {
  UserRole,
  UserStatus,
  ProjectStatus,
  SourceType,
  StageName,
  StageStatus,
  WorkerRole,
  TaskStatus,
  RiskLevel,
  VerifyStatus,
  LogLevel,
  ReportStatus,
  ContainerStatus,
} from './enums'

// ===== 通用 =====

export interface ApiResponse<T> {
  code: string
  message: string
  data: T
  request_id: string
}

export interface ApiFieldError {
  field: string
  reason: string
}

export interface ApiErrorData {
  errors?: ApiFieldError[]
  project_status?: string
  allowed_statuses?: string[]
  expected_version?: number
  current_version?: number
  report_status?: string
  retry_after_seconds?: number
  reason?: string
  field?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  page: number
  page_size: number
  total: number
  has_next: boolean
}

export interface CursorResponse<T> {
  items: T[]
  next_cursor: number | null
  has_more: boolean
}

// ===== 用户 =====

export interface UserSummary {
  id: string
  username: string
  role: UserRole
  status: UserStatus
}

export interface LoginData {
  user: UserSummary
  expires_at: string
}

// ===== 系统 =====

export interface LlmSettings {
  api_base_url: string
  api_key: string
  model_name: string
  max_tokens: number
  temperature: number
}

export interface SystemStatusData {
  initialized: boolean
}

export interface SystemConfigData {
  id: string
  version: number
  default_timeout_seconds: number | null
  max_concurrent_projects: number | null
  log_retention_days: number | null
  file_retention_days: number | null
  enabled_environment_types: string[]
  settings: Record<string, unknown>
  is_active: boolean
  updated_by: string
  updated_at: string
}

// ===== 项目 =====

export interface ProjectSummary {
  id: string
  project_name: string
  source_type: SourceType
  source_path: string
  environment_type: string
  project_status: ProjectStatus
  last_started_at: string | null
  last_finished_at: string | null
  created_at: string
  updated_at: string
}

export interface RuntimeInfo {
  id: string
  runtime_identifier: string | null
  container_status: ContainerStatus
  started_at: string | null
  stopped_at: string | null
  error_message: string | null
}

export interface ProjectStatistics {
  vulnerability_count: number
  verified_vulnerability_count: number
  attack_path_count: number
  worker_task_count: number
}

export interface ProjectDetail extends ProjectSummary {
  task_content: string
  created_by: string
  stop_requested_at: string | null
  runtime: RuntimeInfo | null
  statistics: ProjectStatistics
  report_status: ReportStatus | null
}

export interface ProjectCreatedData {
  id: string
  project_name: string
  source_type: SourceType
  source_path: string
  task_content: string
  environment_type: string
  project_status: ProjectStatus
  created_by: string
  created_at: string
  updated_at: string
}

export interface ProjectOperationData {
  project_id: string
  project_status: string
  operation: string
  accepted_at?: string
  stop_requested_at?: string
}

// ===== 阶段 =====

export interface StageItem {
  id: string
  stage_name: StageName
  stage_order: number
  stage_status: StageStatus
  started_at: string | null
  finished_at: string | null
  error_message: string | null
}

// ===== 角色任务 =====

export interface WorkerTask {
  id: string
  stage_id: string
  worker_role: WorkerRole
  task_content: string
  task_status: TaskStatus
  result_summary: string | null
  error_message: string | null
  request_id: string
  attempt_count: number
  started_at: string | null
  finished_at: string | null
  created_at: string
}

// ===== 消息 =====

export interface ChatMessage {
  id: number
  stage_id: string
  worker_task_id: string
  worker_role: WorkerRole
  message_type: string
  message_text: string
  created_at: string
}

// ===== 日志 =====

export interface RuntimeLog {
  id: number
  stage_id: string
  worker_task_id: string | null
  request_id: string | null
  log_level: LogLevel
  log_content: string
  created_at: string
}

// ===== 资源 =====

export interface ResourceSample {
  id: number
  runtime_id: string
  cpu_usage: number
  memory_usage: number
  token_count: number
  recorded_at: string
}

export interface ResourceUnits {
  cpu_usage: string
  memory_usage: string
  token_count: string
}

export interface ResourceResponse extends CursorResponse<ResourceSample> {
  units: ResourceUnits
}

// ===== 漏洞 =====

export interface VulnerabilitySummary {
  id: string
  vuln_code: string
  vuln_title: string
  rule_type: string
  risk_level: RiskLevel
  file_path: string
  line_start: number
  line_end: number
  verify_status: VerifyStatus
  created_at: string
}

export interface VulnerabilityDetail {
  id: string
  project_id: string
  vuln_code: string
  vuln_title: string
  rule_type: string
  risk_level: RiskLevel
  file_path: string
  line_start: number
  line_end: number
  impact_text: string
  condition_text: string
  evidence_text: string
  verify_status: VerifyStatus
  reproduce_steps_text: string
  verify_code_text: string
  discovered_by_task_id: string
  verified_by_task_id: string | null
  created_at: string
  updated_at: string
}

// ===== 攻击路径 =====

export interface AttackPathSummary {
  id: string
  path_code: string
  path_title: string
  path_summary: string
  final_impact_text: string
  step_count: number
  vulnerability_codes: string[]
  created_at: string
}

export interface AttackPathStepVuln {
  id: string
  vuln_code: string
  vuln_title: string
  risk_level: RiskLevel
  verify_status: VerifyStatus
}

export interface AttackPathStep {
  step_order: number
  step_text: string
  vulnerability: AttackPathStepVuln
}

export interface AttackPathDetail {
  id: string
  project_id: string
  path_code: string
  path_title: string
  path_summary: string
  final_impact_text: string
  steps: AttackPathStep[]
  created_at: string
}

// ===== 报告 =====

export interface ReportData {
  id: string
  project_id: string
  version: number
  report_status: ReportStatus
  report_markdown: string | null
  report_html: string | null
  download_available: boolean
  content_sha256: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}

// ===== 创建/更新请求体 =====

export interface InitRequestBody {
  username: string
  password: string
}

export interface LoginRequestBody {
  username: string
  password: string
}

export interface CreateProjectBody {
  project_name: string
  source_type: SourceType
  source_path: string
  task_content: string
  environment_type: string
}

export interface StopProjectBody {
  reason?: string | null
}

export interface DeleteProjectBody {
  confirm_project_name: string
}

export interface UpdateConfigBody {
  expected_version: number | null
  default_timeout_seconds: number | null
  max_concurrent_projects: number | null
  log_retention_days: number | null
  file_retention_days: number | null
  enabled_environment_types: string[]
  settings?: Record<string, unknown>
}
