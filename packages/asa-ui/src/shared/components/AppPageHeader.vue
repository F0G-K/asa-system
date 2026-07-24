<script setup lang="ts">
interface Props {
  title: string
  subtitle?: string
}

defineProps<Props>()
</script>

<template>
  <div class="page-header">
    <div>
      <h1 class="page-header__title">{{ title }}</h1>
      <p v-if="subtitle" class="page-header__subtitle">{{ subtitle }}</p>
    </div>
    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: var(--spacing-lg);
}

.page-header__title {
  font-size: var(--font-size-2xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.page-header__subtitle {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-xs);
}

.page-header__actions {
  display: flex;
  gap: var(--spacing-sm);
  flex-shrink: 0;
}
</style>
