<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
  <div class="error-page">
    <div class="error-page__code">403</div>
    <h1 class="error-page__title">无权访问</h1>
    <p class="error-page__desc">
      您没有访问此页面的权限。如需帮助，请联系系统管理员。
    </p>
    <el-button type="primary" @click="router.push('/projects')">
      返回项目列表
    </el-button>
  </div>
</template>

<style scoped>
.error-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-2xl);
  text-align: center;
}

.error-page__code {
  font-size: 96px;
  font-weight: 800;
  color: var(--color-border-light);
  line-height: 1;
  margin-bottom: var(--spacing-lg);
}

.error-page__title {
  font-size: var(--font-size-2xl);
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}

.error-page__desc {
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-xl);
  max-width: 400px;
}
</style>
