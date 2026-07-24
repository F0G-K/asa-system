<script setup lang="ts">
import { computed } from 'vue'
import type { StatusDisplay } from '@/contracts'

interface Props {
  value: string
  map: Record<string, StatusDisplay>
  size?: 'small' | 'default' | 'large'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'default',
})

const display = computed<StatusDisplay>(() => {
  return (
    props.map[props.value] ?? {
      text: '未知状态',
      color: 'var(--color-text-secondary)',
      ariaLabel: `未知状态: ${props.value}`,
    }
  )
})
</script>

<template>
  <span
    class="status-tag"
    :class="[`status-tag--${size}`]"
    :style="{ '--tag-color': display.color }"
    :aria-label="display.ariaLabel ?? display.text"
  >
    <span class="status-tag__dot" />
    <span class="status-tag__text">{{ display.text }}</span>
  </span>
</template>

<style scoped>
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 500;
  white-space: nowrap;
}

.status-tag--small {
  font-size: var(--font-size-xs);
}

.status-tag--default {
  font-size: var(--font-size-base);
}

.status-tag--large {
  font-size: var(--font-size-md);
}

.status-tag__dot {
  width: 8px;
  height: 8px;
  border-radius: var(--radius-round);
  background: var(--tag-color);
  flex-shrink: 0;
}

.status-tag--small .status-tag__dot {
  width: 6px;
  height: 6px;
}

.status-tag--large .status-tag__dot {
  width: 10px;
  height: 10px;
}

.status-tag__text {
  color: var(--tag-color);
}
</style>
