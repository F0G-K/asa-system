import type { ApiFieldError } from '@asa/contracts'

export class ApiError extends Error {
  readonly httpStatus: number
  readonly code: string
  readonly requestId: string
  readonly fieldErrors: ApiFieldError[]
  readonly retryAfter: number | null
  readonly data: Record<string, unknown> | null

  constructor(
    httpStatus: number,
    code: string,
    message: string,
    requestId: string,
    fieldErrors: ApiFieldError[] = [],
    retryAfter: number | null = null,
    data: Record<string, unknown> | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.httpStatus = httpStatus
    this.code = code
    this.requestId = requestId
    this.fieldErrors = fieldErrors
    this.retryAfter = retryAfter
    this.data = data
  }

  get isAuthError(): boolean {
    return this.httpStatus === 401
  }

  get isForbidden(): boolean {
    return this.httpStatus === 403
  }

  get isNotFound(): boolean {
    return this.httpStatus === 404
  }

  get isConflict(): boolean {
    return this.httpStatus === 409
  }

  get isValidationError(): boolean {
    return this.httpStatus === 422
  }

  get isRateLimited(): boolean {
    return this.httpStatus === 429
  }

  get isServerError(): boolean {
    return this.httpStatus >= 500
  }

  getFieldError(field: string): string | undefined {
    return this.fieldErrors.find((e) => e.field === field)?.reason
  }
}
