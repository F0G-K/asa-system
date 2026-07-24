import axios, {
  type AxiosInstance,
  type AxiosError,
  type InternalAxiosRequestConfig,
} from 'axios'
import type { ApiResponse, ApiFieldError } from '@/contracts'
import { ApiError } from './errors'
import { readCsrfToken } from './csrf'

const CSRF_METHODS = new Set(['post', 'put', 'patch', 'delete'])

// 防止多个并发 401 同时触发多次跳转
let authRedirectPending = false

function resetAuthRedirect() {
  authRedirectPending = false
}

function createAxiosInstance(): AxiosInstance {
  const instance = axios.create({
    baseURL: '/api/v1',
    withCredentials: true,
    timeout: 30000,
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
  })

  // 请求拦截器
  instance.interceptors.request.use((config: InternalAxiosRequestConfig) => {
    // 注入 X-Request-ID
    if (!config.headers['X-Request-ID']) {
      config.headers['X-Request-ID'] = crypto.randomUUID()
    }

    // 写操作注入 CSRF Token
    const method = (config.method ?? 'get').toLowerCase()
    if (CSRF_METHODS.has(method) && !config.headers['X-CSRF-Token']) {
      const csrf = readCsrfToken()
      if (csrf) {
        config.headers['X-CSRF-Token'] = csrf
      }
    }

    return config
  })

  // 响应拦截器
  instance.interceptors.response.use(
    (response) => {
      return response
    },
    (error: AxiosError<ApiResponse<unknown>>) => {
      // 网络错误（无响应）
      if (!error.response) {
        return Promise.reject(
          new ApiError(
            0,
            'NETWORK_ERROR',
            '网络连接失败，请检查网络后重试',
            '',
          ),
        )
      }

      const { status, data, headers } = error.response

      // 响应体不是标准 JSON 格式
      if (!data || typeof data !== 'object' || !('code' in data)) {
        return Promise.reject(
          new ApiError(
            status,
            'UNEXPECTED_RESPONSE',
            '服务端返回了非预期的响应格式',
            '',
          ),
        )
      }

      const code = (data.code as string) ?? 'UNKNOWN'
      const message =
        (data.message as string) ?? '请求失败，请稍后重试'
      const requestId = (data.request_id as string) ?? ''

      // 提取字段错误
      let fieldErrors: ApiFieldError[] = []
      if (
        data.data &&
        typeof data.data === 'object' &&
        'errors' in data.data &&
        Array.isArray(data.data.errors)
      ) {
        fieldErrors = data.data.errors as ApiFieldError[]
      }

      // 提取 Retry-After
      const retryAfter = headers['retry-after']
        ? parseInt(headers['retry-after'], 10)
        : null

      const apiError = new ApiError(
        status,
        code,
        message,
        requestId,
        fieldErrors,
        retryAfter,
        (data.data as Record<string, unknown>) ?? null,
      )

      // 统一处理 401 跳转（只触发一次）
      if (status === 401 && !authRedirectPending) {
        authRedirectPending = true
        // 动态导入避免循环依赖
        import('@/stores/auth.store').then(({ useAuthStore }) => {
          const authStore = useAuthStore()
          // DEV 模式下如果已模拟登录，跳过清除（避免竞态）
          if (import.meta.env.DEV && authStore.isAuthenticated) {
            resetAuthRedirect()
            return
          }
          authStore.clearSession()
          import('@/router').then(({ router }) => {
            const currentPath = router.currentRoute.value.fullPath
            router.push({
              path: '/login',
              query: currentPath !== '/login' ? { redirect: currentPath } : {},
            })
            resetAuthRedirect()
          })
        }).catch(() => {
          resetAuthRedirect()
        })
      }

      return Promise.reject(apiError)
    },
  )

  return instance
}

export const httpClient = createAxiosInstance()

/**
 * 解包统一响应 { code, message, data, request_id } → data
 */
export function unwrap<T>(response: { data: ApiResponse<T> }): T {
  return response.data.data
}

/**
 * 带解包的 GET 请求
 */
export async function apiGet<T>(
  url: string,
  params?: Record<string, unknown>,
): Promise<T> {
  const response = await httpClient.get<ApiResponse<T>>(url, { params })
  return unwrap(response)
}

/**
 * 带解包的 POST 请求
 */
export async function apiPost<T>(
  url: string,
  data?: unknown,
): Promise<T> {
  const response = await httpClient.post<ApiResponse<T>>(url, data)
  return unwrap(response)
}

/**
 * 带解包的 PUT 请求
 */
export async function apiPut<T>(
  url: string,
  data?: unknown,
): Promise<T> {
  const response = await httpClient.put<ApiResponse<T>>(url, data)
  return unwrap(response)
}

/**
 * 带解包的 DELETE 请求
 */
export async function apiDelete<T>(
  url: string,
  data?: unknown,
): Promise<T> {
  const response = await httpClient.delete<ApiResponse<T>>(url, { data })
  return unwrap(response)
}
