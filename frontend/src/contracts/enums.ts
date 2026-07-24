// ===== 用户与认证 =====

export type UserRole = 'user' | 'admin'

export type UserStatus = 'active' | 'disabled'

// ===== 项目 =====

export type ProjectStatus =
  | 'created'
  | 'running'
  | 'completed'
  | 'failed'
  | 'stopped'

export type SourceType = 'local' | 'repository'

export type EnvironmentType = string // 由管理员配置确定值域

// ===== 阶段 =====

export type StageName =
  | 'environment_scan'
  | 'code_analysis'
  | 'vulnerability_verify'
  | 'report_generate'
  | 'done'

export type StageStatus = 'idle' | 'running' | 'success' | 'failed'

// ===== 角色任务 =====

export type WorkerRole =
  | 'general'
  | 'environment_inspector'
  | 'code_analyst'
  | 'vulnerability_verifier'
  | 'report_editor'
  | 'operations_assistant'

export type TaskStatus = 'idle' | 'running' | 'success' | 'failed'

// ===== 漏洞 =====

export type RiskLevel = 'critical' | 'high' | 'medium' | 'low' | 'info'

export type VerifyStatus = 'pending' | 'verified' | 'rejected'

// ===== 日志与报告 =====

export type LogLevel = 'debug' | 'info' | 'warning' | 'error'

export type ReportStatus = 'pending' | 'generating' | 'ready' | 'failed'

// ===== 容器 =====

export type ContainerStatus =
  | 'pending'
  | 'starting'
  | 'running'
  | 'stopping'
  | 'stopped'
  | 'destroyed'
  | 'failed'

// ===== WebSocket 事件 =====

export type WsEventType =
  | 'project_status'
  | 'stage_status'
  | 'worker_status'
  | 'chat_message'
  | 'runtime_log'
  | 'resource_usage'
  | 'vulnerability_found'
  | 'report_ready'

// ===== 知识库 =====

export type KnowledgeType =
  | 'vulnerability_pattern'
  | 'security_standard'
  | 'remediation_advice'
  | 'historical_assessment'

export type EntryStatus = 'active' | 'disabled' | 'draft'

export type KnowledgeSourceType = 'manual' | 'external_import' | 'auto_curated'

export type RetrievalType = 'stage_pre' | 'role_pre' | 'tool_triggered'

// ===== 消息类型 =====

export type MessageType = string // 非空协议标识，尚未形成闭集
