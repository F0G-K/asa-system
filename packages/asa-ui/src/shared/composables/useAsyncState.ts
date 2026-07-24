import { ref, type Ref, type UnwrapRef } from 'vue'
import { ApiError } from '@/services/http/errors'

interface UseAsyncStateReturn<T> {
  data: Ref<UnwrapRef<T> | null>
  loading: Ref<boolean>
  error: Ref<ApiError | null>
  execute: (...args: unknown[]) => Promise<T | null>
  reset: () => void
}

/**
 * 通用异步状态管理 composable。
 * 自动处理 loading/error/data 状态和竞态条件。
 */
export function useAsyncState<T>(
  fn: (...args: unknown[]) => Promise<T>,
): UseAsyncStateReturn<T> {
  const data = ref<T | null>(null) as Ref<UnwrapRef<T> | null>
  const loading = ref(false)
  const error = ref<ApiError | null>(null)
  let requestId = 0

  async function execute(...args: unknown[]): Promise<T | null> {
    const currentId = ++requestId
    loading.value = true
    error.value = null

    try {
      const result = await fn(...args)
      // 丢弃过期请求的响应
      if (currentId !== requestId) return null
      data.value = result as UnwrapRef<T>
      return result
    } catch (e) {
      if (currentId !== requestId) return null
      if (e instanceof ApiError) {
        error.value = e
      } else {
        error.value = new ApiError(
          0,
          'UNKNOWN',
          e instanceof Error ? e.message : '未知错误',
          '',
        )
      }
      return null
    } finally {
      if (currentId === requestId) {
        loading.value = false
      }
    }
  }

  function reset(): void {
    data.value = null
    loading.value = false
    error.value = null
    requestId++
  }

  return { data, loading, error, execute, reset }
}
