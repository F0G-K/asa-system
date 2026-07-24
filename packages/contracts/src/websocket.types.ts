import type {
  ProjectStatus,
  StageName,
  StageStatus,
  WorkerRole,
  TaskStatus,
  RiskLevel,
  LogLevel,
  ReportStatus,
} from './enums'

// ===== WebSocket 事件包 =====

export interface WsEvent<T = Record<string, unknown>> {
  event_id: string
  sequence: number
  event_type: string
  project_id: string
  occurred_at: string
  data: T
}

// ===== 各事件类型载荷 =====

export interface ProjectStatusEventData {
  project_status: ProjectStatus
  stop_requested_at: string | null
}

export interface StageStatusEventData {
  stage_id: string
  stage_name: StageName
  stage_status: StageStatus
}

export interface WorkerStatusEventData {
  worker_task_id: string
  worker_role: WorkerRole
  task_status: TaskStatus
}

export interface ChatMessageEventData {
  message_id: number
  worker_role: WorkerRole
  message_type: string
  message_text: string
}

export interface RuntimeLogEventData {
  log_id: number
  log_level: LogLevel
  log_content: string
}

export interface ResourceUsageEventData {
  resource_usage_id: number
  cpu_usage: number
  memory_usage: number
  token_count: number
}

export interface VulnerabilityFoundEventData {
  vulnerability_id: string
  vuln_code: string
  vuln_title: string
  risk_level: RiskLevel
}

export interface ReportReadyEventData {
  report_id: string
  version: number
  report_status: ReportStatus
}

// ===== 客户端心跳 =====

export interface WsPing {
  type: 'ping'
  sent_at: string
}

export interface WsPong {
  type: 'pong'
  server_time: string
}

// ===== 连接状态 =====

export type WsConnectionStatus =
  | 'disconnected'
  | 'connecting'
  | 'connected'
  | 'reconnecting'
  | 'compensating'

// ===== WebSocket 关闭码 =====

export const WS_CLOSE_CODES = {
  SESSION_EXPIRED: 4001,
  PROJECT_ACCESS_DENIED: 4003,
  RATE_LIMITED: 4008,
  EVENT_GAP_TOO_LARGE: 4009,
  CLIENT_TOO_SLOW: 4010,
  INTERNAL_ERROR: 1011,
} as const
