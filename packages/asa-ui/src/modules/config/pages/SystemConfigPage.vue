<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { getSystemConfig, updateSystemConfig } from '../api/config.api'
import { ApiError } from '@/services/http/errors'
import { formatDateTime } from '@/shared/utils/format'
import AppPageHeader from '@/shared/components/AppPageHeader.vue'
import AppErrorBlock from '@/shared/components/AppErrorBlock.vue'
import AppLoadingSkeleton from '@/shared/components/AppLoadingSkeleton.vue'
import type { SystemConfigData, LlmSettings } from '@asa/contracts'

const config = ref<SystemConfigData | null>(null)
const loading = ref(false)
const error = ref<ApiError | null>(null)
const successMsg = ref('')
const submitting = ref(false)
const formError = ref('')

const LLM_DEFAULTS: LlmSettings = {
  api_base_url: 'https://api.openai.com/v1',
  api_key: '',
  model_name: 'gpt-4o',
  max_tokens: 4096,
  temperature: 0.7,
}

const form = reactive({
  default_timeout_seconds: null as number | null,
  max_concurrent_projects: null as number | null,
  log_retention_days: null as number | null,
  file_retention_days: null as number | null,
  enabled_environment_types: [] as string[],
  newEnvType: '',
  llm: { ...LLM_DEFAULTS } as LlmSettings,
})

async function fetchConfig() {
  loading.value = true
  error.value = null
  try {
    const data = await getSystemConfig()
    config.value = data
    form.default_timeout_seconds = data.default_timeout_seconds
    form.max_concurrent_projects = data.max_concurrent_projects
    form.log_retention_days = data.log_retention_days
    form.file_retention_days = data.file_retention_days
    form.enabled_environment_types = [...data.enabled_environment_types]

    const saved = (data.settings?.llm ?? {}) as Partial<LlmSettings>
    form.llm = { ...LLM_DEFAULTS, ...saved }
  } catch (e) {
    if (e instanceof ApiError) error.value = e
  } finally {
    loading.value = false
  }
}

function addEnvType() {
  const val = form.newEnvType.trim()
  if (val && !form.enabled_environment_types.includes(val)) {
    form.enabled_environment_types.push(val)
    form.newEnvType = ''
  }
}

function removeEnvType(index: number) {
  form.enabled_environment_types.splice(index, 1)
}

async function handleSubmit() {
  if (submitting.value || !config.value) return
  submitting.value = true
  formError.value = ''
  successMsg.value = ''

  try {
    const result = await updateSystemConfig({
      expected_version: config.value.version,
      default_timeout_seconds: form.default_timeout_seconds,
      max_concurrent_projects: form.max_concurrent_projects,
      log_retention_days: form.log_retention_days,
      file_retention_days: form.file_retention_days,
      enabled_environment_types: form.enabled_environment_types,
      settings: { ...config.value.settings, llm: form.llm },
    })
    config.value = result
    successMsg.value = '配置已更新'
    setTimeout(() => (successMsg.value = ''), 5000)
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.code === 'CONFIG_VERSION_CONFLICT') {
        formError.value = '配置已被其他管理员更新，请刷新页面后重试'
      } else {
        formError.value = e.message
      }
    }
  } finally {
    submitting.value = false
  }
}

onMounted(() => fetchConfig())
</script>

