<script setup lang="ts">
interface Props {
  title?: string
  description?: string
  actionText?: string
}

withDefaults(defineProps<Props>(), {
  title: '暂无数据',
  description: '',
  actionText: '',
})

const emit = defineEmits<{
  action: []
}>()
</script>

<template>
  <div class="empty-state">
    <el-icon class="empty-state__icon" :size="48">
      <FolderOpened />
    </el-icon>
    <p class="empty-state__title">{{ title }}</p>
    <p v-if="description" class="empty-state__description">
      {{ description }}
    </p>
    <el-button
      v-if="actionText"
      type="primary"
      class="empty-state__action"
      @click="emit('action')"
    >
      {{ actionText }}
    </el-button>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2xl) var(--spacing-lg);
  text-align: center;
}

.empty-state__icon {
  color: var(--color-text-placeholder);
  margin-bottom: var(--spacing-md);
}

.empty-state__title {
  font-size: var(--font-size-md);
  color: var(--color-text-secondary);
  font-weight: 500;
}

.empty-state__description {
  font-size: var(--font-size-sm);
  color: var(--color-text-placeholder);
  margin-top: var(--spacing-sm);
  max-width: 360px;
}

.empty-state__action {
  margin-top: var(--spacing-lg);
}
</style>
