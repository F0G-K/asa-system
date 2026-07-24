import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock the HTTP client
vi.mock('@/services/http/client', () => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}))

import { apiGet, apiPost } from '@/services/http/client'
import { useAuthStore } from '../auth.store'
import { ApiError } from '@/services/http/errors'

const mockApiGet = apiGet as ReturnType<typeof vi.fn>
const mockApiPost = apiPost as ReturnType<typeof vi.fn>

describe('useAuthStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    // 清理 sessionStorage
    sessionStorage.clear()
  })

  describe('initial state', () => {
    it('has null user', () => {
      const store = useAuthStore()
      expect(store.user).toBeNull()
    })

    it('has unknown system status', () => {
      const store = useAuthStore()
      expect(store.isSystemInitialized).toBeNull()
    })

    it('is not authenticated', () => {
      const store = useAuthStore()
      expect(store.isAuthenticated).toBe(false)
    })

    it('is not admin', () => {
      const store = useAuthStore()
      expect(store.isAdmin).toBe(false)
    })

    it('has idle loading status', () => {
      const store = useAuthStore()
      expect(store.loadingStatus).toBe('idle')
    })

    it('is not bootstrapped', () => {
      const store = useAuthStore()
      expect(store.isBootstrapped).toBe(false)
    })
  })

  describe('checkSystemStatus', () => {
    it('sets initialized=true on success', async () => {
      mockApiGet.mockResolvedValue({ initialized: true })
      const store = useAuthStore()

      await store.checkSystemStatus()
      expect(store.isSystemInitialized).toBe(true)
      expect(store.loadingStatus).toBe('idle')
    })

    it('sets initialized=false on uninitialized system', async () => {
      mockApiGet.mockResolvedValue({ initialized: false })
      const store = useAuthStore()

      await store.checkSystemStatus()
      expect(store.isSystemInitialized).toBe(false)
    })

    it('sets error state on network failure', async () => {
      mockApiGet.mockRejectedValue(new Error('网络错误'))
      const store = useAuthStore()

      await expect(store.checkSystemStatus()).rejects.toThrow('无法获取系统状态')
      expect(store.loadingStatus).toBe('error')
      expect(store.isSystemInitialized).toBeNull()
    })

    it('sets loading status during request', () => {
      // 使用 pending promise
      mockApiGet.mockImplementation(() => new Promise(() => {}))
      const store = useAuthStore()

      store.checkSystemStatus()
      expect(store.loadingStatus).toBe('loading')
    })
  })

  describe('initSystem', () => {
    it('returns admin user and marks initialized', async () => {
      const admin = {
        id: 'admin-1',
        username: 'admin',
        role: 'admin' as const,
        status: 'active' as const,
      }
      mockApiPost.mockResolvedValue({ admin })
      const store = useAuthStore()

      const result = await store.initSystem('admin', 'password123')
      expect(result).toEqual(admin)
      expect(store.isSystemInitialized).toBe(true)
      expect(mockApiPost).toHaveBeenCalledWith('/system/init', {
        username: 'admin',
        password: 'password123',
      })
    })
  })

  describe('login', () => {
    it('sets user on successful login', async () => {
      const user = {
        id: 'user-1',
        username: 'testuser',
        role: 'user' as const,
        status: 'active' as const,
      }
      mockApiPost.mockResolvedValue({ user, expires_at: '2026-08-01T00:00:00Z' })
      const store = useAuthStore()

      await store.login('testuser', 'password')
      expect(store.user).toEqual(user)
      expect(store.isAuthenticated).toBe(true)
    })

    it('throws on login failure', async () => {
      mockApiPost.mockRejectedValue(new ApiError(401, 'INVALID_CREDENTIALS', '密码错误', 'r1'))
      const store = useAuthStore()

      await expect(store.login('test', 'wrong')).rejects.toBeInstanceOf(ApiError)
      expect(store.isAuthenticated).toBe(false)
    })
  })

  describe('logout', () => {
    it('clears session even when API fails', async () => {
      const user = { id: 'u1', username: 'test', role: 'user' as const, status: 'active' as const }
      mockApiPost.mockResolvedValue({ user, expires_at: 'd' })
      const store = useAuthStore()

      await store.login('test', 'pass')
      expect(store.isAuthenticated).toBe(true)

      mockApiPost.mockRejectedValue(new Error('网络错误'))
      await store.logout()
      expect(store.isAuthenticated).toBe(false)
      expect(store.user).toBeNull()
    })

    it('clears asa_ prefixed sessionStorage', async () => {
      sessionStorage.setItem('asa_project_id', '123')
      sessionStorage.setItem('other', 'keep')
      const store = useAuthStore()

      store.clearSession()
      expect(sessionStorage.getItem('asa_project_id')).toBeNull()
      expect(sessionStorage.getItem('other')).toBe('keep')
    })
  })

  describe('clearSession', () => {
    it('sets user to null', () => {
      const store = useAuthStore()
      store.user = {
        id: 'u1',
        username: 'test',
        role: 'user',
        status: 'active',
      }
      store.clearSession()
      expect(store.user).toBeNull()
    })

    it('removes asa_ prefixed keys only', () => {
      sessionStorage.setItem('asa_key1', 'val1')
      sessionStorage.setItem('asa_key2', 'val2')
      sessionStorage.setItem('keep_me', 'val3')

      const store = useAuthStore()
      store.clearSession()

      expect(sessionStorage.getItem('asa_key1')).toBeNull()
      expect(sessionStorage.getItem('asa_key2')).toBeNull()
      expect(sessionStorage.getItem('keep_me')).toBe('val3')
    })
  })

  describe('getters', () => {
    it('isAuthenticated returns true when user exists', () => {
      const store = useAuthStore()
      store.user = {
        id: 'u1',
        username: 't',
        role: 'user',
        status: 'active',
      }
      expect(store.isAuthenticated).toBe(true)
    })

    it('isAdmin returns false for regular user', () => {
      const store = useAuthStore()
      store.user = {
        id: 'u1',
        username: 't',
        role: 'user',
        status: 'active',
      }
      expect(store.isAdmin).toBe(false)
    })

    it('isAdmin returns true for admin', () => {
      const store = useAuthStore()
      store.user = {
        id: 'u1',
        username: 'admin',
        role: 'admin',
        status: 'active',
      }
      expect(store.isAdmin).toBe(true)
    })

    it('username returns empty string when no user', () => {
      const store = useAuthStore()
      expect(store.username).toBe('')
    })

    it('userId returns empty string when no user', () => {
      const store = useAuthStore()
      expect(store.userId).toBe('')
    })
  })

  describe('enableDevMode', () => {
    it('sets dev admin user', () => {
      const store = useAuthStore()
      store.enableDevMode()
      expect(store.isAuthenticated).toBe(true)
      expect(store.isAdmin).toBe(true)
      expect(store.username).toBe('dev_admin')
      expect(store.isSystemInitialized).toBe(true)
    })
  })

  describe('markBootstrapped', () => {
    it('sets isBootstrapped to true', () => {
      const store = useAuthStore()
      expect(store.isBootstrapped).toBe(false)
      store.markBootstrapped()
      expect(store.isBootstrapped).toBe(true)
    })
  })

  describe('setSystemStatusUnknown', () => {
    it('resets system status to unknown with error', () => {
      const store = useAuthStore()
      store.isSystemInitialized = true
      store.setSystemStatusUnknown()
      expect(store.isSystemInitialized).toBeNull()
      expect(store.loadingStatus).toBe('error')
    })
  })
})
