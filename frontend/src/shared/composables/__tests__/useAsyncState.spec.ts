import { describe, it, expect, vi, beforeEach } from 'vitest'
import { ref } from 'vue'
import { useAsyncState } from '../useAsyncState'
import { ApiError } from '@/services/http/errors'

describe('useAsyncState', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('initializes with null data, not loading, null error', () => {
    const fn = vi.fn().mockResolvedValue('result')
    const { data, loading, error } = useAsyncState(fn)

    expect(data.value).toBeNull()
    expect(loading.value).toBe(false)
    expect(error.value).toBeNull()
  })

  it('sets loading to true during execution', async () => {
    const fn = vi.fn().mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve('result'), 10)),
    )
    const { execute, loading } = useAsyncState(fn)

    const promise = execute()
    expect(loading.value).toBe(true)

    await promise
    expect(loading.value).toBe(false)
  })

  it('sets data on successful execution', async () => {
    const fn = vi.fn().mockResolvedValue({ name: 'test' })
    const { execute, data } = useAsyncState(fn)

    const result = await execute()
    expect(result).toEqual({ name: 'test' })
    expect(data.value).toEqual({ name: 'test' })
  })

  it('passes arguments to the wrapped function', async () => {
    const fn = vi.fn().mockResolvedValue('ok')
    const { execute } = useAsyncState(fn)

    await execute('arg1', 42, { key: 'val' })
    expect(fn).toHaveBeenCalledWith('arg1', 42, { key: 'val' })
  })

  it('sets ApiError on failed execution', async () => {
    const apiErr = new ApiError(404, 'NOT_FOUND', '不存在', 'r1')
    const fn = vi.fn().mockRejectedValue(apiErr)
    const { execute, error } = useAsyncState(fn)

    const result = await execute()
    expect(result).toBeNull()
    expect(error.value).toBe(apiErr)
  })

  it('wraps non-ApiError into ApiError', async () => {
    const fn = vi.fn().mockRejectedValue(new Error('原生错误'))
    const { execute, error } = useAsyncState(fn)

    await execute()
    expect(error.value).toBeInstanceOf(ApiError)
    expect(error.value!.code).toBe('UNKNOWN')
    expect(error.value!.message).toBe('原生错误')
  })

  it('wraps non-Error rejections', async () => {
    const fn = vi.fn().mockRejectedValue('字符串错误')
    const { execute, error } = useAsyncState(fn)

    await execute()
    expect(error.value).toBeInstanceOf(ApiError)
    expect(error.value!.code).toBe('UNKNOWN')
    expect(error.value!.message).toBe('未知错误')
  })

  it('discards stale responses (race condition)', async () => {
    // 第一次调用慢，第二次调用快
    let resolve1: (v: string) => void
    let resolve2: (v: string) => void
    const fn = vi
      .fn()
      .mockImplementationOnce(
        () => new Promise<string>((r) => { resolve1 = r }),
      )
      .mockImplementationOnce(
        () => new Promise<string>((r) => { resolve2 = r }),
      )

    const { execute, data } = useAsyncState(fn)

    const p1 = execute()
    const p2 = execute()

    // 第二次调用先返回
    resolve2!('result-2')
    await p2
    expect(data.value).toBe('result-2')

    // 第一次调用后返回，应被丢弃
    resolve1!('result-1')
    const r1 = await p1
    expect(r1).toBeNull()
    expect(data.value).toBe('result-2') // 未被覆盖
  })

  it('discards stale errors', async () => {
    let reject1!: (e: Error) => void
    let resolve2!: (v: string) => void
    const fn = vi
      .fn()
      .mockImplementationOnce(
        () => new Promise<string>((_, r) => { reject1 = r }),
      )
      .mockImplementationOnce(
        () => new Promise<string>((r) => { resolve2 = r }),
      )

    const { execute, error } = useAsyncState(fn)

    const p1 = execute()
    const p2 = execute()

    resolve2!('ok')
    await p2
    expect(error.value).toBeNull()

    reject1!(new Error('过期错误'))
    await p1
    expect(error.value).toBeNull() // 过期错误被丢弃
  })

  it('reset clears all state', async () => {
    const fn = vi.fn().mockResolvedValue('data')
    const { execute, reset, data, loading, error } = useAsyncState(fn)

    await execute()
    expect(data.value).toBe('data')

    reset()
    expect(data.value).toBeNull()
    expect(loading.value).toBe(false)
    expect(error.value).toBeNull()
  })

  it('loading stays false when stale call completes after reset', async () => {
    let resolve1!: (v: string) => void
    const fn = vi.fn().mockImplementationOnce(
      () => new Promise<string>((r) => { resolve1 = r }),
    )

    const { execute, reset, loading } = useAsyncState(fn)
    const p = execute()
    reset()
    resolve1!('ok')
    await p
    // reset 后 requestId 已递增，stale 结果不会更新 loading
    expect(loading.value).toBe(false)
  })
})
