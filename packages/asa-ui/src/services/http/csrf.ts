/**
 * 从 Cookie 中读取 asa_csrf 值。
 * asa_session 是 HttpOnly，前端不应读取；但 asa_csrf 需要可读以注入请求头。
 */
export function readCsrfToken(): string | null {
  const match = document.cookie.match(/(?:^|;\s*)asa_csrf=([^;]*)/)
  return match?.[1] ?? null
}
