import { describe, it, expect } from 'vitest'
import { ApiError } from '../errors'

describe('ApiError', () => {
  it('creates error with all fields', () => {
    const err = new ApiError(
      422,
      'VALIDATION_ERROR',
      '请求参数校验失败',
      'test-request-id',
      [{ field: 'body.name', reason: '不能为空' }],
      30,
      { errors: [{ field: 'body.name', reason: '不能为空' }] },
    )

    expect(err.httpStatus).toBe(422)
    expect(err.code).toBe('VALIDATION_ERROR')
    expect(err.message).toBe('请求参数校验失败')
    expect(err.requestId).toBe('test-request-id')
    expect(err.fieldErrors).toHaveLength(1)
    expect(err.retryAfter).toBe(30)
  })

  it('isAuthError returns true for 401', () => {
    const err = new ApiError(401, 'AUTH_REQUIRED', '未登录', 'r1')
    expect(err.isAuthError).toBe(true)
    expect(err.isForbidden).toBe(false)
  })

  it('isForbidden returns true for 403', () => {
    const err = new ApiError(403, 'PERMISSION_DENIED', '无权限', 'r1')
    expect(err.isForbidden).toBe(true)
  })

  it('isNotFound returns true for 404', () => {
    const err = new ApiError(404, 'NOT_FOUND', '不存在', 'r1')
    expect(err.isNotFound).toBe(true)
  })

  it('isConflict returns true for 409', () => {
    const err = new ApiError(409, 'CONFLICT', '冲突', 'r1')
    expect(err.isConflict).toBe(true)
  })

  it('isValidationError returns true for 422', () => {
    const err = new ApiError(422, 'VALIDATION_ERROR', '校验失败', 'r1')
    expect(err.isValidationError).toBe(true)
  })

  it('isRateLimited returns true for 429', () => {
    const err = new ApiError(429, 'RATE_LIMITED', '限流', 'r1', [], 30)
    expect(err.isRateLimited).toBe(true)
    expect(err.retryAfter).toBe(30)
  })

  it('isServerError returns true for 500', () => {
    const err = new ApiError(500, 'INTERNAL_ERROR', '内部错误', 'r1')
    expect(err.isServerError).toBe(true)
  })

  it('getFieldError returns error for matching field', () => {
    const err = new ApiError(422, 'V', 'm', 'r', [
      { field: 'body.name', reason: '不能为空' },
      { field: 'body.email', reason: '格式错误' },
    ])
    expect(err.getFieldError('body.name')).toBe('不能为空')
    expect(err.getFieldError('body.email')).toBe('格式错误')
    expect(err.getFieldError('body.other')).toBeUndefined()
  })

  it('defaults for empty constructor', () => {
    const err = new ApiError(400, 'BAD', 'bad', 'r')
    expect(err.fieldErrors).toEqual([])
    expect(err.retryAfter).toBeNull()
    expect(err.data).toBeNull()
  })
})
