import { useAuthStore } from '@/stores/auth.store'

export async function bootstrap(): Promise<void> {
  const authStore = useAuthStore()
  try {
    await authStore.checkSystemStatus()
  } catch {
    // 系统状态检查失败时，允许应用继续加载（由路由守卫处理）
    authStore.setSystemStatusUnknown()
  }
}
