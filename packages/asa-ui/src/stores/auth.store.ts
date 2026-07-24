import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserSummary, SystemStatusData, LoginData } from '@asa/contracts'
import { apiGet, apiPost } from '@/services/http/client'

export const useAuthStore = defineStore('auth', () => {
  // ===== State =====
  const user = ref<UserSummary | null>(null)
  const isSystemInitialized = ref<boolean | null>(null)
  const loadingStatus = ref<'idle' | 'loading' | 'error'>('idle')

  // ===== Getters =====
  const isAuthenticated = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const username = computed(() => user.value?.username ?? '')
  const userId = computed(() => user.value?.id ?? '')

  // ===== Actions =====

  async function checkSystemStatus(): Promise<void> {
    loadingStatus.value = 'loading'
    try {
      const data = await apiGet<SystemStatusData>('/system/status')
      isSystemInitialized.value = data.initialized
      loadingStatus.value = 'idle'
    } catch {
      isSystemInitialized.value = null
      loadingStatus.value = 'error'
      throw new Error('无法获取系统状态')
    }
  }

  function setSystemStatusUnknown(): void {
    isSystemInitialized.value = null
    loadingStatus.value = 'error'
  }

  async function initSystem(username: string, password: string): Promise<UserSummary> {
    const data = await apiPost<{ admin: UserSummary }>('/system/init', {
      username,
      password,
    })
    isSystemInitialized.value = true
    return data.admin
  }

  async function login(username: string, password: string): Promise<void> {
    const data = await apiPost<LoginData>('/system/login', {
      username,
      password,
    })
    user.value = data.user
  }

  async function logout(): Promise<void> {
    try {
      await apiPost('/system/logout')
    } catch {
      // 即使退出API失败，也清理本地状态
    } finally {
      clearSession()
    }
  }

  function clearSession(): void {
    user.value = null
    // 清理项目级 sessionStorage
    for (const key of Object.keys(sessionStorage)) {
      if (key.startsWith('asa_')) {
        sessionStorage.removeItem(key)
      }
    }
  }

  return {
    // state
    user,
    isSystemInitialized,
    loadingStatus,
    // getters
    isAuthenticated,
    isAdmin,
    username,
    userId,
    // actions
    checkSystemStatus,
    setSystemStatusUnknown,
    initSystem,
    login,
    logout,
    clearSession,
  }
})
