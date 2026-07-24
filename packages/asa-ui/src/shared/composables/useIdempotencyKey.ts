import { ref } from 'vue'

/**
 * 幂等键管理 composable。
 * 操作开始时生成 UUID，重试时复用，终态或新操作时更换。
 */
export function useIdempotencyKey() {
  const key = ref<string | null>(null)

  function generate(): string {
    const newKey = crypto.randomUUID()
    key.value = newKey
    return newKey
  }

  function getOrCreate(): string {
    if (!key.value) {
      key.value = crypto.randomUUID()
    }
    return key.value
  }

  function reset(): void {
    key.value = null
  }

  return {
    key,
    generate,
    getOrCreate,
    reset,
  }
}
