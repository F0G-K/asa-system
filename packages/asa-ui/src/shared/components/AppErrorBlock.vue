<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  message?: string
  requestId?: string
  retryable?: boolean
  details?: string
}

const props = withDefaults(defineProps<Props>(), {
  message: '请求失败',
  requestId: '',
  retryable: false,
  details: '',
})

const emit = defineEmits<{
  retry: []
}>()

const showRequestId = computed(() => props.requestId.length > 0)

async function copyRequestId() {
  if (props.requestId) {
    try {
      await navigator.clipboard.writeText(props.requestId)
    } catch {
      // 降级：不处理
    }
  }
}
</script>

<template>
  <div class="error-block" role="alert">
    <div class="error-block__icon">
      <el-icon :size="24"><WarningFilled /></el-icon>
    </div>
    <div class="error-block__content">
      <p class="error-block__message">{{ message }}</p>
      <p v-if="details" class="error-block__details">{{ details }}</p>
      <div v-if="showRequestId" class="error-block__request-id">
        <span class="error-block__request-id-label">Request ID:</span>
        <code>{{ requestId }}</code>
        <el-button
          text
          size="small"
          @click="copyRequestId"
          aria-label="复制 Request ID"
        >
          复制
        </el-button>
      </div>
    </div>
    <div v-if="retryable" class="error-block__action">
      <el-button type="primary" @click="emit('retry')">
        重试
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.error-block {
  display: flex;
  align-items: flex-start;
  gap: var(--spacing-md);
  padding: var(--spacing-lg);
  background: rgba(255, 77, 79, 0.1);
  border: 1px solid rgba(255, 77, 79, 0.25);
  border-radius: var(--radius-md);
}

.error-block__icon {
  color: var(--color-danger);
  flex-shrink: 0;
  margin-top: 2px;
}

.error-block__content {
  flex: 1;
  min-width: 0;
}

.error-block__message {
  font-size: var(--font-size-base);
  color: var(--color-text-primary);
  font-weight: 500;
}

.error-block__details {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-xs);
}

.error-block__request-id {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  margin-top: var(--spacing-sm);
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.error-block__request-id code {
  font-family: var(--font-mono);
  background: rgba(255, 255, 255, 0.06);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

.error-block__action {
  flex-shrink: 0;
}
</style>
