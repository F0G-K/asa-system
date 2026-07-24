<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import type { FormInstance, FormRules } from 'element-plus'
import { createProject } from '../api/project.api'
import { ApiError } from '@/services/http/errors'
import AppPageHeader from '@/shared/components/AppPageHeader.vue'

const router = useRouter()

const formRef = ref<FormInstance>()
const submitting = ref(false)
const errorMsg = ref('')
const fieldErrors = ref<Record<string, string>>({})
const enabledEnvTypes = ref<string[]>(['python-3.12', 'node-22'])

const form = reactive({
  project_name: '',
  source_type: 'local' as 'local' | 'repository',
  source_path: '',
  task_content: '',
  environment_type: 'python-3.12',
})

const sourcePathPlaceholder = (): string => {
  return form.source_type === 'local'
    ? '例如：./demo-app'
    : '例如：https://git.example.com/team/project.git'
}

const sourcePathHelp = (): string => {
  return form.source_type === 'local'
    ? '授权根目录内的相对路径'
    : 'HTTPS 或 SSH 仓库地址（不含内联凭证）'
}

const rules: FormRules = {
  project_name: [
    { required: true, message: '请输入项目名称', trigger: 'blur' },
    { min: 1, max: 128, message: '项目名称长度为 1 至 128 个字符', trigger: 'blur' },
  ],
  source_type: [
    { required: true, message: '请选择源码类型', trigger: 'change' },
  ],
  source_path: [
    { required: true, message: '请输入源码地址', trigger: 'blur' },
  ],
  task_content: [
    { required: true, message: '请输入评估任务说明', trigger: 'blur' },
  ],
  environment_type: [
    { required: true, message: '请选择隔离环境类型', trigger: 'change' },
  ],
}

async function handleSubmit() {
  if (submitting.value) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  errorMsg.value = ''
  fieldErrors.value = {}

  try {
    const result = await createProject({
      project_name: form.project_name,
      source_type: form.source_type,
      source_path: form.source_path,
      task_content: form.task_content,
      environment_type: form.environment_type,
    })
    router.push(`/projects/${result.id}`)
  } catch (e) {
    if (e instanceof ApiError) {
      errorMsg.value = e.message
      // 映射字段错误
      for (const fe of e.fieldErrors) {
        const fieldName = fe.field.replace('body.', '')
        fieldErrors.value[fieldName] = fe.reason
      }
    } else {
      errorMsg.value = '创建失败，请稍后重试'
    }
  } finally {
    submitting.value = false
  }
}

function handleCancel() {
  router.back()
}

// Field error mapping handled via form rules
</script>

<template>
  <div class="page-container">
    <AppPageHeader
      title="创建项目"
      subtitle="登记源码信息与评估任务范围"
    />

    <el-alert
      v-if="errorMsg && Object.keys(fieldErrors).length === 0"
      :title="errorMsg"
      type="error"
      show-icon
      :closable="true"
      class="create-error"
      @close="errorMsg = ''"
    />

    <div class="create-form-card">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        size="large"
        @submit.prevent="handleSubmit"
      >
        <!-- 项目名称 -->
        <el-form-item label="项目名称" prop="project_name">
          <el-input
            v-model="form.project_name"
            placeholder="请输入项目名称"
            :disabled="submitting"
            maxlength="128"
            show-word-limit
          />
        </el-form-item>

        <!-- 源码类型 -->
        <el-form-item label="源码类型" prop="source_type">
          <el-radio-group
            v-model="form.source_type"
            :disabled="submitting"
          >
            <el-radio value="local">本地源码</el-radio>
            <el-radio value="repository">Git 仓库</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 源码地址 -->
        <el-form-item label="源码地址" prop="source_path">
          <el-input
            v-model="form.source_path"
            :placeholder="sourcePathPlaceholder()"
            :disabled="submitting"
          />
          <template #extra>
            <span class="form-help">{{ sourcePathHelp() }}</span>
          </template>
        </el-form-item>

        <!-- 评估任务说明 -->
        <el-form-item label="评估任务说明" prop="task_content">
          <el-input
            v-model="form.task_content"
            type="textarea"
            :rows="4"
            placeholder="描述评估范围和重点关注方向，例如：评估支付回调、订单权限校验和数据库访问层，重点检查注入与越权风险。"
            :disabled="submitting"
          />
        </el-form-item>

        <!-- 隔离环境 -->
        <el-form-item label="隔离环境类型" prop="environment_type">
          <el-select
            v-model="form.environment_type"
            :disabled="submitting"
            style="width: 100%"
          >
            <el-option
              v-for="env in enabledEnvTypes"
              :key="env"
              :label="env"
              :value="env"
            />
          </el-select>
          <template #extra>
            <span class="form-help">选择与源码匹配的运行环境</span>
          </template>
        </el-form-item>

        <!-- 操作按钮 -->
        <div class="create-form-actions">
          <el-button
            :disabled="submitting"
            @click="handleCancel"
          >
            取消
          </el-button>
          <el-button
            type="primary"
            :loading="submitting"
            @click="handleSubmit"
          >
            {{ submitting ? '创建中...' : '创建项目' }}
          </el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.create-error {
  margin-bottom: var(--spacing-lg);
}

.create-form-card {
  max-width: 720px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: var(--spacing-xl);
}

.form-help {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.create-form-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-xl);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-border-lighter);
}
</style>
