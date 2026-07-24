<script setup lang="ts">
interface Props {
  variant?: 'table' | 'detail' | 'card' | 'chart'
  rows?: number
}

withDefaults(defineProps<Props>(), {
  variant: 'table',
  rows: 5,
})
</script>

<template>
  <div v-if="variant === 'table'" class="skeleton-table">
    <div
      v-for="i in rows"
      :key="i"
      class="skeleton-table__row"
      :style="{ animationDelay: `${i * 0.1}s` }"
    >
      <el-skeleton :rows="1" animated />
    </div>
  </div>

  <div v-else-if="variant === 'detail'" class="skeleton-detail">
    <el-skeleton :rows="2" animated />
    <el-skeleton :rows="3" animated style="margin-top: 16px" />
    <el-skeleton :rows="2" animated style="margin-top: 16px" />
  </div>

  <div v-else-if="variant === 'card'" class="skeleton-card">
    <el-skeleton :rows="4" animated />
  </div>

  <div v-else-if="variant === 'chart'" class="skeleton-chart">
    <el-skeleton :rows="1" animated />
    <div class="skeleton-chart__area">
      <el-skeleton :rows="6" animated />
    </div>
  </div>
</template>

<style scoped>
.skeleton-table__row {
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border-lighter);
}

.skeleton-detail {
  padding: var(--spacing-lg);
}

.skeleton-card {
  padding: var(--spacing-lg);
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
}

.skeleton-chart {
  padding: var(--spacing-lg);
}

.skeleton-chart__area {
  margin-top: var(--spacing-md);
  padding: var(--spacing-lg);
  background: var(--color-bg-page);
  border-radius: var(--radius-sm);
}
</style>