<template>
  <div class="page-container">
    <AppPageHeader
      title="系统配置"
      subtitle="管理评估参数、大模型 API、环境类型和保留策略"
    />

    <AppLoadingSkeleton v-if="loading" variant="detail" />

    <AppErrorBlock
      v-else-if="error"
      :message="error.message"
      :request-id="error.requestId"
      retryable
      @retry="fetchConfig"
    />

    <template v-else-if="config">
      <el-alert
        v-if="successMsg"
        :title="successMsg"
        type="success"
        show-icon
        :closable="true"
        class="config-alert"
        @close="successMsg = ''"
      />

      <el-alert
        v-if="formError"
        :title="formError"
        type="error"
        show-icon
        :closable="true"
        class="config-alert"
        @close="formError = ''"
      />

      <div class="config-form-card">
        <div class="config-meta">
          <span>当前版本：{{ config.version }}</span>
          <span>最后更新：{{ formatDateTime(config.updated_at) }}</span>
        </div>

        <el-form label-position="top" @submit.prevent="handleSubmit">
          <div class="config-grid">
            <el-form-item label="默认超时（秒）">
              <el-input-number
                v-model="form.default_timeout_seconds"
                :min="60"
                :max="86400"
                :step="60"
                :disabled="submitting"
                style="width: 100%"
              />
              <template #extra>
                <span class="form-help">单个项目的最大评估时长，60 至 86400 秒</span>
              </template>
            </el-form-item>

            <el-form-item label="最大并发项目数">
              <el-input-number
                v-model="form.max_concurrent_projects"
                :min="1"
                :max="20"
                :disabled="submitting"
                style="width: 100%"
              />
              <template #extra>
                <span class="form-help">同时运行的最大项目数量</span>
              </template>
            </el-form-item>

            <el-form-item label="日志保留天数">
              <el-input-number
                v-model="form.log_retention_days"
                :min="1"
                :max="365"
                :disabled="submitting"
                style="width: 100%"
              />
            </el-form-item>

            <el-form-item label="文件保留天数">
              <el-input-number
                v-model="form.file_retention_days"
                :min="1"
                :max="365"
                :disabled="submitting"
                style="width: 100%"
              />
            </el-form-item>
          </div>

          <!-- 大模型 API 配置 -->
          <div class="config-section">
            <h3 class="config-section__title">大模型 API 配置</h3>
            <p class="config-section__desc">
              配置评估系统调用的大语言模型接口，支持任意 OpenAI 兼容的 API 端点
            </p>

            <div class="config-grid">
              <el-form-item label="API 地址">
                <el-input
                  v-model="form.llm.api_base_url"
                  placeholder="https://api.openai.com/v1"
                  :disabled="submitting"
                />
                <template #extra>
                  <span class="form-help">OpenAI 兼容的 API 端点地址</span>
                </template>
              </el-form-item>

              <el-form-item label="API 密钥">
                <el-input
                  v-model="form.llm.api_key"
                  type="password"
                  placeholder="sk-..."
                  :disabled="submitting"
                  show-password
                />
                <template #extra>
                  <span class="form-help">密钥加密存储，不会在日志或前端暴露明文</span>
                </template>
              </el-form-item>

              <el-form-item label="模型名称">
                <el-input
                  v-model="form.llm.model_name"
                  placeholder="gpt-4o"
                  :disabled="submitting"
                />
                <template #extra>
                  <span class="form-help">大模型标识，如 gpt-4o、claude-3-opus、deepseek-chat</span>
                </template>
              </el-form-item>

              <el-form-item label="最大 Token 数">
                <el-input-number
                  v-model="form.llm.max_tokens"
                  :min="256"
                  :max="128000"
                  :step="256"
                  :disabled="submitting"
                  style="width: 100%"
                />
                <template #extra>
                  <span class="form-help">单次请求的最大输出 Token 数</span>
                </template>
              </el-form-item>

              <el-form-item label="温度 (Temperature)">
                <el-input-number
                  v-model="form.llm.temperature"
                  :min="0"
                  :max="2"
                  :step="0.1"
                  :precision="1"
                  :disabled="submitting"
                  style="width: 100%"
                />
                <template #extra>
                  <span class="form-help">0 = 确定性输出，2 = 最大随机性，建议 0.7</span>
                </template>
              </el-form-item>
            </div>
          </div>

          <!-- 环境类型 -->
          <el-form-item label="启用的隔离环境类型" style="margin-top: var(--spacing-lg)">
            <div class="env-input">
              <el-input
                v-model="form.newEnvType"
                placeholder="输入环境类型标识，如 python-3.12"
                :disabled="submitting"
                style="flex: 1"
                @keyup.enter="addEnvType"
              />
              <el-button
                :disabled="submitting || !form.newEnvType.trim()"
                @click="addEnvType"
              >
                添加
              </el-button>
            </div>
            <div v-if="form.enabled_environment_types.length > 0" class="env-tags">
              <el-tag
                v-for="(env, idx) in form.enabled_environment_types"
                :key="idx"
                closable
                :disable-transitions="false"
                type="info"
                @close="removeEnvType(idx)"
              >
                {{ env }}
              </el-tag>
            </div>
            <div v-else class="env-empty">
              暂未启用任何环境类型
            </div>
          </el-form-item>

          <div class="config-form-actions">
            <el-button
              type="primary"
              :loading="submitting"
              @click="handleSubmit"
            >
              {{ submitting ? '保存中...' : '保存配置' }}
            </el-button>
          </div>
        </el-form>
      </div>
    </template>
  </div>
</template>

<style scoped>
.config-alert {
  margin-bottom: var(--spacing-lg);
}

.config-form-card {
  max-width: 800px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: var(--spacing-xl);
}

.config-meta {
  display: flex;
  gap: var(--spacing-lg);
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-xl);
  padding-bottom: var(--spacing-md);
  border-bottom: 1px solid var(--color-border-lighter);
}

.config-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-lg);
}

.config-section {
  margin-top: var(--spacing-xl);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-border-lighter);
}

.config-section__title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--spacing-xs);
}

.config-section__desc {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin: 0 0 var(--spacing-lg);
}

.form-help {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
}

.env-input {
  display: flex;
  gap: var(--spacing-sm);
}

.env-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
}

.env-empty {
  font-size: var(--font-size-sm);
  color: var(--color-text-placeholder);
  margin-top: var(--spacing-sm);
}

.config-form-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--spacing-xl);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-border-lighter);
}

@media (max-width: 768px) {
  .config-grid {
    grid-template-columns: 1fr;
  }
}
</style>
