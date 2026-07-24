<script setup lang="ts">
import { ref } from 'vue'

interface Props {
  code: string
  label?: string
  maxHeight?: string
}

withDefaults(defineProps<Props>(), {
  label: '',
  maxHeight: '400px',
})

const copied = ref(false)

async function handleCopy(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch {
    // 降级
  }
}
</script>

<template>
  <div class="code-block-wrapper">
    <div v-if="label" class="code-block__header">
      <span class="code-block__label">{{ label }}</span>
      <el-button text size="small" @click="handleCopy(code)">
        {{ copied ? '已复制' : '复制' }}
      </el-button>
    </div>
    <pre
      class="code-block"
      :style="{ maxHeight }"
    ><code>{{ code }}</code></pre>
  </div>
</template>

<style scoped>
.code-block-wrapper {
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  overflow: hidden;
}

.code-block__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--spacing-sm) var(--spacing-md);
  background: var(--color-bg-page);
  border-bottom: 1px solid var(--color-border-lighter);
}

.code-block__label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.code-block {
  margin: 0;
  padding: var(--spacing-md);
  font-family: var(--font-mono);
  font-size: var(--font-size-sm);
  line-height: 1.7;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  background: var(--color-fill-input);
  color: var(--color-text-primary);
}
</style>
