import { useAuthStore } from '@/stores/auth.store'

export async function bootstrap(): Promise<void> {
  const authStore = useAuthStore()
  try {
    await authStore.checkSystemStatus()
  } catch {
    // 开发模式：后端不可用时自动启用 admin 模拟登录
    if (import.meta.env.DEV) {
      console.warn('[DEV] 后端不可用，已启用开发模式（admin 模拟登录）')
      authStore.enableDevMode()
      authStore.markBootstrapped()
      return
    }
    // 生产模式：系统状态检查失败时，允许应用继续加载（由路由守卫处理）
    authStore.setSystemStatusUnknown()
  }
  authStore.markBootstrapped()
}
