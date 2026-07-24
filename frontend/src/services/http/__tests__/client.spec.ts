import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'
import type { ApiResponse } from '@/contracts'
import { ApiError } from '../errors'

// Mock axios
vi.mock('axios', () => {
  const mockInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  }
  return {
    default: {
      create: vi.fn(() => mockInstance),
    },
  }
})

// Mock csrf
vi.mock('../csrf', () => ({
  readCsrfToken: vi.fn(() => 'mock-csrf-token'),
}))

// Mock router
vi.mock('@/router', () => ({
  router: {
    push: vi.fn(),
    currentRoute: { value: { fullPath: '/test' } },
  },
}))

// Mock auth store
const mockClearSession = vi.fn()
vi.mock('@/stores/auth.store', () => ({
  useAuthStore: vi.fn(() => ({
    clearSession: mockClearSession,
    isAuthenticated: false,
  })),
}))

// We must import after mocks are set up
import { apiGet, apiPost, apiPut, apiDelete, unwrap } from '../client'

const mockAxios = axios.create() as ReturnType<typeof axios.create> & {
  get: ReturnType<typeof vi.fn>
  post: ReturnType<typeof vi.fn>
  put: ReturnType<typeof vi.fn>
  delete: ReturnType<typeof vi.fn>
}

describe('unwrap', () => {
  it('extracts data from ApiResponse', () => {
    const response: { data: ApiResponse<{ id: string }> } = {
      data: {
        code: 'OK',
        message: '成功',
        data: { id: '123' },
        request_id: 'req-1',
      },
    }
    expect(unwrap(response)).toEqual({ id: '123' })
  })

  it('extracts null data', () => {
    const response: { data: ApiResponse<null> } = {
      data: {
        code: 'OK',
        message: '成功',
        data: null,
        request_id: 'req-1',
      },
    }
    expect(unwrap(response)).toBeNull()
  })
})

describe('apiGet', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls httpClient.get and unwraps', async () => {
    mockAxios.get.mockResolvedValue({
      data: {
        code: 'OK',
        message: '成功',
        data: { items: [], total: 0 },
        request_id: 'r1',
      },
    })

    const result = await apiGet('/projects', { page: 1 })
    expect(result).toEqual({ items: [], total: 0 })
    expect(mockAxios.get).toHaveBeenCalledWith('/projects', { params: { page: 1 } })
  })

  it('calls without params', async () => {
    mockAxios.get.mockResolvedValue({
      data: {
        code: 'OK',
        message: '成功',
        data: null,
        request_id: 'r1',
      },
    })

    await apiGet('/system/status')
    expect(mockAxios.get).toHaveBeenCalledWith('/system/status', { params: undefined })
  })
})

describe('apiPost', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls httpClient.post and unwraps', async () => {
    mockAxios.post.mockResolvedValue({
      data: {
        code: 'OK',
        message: '创建成功',
        data: { id: 'new-id' },
        request_id: 'r1',
      },
    })

    const result = await apiPost('/projects', { name: 'test' })
    expect(result).toEqual({ id: 'new-id' })
    expect(mockAxios.post).toHaveBeenCalledWith('/projects', { name: 'test' })
  })

  it('calls with undefined body', async () => {
    mockAxios.post.mockResolvedValue({
      data: { code: 'OK', message: '成功', data: null, request_id: 'r1' },
    })

    await apiPost('/system/logout')
    expect(mockAxios.post).toHaveBeenCalledWith('/system/logout', undefined)
  })
})

describe('apiPut', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls httpClient.put and unwraps', async () => {
    mockAxios.put.mockResolvedValue({
      data: {
        code: 'OK',
        message: '更新成功',
        data: { id: 'updated' },
        request_id: 'r1',
      },
    })

    const result = await apiPut('/config/1', { setting: 'value' })
    expect(result).toEqual({ id: 'updated' })
    expect(mockAxios.put).toHaveBeenCalledWith('/config/1', { setting: 'value' })
  })
})

describe('apiDelete', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('calls httpClient.delete and unwraps', async () => {
    mockAxios.delete.mockResolvedValue({
      data: {
        code: 'OK',
        message: '删除成功',
        data: { id: 'deleted' },
        request_id: 'r1',
      },
    })

    const result = await apiDelete('/projects/1', { confirm_project_name: 'test' })
    expect(result).toEqual({ id: 'deleted' })
    expect(mockAxios.delete).toHaveBeenCalledWith('/projects/1', {
      data: { confirm_project_name: 'test' },
    })
  })
})
