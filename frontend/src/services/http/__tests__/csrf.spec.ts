import { describe, it, expect, beforeEach, vi } from 'vitest'
import { readCsrfToken } from '../csrf'

describe('readCsrfToken', () => {
  beforeEach(() => {
    // 清理 cookie
    Object.defineProperty(document, 'cookie', {
      writable: true,
      value: '',
    })
  })

  it('returns null when cookie is empty', () => {
    document.cookie = ''
    expect(readCsrfToken()).toBeNull()
  })

  it('returns csrf token from cookie', () => {
    document.cookie = 'asa_csrf=abc123def456'
    expect(readCsrfToken()).toBe('abc123def456')
  })

  it('returns csrf token when multiple cookies present', () => {
    document.cookie = 'asa_session=session123; asa_csrf=xyz789; other=value'
    expect(readCsrfToken()).toBe('xyz789')
  })

  it('returns null when asa_csrf not in cookies', () => {
    document.cookie = 'asa_session=session123; other=value'
    expect(readCsrfToken()).toBeNull()
  })

  it('returns null for malformed asa_csrf cookie', () => {
    document.cookie = 'asa_csrf='
    expect(readCsrfToken()).toBe('')
  })
})
