<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'
import { ApiError } from '@/services/http/errors'
import type { FormInstance, FormRules } from 'element-plus'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const errorMsg = ref('')

const form = reactive({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
  ],
}

async function handleSubmit() {
  if (submitting.value) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  errorMsg.value = ''

  try {
    await authStore.login(form.username, form.password)
    const redirect = (route.query.redirect as string) ?? '/projects'
    router.push(redirect)
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.code === 'SYSTEM_NOT_INITIALIZED') {
        router.push('/system/init')
        return
      }
      if (e.isRateLimited && e.retryAfter) {
        errorMsg.value = `登录过于频繁，请 ${e.retryAfter} 秒后重试`
      } else {
        errorMsg.value = e.message
      }
    } else {
      errorMsg.value = '登录失败，请稍后重试'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-page__card">
      <h1 class="login-page__title">ASA System</h1>
      <p class="login-page__subtitle">自动化安全评估系统</p>

      <el-alert
        v-if="errorMsg"
        :title="errorMsg"
        type="error"
        show-icon
        :closable="true"
        class="login-page__error"
        @close="errorMsg = ''"
      />

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入用户名"
            :disabled="submitting"
            autocomplete="username"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :disabled="submitting"
            show-password
            autocomplete="current-password"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>

        <el-button
          type="primary"
          :loading="submitting"
          class="login-page__submit"
          @click="handleSubmit"
        >
          {{ submitting ? '登录中...' : '登录' }}
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-page);
  padding: var(--spacing-lg);
}

.login-page__card {
  width: 100%;
  max-width: 420px;
  background: var(--color-bg-card);
  padding: var(--spacing-2xl);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}

.login-page__title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  text-align: center;
  color: var(--color-primary);
  margin-bottom: var(--spacing-xs);
}

.login-page__subtitle {
  font-size: var(--font-size-base);
  text-align: center;
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-xl);
}

.login-page__error {
  margin-bottom: var(--spacing-lg);
}

.login-page__submit {
  width: 100%;
  margin-top: var(--spacing-sm);
}
</style>
