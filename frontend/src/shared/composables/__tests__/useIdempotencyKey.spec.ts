import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useIdempotencyKey } from '../useIdempotencyKey'

describe('useIdempotencyKey', () => {
  let counter = 0

  beforeEach(() => {
    counter = 0
    vi.spyOn(globalThis.crypto, 'randomUUID').mockImplementation(() => {
      counter++
      return `mock-uuid-${counter}`
    })
  })

  it('initializes with null key', () => {
    const { key } = useIdempotencyKey()
    expect(key.value).toBeNull()
  })

  it('generate creates a new key each time', () => {
    const { generate, key } = useIdempotencyKey()
    const first = generate()
    expect(key.value).toBe(first)
    expect(first).toMatch(/^mock-uuid-\d+$/)

    const second = generate()
    expect(key.value).toBe(second)
    expect(second).not.toBe(first)
  })

  it('getOrCreate returns same key across calls', () => {
    const { getOrCreate, key } = useIdempotencyKey()
    const first = getOrCreate()
    expect(key.value).toBe(first)

    const second = getOrCreate()
    expect(second).toBe(first)
  })

  it('getOrCreate generates a new key after reset', () => {
    const { getOrCreate, reset, key } = useIdempotencyKey()
    const first = getOrCreate()
    reset()
    expect(key.value).toBeNull()

    const second = getOrCreate()
    expect(second).not.toBe(first)
  })

  it('reset clears the key', () => {
    const { generate, reset, key } = useIdempotencyKey()
    generate()
    expect(key.value).not.toBeNull()
    reset()
    expect(key.value).toBeNull()
  })

  it('generate returns unique UUIDs on each call', () => {
    const { generate } = useIdempotencyKey()
    const a = generate()
    const b = generate()
    const c = generate()
    const set = new Set([a, b, c])
    expect(set.size).toBe(3)
  })
})
