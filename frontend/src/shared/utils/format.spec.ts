import { describe, it, expect } from 'vitest'
import {
  formatDateTime,
  formatDate,
  formatTime,
  formatBytes,
  formatCpuPercent,
  formatTokenCount,
  formatDuration,
} from './format'

describe('formatDateTime', () => {
  it('returns - for null/undefined/empty', () => {
    expect(formatDateTime(null)).toBe('-')
    expect(formatDateTime(undefined)).toBe('-')
    expect(formatDateTime('')).toBe('-')
  })

  it('formats valid ISO 8601 UTC', () => {
    const result = formatDateTime('2026-07-24T08:30:00Z')
    expect(result).toContain('2026-07-24')
    expect(result).toContain(':')
  })
})

describe('formatDate', () => {
  it('returns - for null', () => {
    expect(formatDate(null)).toBe('-')
  })

  it('formats date portion', () => {
    const result = formatDate('2026-07-24T08:30:00Z')
    expect(result).toBe('2026-07-24')
  })
})

describe('formatTime', () => {
  it('returns - for null', () => {
    expect(formatTime(null)).toBe('-')
  })

  it('formats time portion', () => {
    const result = formatTime('2026-07-24T08:30:00Z')
    expect(result).toContain(':')
  })
})

describe('formatBytes', () => {
  it('returns - for null/undefined', () => {
    expect(formatBytes(null)).toBe('-')
    expect(formatBytes(undefined)).toBe('-')
  })

  it('returns - for negative values', () => {
    expect(formatBytes(-1)).toBe('-')
    expect(formatBytes(-1024)).toBe('-')
  })

  it('returns 0 B for 0', () => {
    expect(formatBytes(0)).toBe('0 B')
  })

  it('formats bytes', () => {
    expect(formatBytes(500)).toBe('500 B')
  })

  it('formats KB', () => {
    expect(formatBytes(1024)).toBe('1.0 KB')
  })

  it('formats MB', () => {
    expect(formatBytes(1048576)).toBe('1.0 MB')
  })

  it('formats GB', () => {
    expect(formatBytes(1073741824)).toBe('1.0 GB')
  })

  it('formats TB', () => {
    expect(formatBytes(1099511627776)).toBe('1.0 TB')
  })

  it('formats fractional KB', () => {
    expect(formatBytes(1536)).toBe('1.5 KB')
  })

  it('formats fractional MB', () => {
    expect(formatBytes(1572864)).toBe('1.5 MB')
  })
})

describe('formatCpuPercent', () => {
  it('returns - for null/undefined', () => {
    expect(formatCpuPercent(null)).toBe('-')
    expect(formatCpuPercent(undefined)).toBe('-')
  })

  it('formats percent with one decimal', () => {
    expect(formatCpuPercent(132.456)).toBe('132.5%')
  })
})

describe('formatTokenCount', () => {
  it('returns - for null', () => {
    expect(formatTokenCount(null)).toBe('-')
  })

  it('returns raw number for < 1000', () => {
    expect(formatTokenCount(500)).toBe('500')
  })

  it('formats K for thousands', () => {
    expect(formatTokenCount(28450)).toBe('28.4K')
  })

  it('formats M for millions', () => {
    expect(formatTokenCount(2_500_000)).toBe('2.5M')
  })
})

describe('formatDuration', () => {
  it('returns - for null', () => {
    expect(formatDuration(null)).toBe('-')
  })

  it('returns seconds for < 1 minute', () => {
    const recent = new Date().toISOString()
    const result = formatDuration(recent)
    expect(result).toContain('秒')
  })

  it('returns minutes for < 1 hour', () => {
    // 30 minutes ago
    const ago = new Date(Date.now() - 30 * 60 * 1000).toISOString()
    const result = formatDuration(ago)
    expect(result).toContain('分钟')
    expect(result).not.toContain('小时')
  })

  it('returns hours for < 1 day', () => {
    // 3 hours ago
    const ago = new Date(Date.now() - 3 * 3600 * 1000).toISOString()
    const result = formatDuration(ago)
    expect(result).toContain('小时')
    expect(result).toContain('分钟')
  })

  it('returns days for >= 1 day', () => {
    // 2 days ago
    const ago = new Date(Date.now() - 2 * 86400 * 1000).toISOString()
    const result = formatDuration(ago)
    expect(result).toContain('天')
    expect(result).toContain('小时')
  })
})
