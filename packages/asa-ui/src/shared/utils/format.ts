import dayjs from 'dayjs'
import utc from 'dayjs/plugin/utc'

dayjs.extend(utc)

/**
 * 格式化 ISO 8601 UTC 时间为可读日期时间
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '-'
  return dayjs.utc(iso).local().format('YYYY-MM-DD HH:mm:ss')
}

/**
 * 格式化 ISO 8601 UTC 时间为可读日期
 */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '-'
  return dayjs.utc(iso).local().format('YYYY-MM-DD')
}

/**
 * 格式化 ISO 8601 UTC 时间为可读时间
 */
export function formatTime(iso: string | null | undefined): string {
  if (!iso) return '-'
  return dayjs.utc(iso).local().format('HH:mm:ss')
}

/**
 * 格式化字节数为人类可读
 */
export function formatBytes(bytes: number | null | undefined): string {
  if (bytes == null || bytes < 0) return '-'
  if (bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const k = 1024
  const i = Math.min(Math.floor(Math.log(bytes) / Math.log(k)), units.length - 1)
  const value = bytes / Math.pow(k, i)
  return `${value.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

/**
 * 格式化 CPU 百分比
 */
export function formatCpuPercent(value: number | null | undefined): string {
  if (value == null) return '-'
  return `${value.toFixed(1)}%`
}

/**
 * 格式化 token 数量
 */
export function formatTokenCount(count: number | null | undefined): string {
  if (count == null) return '-'
  if (count < 1000) return String(count)
  if (count < 1_000_000) return `${(count / 1000).toFixed(1)}K`
  return `${(count / 1_000_000).toFixed(1)}M`
}

/**
 * 计算从某时间到现在的时长描述
 */
export function formatDuration(iso: string | null | undefined): string {
  if (!iso) return '-'
  const start = dayjs.utc(iso)
  const now = dayjs.utc()
  const diffSec = now.diff(start, 'second')
  if (diffSec < 60) return `${diffSec} 秒`
  const diffMin = Math.floor(diffSec / 60)
  if (diffMin < 60) return `${diffMin} 分钟`
  const diffHour = Math.floor(diffMin / 60)
  if (diffHour < 24) return `${diffHour} 小时 ${diffMin % 60} 分钟`
  const diffDay = Math.floor(diffHour / 24)
  return `${diffDay} 天 ${diffHour % 24} 小时`
}
