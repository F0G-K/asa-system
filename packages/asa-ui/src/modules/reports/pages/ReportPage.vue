<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { REPORT_STATUS_MAP, type StatusDisplay } from '@asa/contracts'
import { getReport, downloadReport } from '../api/report.api'
import { ApiError } from '@/services/http/errors'
import { formatDateTime } from '@/shared/utils/format'
import AppStatusTag from '@/shared/components/AppStatusTag.vue'
import AppPageHeader from '@/shared/components/AppPageHeader.vue'
import AppErrorBlock from '@/shared/components/AppErrorBlock.vue'
import AppLoadingSkeleton from '@/shared/components/AppLoadingSkeleton.vue'
import type { ReportData } from '@asa/contracts'

const route = useRoute()
const router = useRouter()
const projectId = route.params.projectId as string

const report = ref<ReportData | null>(null)
const loading = ref(false)
const error = ref<ApiError | null>(null)
const downloadLoading = ref('')
const activeTab = ref<'markdown' | 'html'>('markdown')

let pollTimer: ReturnType<typeof setInterval> | null = null

const isPending = computed(() => report.value?.report_status === 'pending')
const isGenerating = computed(() => report.value?.report_status === 'generating')
const isReady = computed(() => report.value?.report_status === 'ready')
const isFailed = computed(() => report.value?.report_status === 'failed')
const canDownload = computed(() => isReady.value && report.value?.download_available === true)

async function fetchReport() {
  loading.value = true
  error.value = null
  try {
    report.value = await getReport(projectId)
    // 如果未就绪，开始轮询
    if (report.value.report_status === 'pending' || report.value.report_status === 'generating') {
      startPolling()
    } else {
      stopPolling()
    }
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.isNotFound) {
        report.value = null
      } else {
        error.value = e
      }
    }
  } finally {
    loading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const data = await getReport(projectId)
      report.value = data
      if (data.report_status === 'ready' || data.report_status === 'failed') {
        stopPolling()
      }
    } catch {
      // 轮询失败不影响展示
    }
  }, 5000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

async function handleDownload(format: 'markdown' | 'html') {
  if (!canDownload.value) return
  downloadLoading.value = format
  try {
    const { blob, filename } = await downloadReport(projectId, format)
    // 创建下载链接
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) {
    // 下载失败提示
    if (e instanceof ApiError) {
      error.value = e
    }
  } finally {
    downloadLoading.value = ''
  }
}

onMounted(() => fetchReport())
onUnmounted(() => stopPolling())
</script>

<template>
  <div class="page-container">
    <AppPageHeader title="评估报告">
      <template #actions>
        <el-button @click="router.push(`/projects/${projectId}`)">
          返回详情
        </el-button>
      </template>
    </AppPageHeader>

    <AppLoadingSkeleton v-if="loading && !report" variant="detail" />

    <AppErrorBlock
      v-else-if="error"
      :message="error.message"
      :request-id="error.requestId"
      retryable
      @retry="fetchReport"
    />

    <!-- 报告不存在 -->
    <div v-else-if="!report" class="detail-section">
      <h2 class="detail-section__title">报告状态</h2>
      <p class="report-message">项目评估报告尚不存在。评估完成后系统将自动生成报告。</p>
      <div style="margin-top: var(--spacing-lg)">
        <el-button @click="router.push(`/projects/${projectId}/vulnerabilities`)">
          查看漏洞
        </el-button>
        <el-button @click="router.push(`/projects/${projectId}/attack-paths`)">
          查看攻击路径
        </el-button>
      </div>
    </div>

    <template v-else>
      <!-- 报告状态栏 -->
      <div class="detail-section">
        <div class="report-header">
          <div class="report-info">
            <span class="report-label">报告状态：</span>
            <AppStatusTag
              :value="report.report_status"
              :map="REPORT_STATUS_MAP as Record<string, StatusDisplay>"
            />
            <span v-if="report.version" class="report-version">
              版本 {{ report.version }}
            </span>
            <span class="report-time">
              最后更新：{{ formatDateTime(report.updated_at) }}
            </span>
          </div>
          <div v-if="canDownload" class="report-actions">
            <el-button
              :loading="downloadLoading === 'markdown'"
              @click="handleDownload('markdown')"
            >
              下载 Markdown
            </el-button>
            <el-button
              type="primary"
              :loading="downloadLoading === 'html'"
              @click="handleDownload('html')"
            >
              下载 HTML
            </el-button>
          </div>
        </div>
      </div>

      <!-- 生成中 -->
      <div v-if="isPending || isGenerating" class="detail-section report-status-center">
        <el-icon class="report-spinner" :size="48">
          <Loading />
        </el-icon>
        <p class="report-message">
          {{ isPending ? '报告排队等待生成...' : '报告正在生成中，请稍候...' }}
        </p>
        <el-progress
          :percentage="isPending ? 10 : 60"
          :indeterminate="true"
          :duration="3"
          style="width: 300px; margin-top: var(--spacing-lg)"
        />
      </div>

      <!-- 生成失败 -->
      <div v-else-if="isFailed" class="detail-section">
        <h2 class="detail-section__title">报告生成失败</h2>
        <el-alert
          :title="report.error_message ?? '报告生成过程中发生错误'"
          type="error"
          show-icon
          :closable="false"
        />
        <div class="report-error-actions">
          <el-button @click="router.push(`/projects/${projectId}/vulnerabilities`)">
            查看漏洞
          </el-button>
          <el-button @click="router.push(`/projects/${projectId}/attack-paths`)">
            查看攻击路径
          </el-button>
        </div>
      </div>

      <!-- 报告就绪 -->
      <div v-else-if="isReady" class="detail-section">
        <el-tabs v-model="activeTab">
          <el-tab-pane label="Markdown 预览" name="markdown" />
          <el-tab-pane label="HTML 预览" name="html" />
        </el-tabs>

        <div class="report-preview">
          <!-- Markdown 预览使用安全的纯文本渲染 -->
          <pre
            v-if="activeTab === 'markdown'"
            class="report-markdown"
          >{{ report.report_markdown }}</pre>

          <!-- HTML 预览使用隔离容器 -->
          <div
            v-else
            class="report-html"
          >
            <iframe
              :srcdoc="report.report_html ?? ''"
              sandbox="allow-same-origin"
              class="report-iframe"
              title="报告预览"
            />
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--spacing-md);
}

.report-info {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

.report-label {
  font-weight: 500;
  color: var(--color-text-secondary);
}

.report-version {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}

.report-time {
  font-size: var(--font-size-sm);
  color: var(--color-text-placeholder);
}

.report-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.report-status-center {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--spacing-2xl);
}

.report-spinner {
  color: var(--color-primary);
  animation: spin 1.5s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.report-message {
  font-size: var(--font-size-md);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-lg);
  text-align: center;
}

.report-error-actions {
  margin-top: var(--spacing-lg);
  display: flex;
  gap: var(--spacing-sm);
}

.report-preview {
  margin-top: var(--spacing-lg);
}

.report-markdown {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: var(--spacing-xl);
  font-family: var(--font-mono);
  font-size: var(--font-size-base);
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 600px;
  overflow-y: auto;
}

.report-html {
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  overflow: hidden;
}

.report-iframe {
  width: 100%;
  height: 600px;
  border: none;
}
</style>
