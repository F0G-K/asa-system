// ===== 状态映射类型 =====

export interface StatusDisplay {
  text: string
  color: string
  icon?: string
  ariaLabel?: string
}

// ===== 项目状态映射 =====

export const PROJECT_STATUS_MAP: Record<string, StatusDisplay> = {
  created: {
    text: '已创建',
    color: 'var(--color-info)',
    ariaLabel: '项目状态：已创建',
  },
  running: {
    text: '运行中',
    color: 'var(--color-primary)',
    ariaLabel: '项目状态：运行中',
  },
  completed: {
    text: '已完成',
    color: 'var(--color-success)',
    ariaLabel: '项目状态：已完成',
  },
  failed: {
    text: '失败',
    color: 'var(--color-danger)',
    ariaLabel: '项目状态：失败',
  },
  stopped: {
    text: '已停止',
    color: 'var(--color-warning)',
    ariaLabel: '项目状态：已停止',
  },
}

// ===== 阶段名称映射 =====

export const STAGE_NAME_MAP: Record<string, StatusDisplay> = {
  environment_scan: { text: '环境扫描', color: 'var(--color-primary)' },
  code_analysis: { text: '代码分析', color: 'var(--color-primary)' },
  vulnerability_verify: { text: '漏洞验证', color: 'var(--color-primary)' },
  report_generate: { text: '报告生成', color: 'var(--color-primary)' },
  done: { text: '完成', color: 'var(--color-success)' },
}

// ===== 阶段状态映射 =====

export const STAGE_STATUS_MAP: Record<string, StatusDisplay> = {
  idle: { text: '等待中', color: 'var(--color-text-secondary)' },
  running: { text: '执行中', color: 'var(--color-primary)' },
  success: { text: '成功', color: 'var(--color-success)' },
  failed: { text: '失败', color: 'var(--color-danger)' },
}

// ===== 任务状态映射 =====

export const TASK_STATUS_MAP: Record<string, StatusDisplay> = {
  idle: { text: '等待中', color: 'var(--color-text-secondary)' },
  running: { text: '执行中', color: 'var(--color-primary)' },
  success: { text: '成功', color: 'var(--color-success)' },
  failed: { text: '失败', color: 'var(--color-danger)' },
}

// ===== 执行角色映射 =====

export const WORKER_ROLE_MAP: Record<string, StatusDisplay> = {
  general: { text: '通用助手', color: 'var(--color-text-secondary)' },
  environment_inspector: { text: '环境检查员', color: 'var(--color-primary)' },
  code_analyst: { text: '代码分析员', color: 'var(--color-primary)' },
  vulnerability_verifier: { text: '漏洞验证员', color: 'var(--color-warning)' },
  report_editor: { text: '报告编辑', color: 'var(--color-success)' },
  operations_assistant: { text: '运维助理', color: 'var(--color-info)' },
}

// ===== 风险等级映射 =====

export const RISK_LEVEL_MAP: Record<string, StatusDisplay> = {
  critical: {
    text: '严重',
    color: 'var(--color-danger)',
    ariaLabel: '风险等级：严重',
  },
  high: { text: '高', color: 'var(--color-danger)', ariaLabel: '风险等级：高' },
  medium: {
    text: '中',
    color: 'var(--color-warning)',
    ariaLabel: '风险等级：中',
  },
  low: { text: '低', color: 'var(--color-info)', ariaLabel: '风险等级：低' },
  info: {
    text: '信息',
    color: 'var(--color-text-secondary)',
    ariaLabel: '风险等级：信息',
  },
}

// ===== 验证状态映射 =====

export const VERIFY_STATUS_MAP: Record<string, StatusDisplay> = {
  pending: { text: '待验证', color: 'var(--color-text-secondary)' },
  verified: { text: '已验证', color: 'var(--color-success)' },
  rejected: { text: '已拒绝', color: 'var(--color-danger)' },
}

// ===== 日志级别映射 =====

export const LOG_LEVEL_MAP: Record<string, StatusDisplay> = {
  debug: { text: '调试', color: 'var(--color-text-secondary)' },
  info: { text: '信息', color: 'var(--color-primary)' },
  warning: { text: '警告', color: 'var(--color-warning)' },
  error: { text: '错误', color: 'var(--color-danger)' },
}

// ===== 报告状态映射 =====

export const REPORT_STATUS_MAP: Record<string, StatusDisplay> = {
  pending: { text: '待生成', color: 'var(--color-text-secondary)' },
  generating: { text: '生成中', color: 'var(--color-primary)' },
  ready: { text: '已就绪', color: 'var(--color-success)' },
  failed: { text: '生成失败', color: 'var(--color-danger)' },
}

// ===== 容器状态映射 =====

export const CONTAINER_STATUS_MAP: Record<string, StatusDisplay> = {
  pending: { text: '等待中', color: 'var(--color-text-secondary)' },
  starting: { text: '启动中', color: 'var(--color-primary)' },
  running: { text: '运行中', color: 'var(--color-success)' },
  stopping: { text: '停止中', color: 'var(--color-warning)' },
  stopped: { text: '已停止', color: 'var(--color-text-secondary)' },
  destroyed: { text: '已销毁', color: 'var(--color-text-secondary)' },
  failed: { text: '失败', color: 'var(--color-danger)' },
}

// ===== 源码类型映射 =====

export const SOURCE_TYPE_MAP: Record<string, StatusDisplay> = {
  local: { text: '本地源码', color: 'var(--color-info)' },
  repository: { text: 'Git 仓库', color: 'var(--color-primary)' },
}

// ===== 风险等级排序权重 =====

export const RISK_LEVEL_ORDER: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
}

// ===== 项目状态允许的操作 =====

export const PROJECT_ALLOWED_ACTIONS: Record<string, string[]> = {
  created: ['view', 'start', 'delete'],
  running: ['view', 'monitor', 'stop'],
  completed: ['view', 'results', 'report', 'delete'],
  failed: ['view', 'results', 'delete'],
  stopped: ['view', 'results', 'delete'],
}
