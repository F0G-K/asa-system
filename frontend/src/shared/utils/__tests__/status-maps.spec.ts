import { describe, it, expect } from 'vitest'
import {
  PROJECT_STATUS_MAP,
  STAGE_NAME_MAP,
  STAGE_STATUS_MAP,
  TASK_STATUS_MAP,
  WORKER_ROLE_MAP,
  RISK_LEVEL_MAP,
  VERIFY_STATUS_MAP,
  LOG_LEVEL_MAP,
  REPORT_STATUS_MAP,
  CONTAINER_STATUS_MAP,
  SOURCE_TYPE_MAP,
  RISK_LEVEL_ORDER,
  PROJECT_ALLOWED_ACTIONS,
} from '@/contracts'

describe('Status maps', () => {
  it('PROJECT_STATUS_MAP has all expected keys', () => {
    const keys = ['created', 'running', 'completed', 'failed', 'stopped']
    for (const key of keys) {
      expect(PROJECT_STATUS_MAP[key]).toBeDefined()
      expect(PROJECT_STATUS_MAP[key]!.text).toBeTruthy()
      expect(PROJECT_STATUS_MAP[key]!.color).toBeTruthy()
    }
  })

  it('STAGE_NAME_MAP has 5 stages in order', () => {
    const keys = [
      'environment_scan',
      'code_analysis',
      'vulnerability_verify',
      'report_generate',
      'done',
    ]
    for (const key of keys) {
      expect(STAGE_NAME_MAP[key]).toBeDefined()
    }
  })

  it('RISK_LEVEL_MAP has 5 levels', () => {
    const keys = ['critical', 'high', 'medium', 'low', 'info']
    for (const key of keys) {
      expect(RISK_LEVEL_MAP[key]).toBeDefined()
      expect(RISK_LEVEL_MAP[key]!.ariaLabel).toBeTruthy()
    }
  })

  it('RISK_LEVEL_ORDER has correct priority', () => {
    expect(RISK_LEVEL_ORDER.critical).toBeLessThan(RISK_LEVEL_ORDER.high!)
    expect(RISK_LEVEL_ORDER.high).toBeLessThan(RISK_LEVEL_ORDER.medium!)
    expect(RISK_LEVEL_ORDER.medium).toBeLessThan(RISK_LEVEL_ORDER.low!)
    expect(RISK_LEVEL_ORDER.low).toBeLessThan(RISK_LEVEL_ORDER.info!)
  })

  it('VERIFY_STATUS_MAP has 3 states', () => {
    expect(VERIFY_STATUS_MAP.pending).toBeDefined()
    expect(VERIFY_STATUS_MAP.verified).toBeDefined()
    expect(VERIFY_STATUS_MAP.rejected).toBeDefined()
  })

  it('LOG_LEVEL_MAP has 4 levels', () => {
    expect(LOG_LEVEL_MAP.debug).toBeDefined()
    expect(LOG_LEVEL_MAP.info).toBeDefined()
    expect(LOG_LEVEL_MAP.warning).toBeDefined()
    expect(LOG_LEVEL_MAP.error).toBeDefined()
  })

  it('REPORT_STATUS_MAP has 4 states', () => {
    expect(REPORT_STATUS_MAP.pending).toBeDefined()
    expect(REPORT_STATUS_MAP.generating).toBeDefined()
    expect(REPORT_STATUS_MAP.ready).toBeDefined()
    expect(REPORT_STATUS_MAP.failed).toBeDefined()
  })

  it('CONTAINER_STATUS_MAP has 7 states', () => {
    const keys = [
      'pending', 'starting', 'running', 'stopping',
      'stopped', 'destroyed', 'failed',
    ]
    for (const key of keys) {
      expect(CONTAINER_STATUS_MAP[key]).toBeDefined()
    }
  })

  it('WORKER_ROLE_MAP has 6 roles', () => {
    const keys = [
      'general', 'environment_inspector', 'code_analyst',
      'vulnerability_verifier', 'report_editor', 'operations_assistant',
    ]
    for (const key of keys) {
      expect(WORKER_ROLE_MAP[key]).toBeDefined()
    }
  })

  it('SOURCE_TYPE_MAP has local and repository', () => {
    expect(SOURCE_TYPE_MAP.local).toBeDefined()
    expect(SOURCE_TYPE_MAP.repository).toBeDefined()
  })

  it('PROJECT_ALLOWED_ACTIONS has correct actions per status', () => {
    expect(PROJECT_ALLOWED_ACTIONS.created).toContain('start')
    expect(PROJECT_ALLOWED_ACTIONS.created).toContain('delete')
    expect(PROJECT_ALLOWED_ACTIONS.running).toContain('stop')
    expect(PROJECT_ALLOWED_ACTIONS.running).toContain('monitor')
    expect(PROJECT_ALLOWED_ACTIONS.completed).toContain('report')
    expect(PROJECT_ALLOWED_ACTIONS.failed).toContain('results')
    expect(PROJECT_ALLOWED_ACTIONS.stopped).toContain('results')
  })

  it('STAGE_STATUS_MAP has 4 states', () => {
    expect(STAGE_STATUS_MAP.idle).toBeDefined()
    expect(STAGE_STATUS_MAP.running).toBeDefined()
    expect(STAGE_STATUS_MAP.success).toBeDefined()
    expect(STAGE_STATUS_MAP.failed).toBeDefined()
  })

  it('TASK_STATUS_MAP has 4 states', () => {
    expect(TASK_STATUS_MAP.idle).toBeDefined()
    expect(TASK_STATUS_MAP.running).toBeDefined()
    expect(TASK_STATUS_MAP.success).toBeDefined()
    expect(TASK_STATUS_MAP.failed).toBeDefined()
  })
})
