<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'
import { ApiError } from '@/services/http/errors'
import type { FormInstance, FormRules } from 'element-plus'

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
    { required: true, message: '请输入管理员用户名', trigger: 'blur' },
    { min: 1, max: 64, message: '用户名长度为 1 至 64 个字符', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 1, message: '密码不能为空', trigger: 'blur' },
  ],
}

async function handleSubmit() {
  if (submitting.value) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  errorMsg.value = ''

  try {
    await authStore.initSystem(form.username, form.password)
    router.push('/login')
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.code === 'SYSTEM_ALREADY_INITIALIZED') {
        router.push('/login')
        return
      }
      errorMsg.value = e.message
    } else {
      errorMsg.value = '初始化失败，请稍后重试'
    }
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="init-page">
    <div class="init-page__card">
      <h1 class="init-page__title">系统初始化</h1>
      <p class="init-page__subtitle">
        首次使用前请创建管理员账户
      </p>

      <el-alert
        v-if="errorMsg"
        :title="errorMsg"
        type="error"
        show-icon
        :closable="true"
        class="init-page__error"
        @close="errorMsg = ''"
      />

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="管理员用户名" prop="username">
          <el-input
            v-model="form.username"
            placeholder="请输入管理员用户名"
            :disabled="submitting"
            maxlength="64"
            autocomplete="username"
          />
        </el-form-item>

        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            :disabled="submitting"
            show-password
            autocomplete="new-password"
          />
        </el-form-item>

        <el-button
          type="primary"
          :loading="submitting"
          class="init-page__submit"
          @click="handleSubmit"
        >
          {{ submitting ? '初始化中...' : '初始化系统' }}
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.init-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-page);
  padding: var(--spacing-lg);
}

.init-page__card {
  width: 100%;
  max-width: 420px;
  background: var(--color-bg-card);
  padding: var(--spacing-2xl);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
}

.init-page__title {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  text-align: center;
  color: var(--color-text-primary);
  margin-bottom: var(--spacing-sm);
}

.init-page__subtitle {
  font-size: var(--font-size-base);
  text-align: center;
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-xl);
}

.init-page__error {
  margin-bottom: var(--spacing-lg);
}

.init-page__submit {
  width: 100%;
  margin-top: var(--spacing-sm);
}
</style>
