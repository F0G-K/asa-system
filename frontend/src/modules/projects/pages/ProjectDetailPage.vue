<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  PROJECT_STATUS_MAP,
  CONTAINER_STATUS_MAP,
  REPORT_STATUS_MAP,
  PROJECT_ALLOWED_ACTIONS,
  type StatusDisplay,
} from '@/contracts'
import { getProjectDetail, startProject, stopProject, deleteProject } from '../api/project.api'
import { ApiError } from '@/services/http/errors'
import { formatDateTime } from '@/shared/utils/format'
import { useIdempotencyKey } from '@/shared/composables/useIdempotencyKey'
import AppStatusTag from '@/shared/components/AppStatusTag.vue'
import AppPageHeader from '@/shared/components/AppPageHeader.vue'
import AppErrorBlock from '@/shared/components/AppErrorBlock.vue'
import AppLoadingSkeleton from '@/shared/components/AppLoadingSkeleton.vue'
import AppConfirmDialog from '@/shared/components/AppConfirmDialog.vue'
import type { ProjectDetail } from '@/contracts'

const route = useRoute()
const router = useRouter()

const projectId = route.params.projectId as string

// ===== State =====
const project = ref<ProjectDetail | null>(null)
const loading = ref(false)
const error = ref<ApiError | null>(null)
const actionLoading = ref('')
const actionMsg = ref('')

// 弹窗
const stopDialogVisible = ref(false)
const stopReason = ref('')
const deleteDialogVisible = ref(false)

// 幂等键
const startKey = useIdempotencyKey()
const stopKey = useIdempotencyKey()
const deleteKey = useIdempotencyKey()

// 轮询定时器
let pollTimer: ReturnType<typeof setInterval> | null = null

// ===== Computed =====
const isStopRequested = computed(
  () => project.value?.stop_requested_at != null,
)

const allowedActions = computed(() => {
  if (!project.value) return []
  return PROJECT_ALLOWED_ACTIONS[project.value.project_status] ?? []
})

const canStart = computed(() => allowedActions.value.includes('start'))
const canStop = computed(() => allowedActions.value.includes('stop'))
const canDelete = computed(() => allowedActions.value.includes('delete'))

// ===== Actions =====
async function fetchDetail() {
  loading.value = true
  error.value = null
  try {
    const data = await getProjectDetail(projectId)
    project.value = data
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.isNotFound) {
        router.replace({ name: 'NotFound' })
        return
      }
      error.value = e
    }
  } finally {
    loading.value = false
  }
}

async function handleStart() {
  actionLoading.value = 'start'
  actionMsg.value = ''
  try {
    startKey.getOrCreate()
    await startProject(projectId)
    actionMsg.value = '启动请求已受理'
    startKey.reset()
    startPolling()
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.isConflict) {
        actionMsg.value = e.message
      } else {
        actionMsg.value = '启动失败：' + e.message
      }
    }
  } finally {
    actionLoading.value = ''
  }
}

async function handleStop() {
  stopDialogVisible.value = false
  actionLoading.value = 'stop'
  actionMsg.value = ''
  try {
    stopKey.getOrCreate()
    await stopProject(projectId, stopReason.value || null)
    actionMsg.value = '停止请求已受理'
    stopKey.reset()
    stopReason.value = ''
    startPolling()
  } catch (e) {
    if (e instanceof ApiError) {
      actionMsg.value = e.message
    }
  } finally {
    actionLoading.value = ''
  }
}

async function handleDelete() {
  deleteDialogVisible.value = false
  actionLoading.value = 'delete'
  actionMsg.value = ''
  try {
    deleteKey.getOrCreate()
    await deleteProject(projectId, project.value!.project_name)
    actionMsg.value = '删除请求已受理'
    // 跳回列表
    setTimeout(() => router.push('/projects'), 1500)
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.code === 'PROJECT_NAME_CONFIRMATION_MISMATCH') {
        actionMsg.value = '项目名称不匹配，请重试'
      } else {
        actionMsg.value = e.message
      }
    }
  } finally {
    actionLoading.value = ''
  }
}

function startPolling() {
  stopPolling()
  pollTimer = setInterval(async () => {
    try {
      const data = await getProjectDetail(projectId)
      project.value = data
      // 当状态不再运行中，停止轮询
      if (
        data.project_status !== 'running' &&
        !data.stop_requested_at
      ) {
        stopPolling()
        actionMsg.value = ''
      }
    } catch {
      // 轮询失败不处理
    }
  }, 3000)
}

function stopPolling() {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

function goToMonitor() {
  router.push(`/projects/${projectId}/monitor`)
}

function goToVulnerabilities() {
  router.push(`/projects/${projectId}/vulnerabilities`)
}

function goToReport() {
  router.push(`/projects/${projectId}/report`)
}

onMounted(() => {
  fetchDetail()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<template>
  <div class="page-container">
    <!-- Loading -->
    <AppLoadingSkeleton v-if="loading && !project" variant="detail" />

    <!-- Error -->
    <AppErrorBlock
      v-else-if="error"
      :message="error.message"
      :request-id="error.requestId"
      retryable
      @retry="fetchDetail"
    />

    <template v-else-if="project">
      <!-- Header -->
      <AppPageHeader :title="project.project_name">
        <template #actions>
          <el-button
            v-if="canStart"
            type="primary"
            :loading="actionLoading === 'start'"
            @click="handleStart"
          >
            启动评估
          </el-button>
          <el-button
            v-if="canStop"
            type="warning"
            :loading="actionLoading === 'stop'"
            @click="stopDialogVisible = true"
          >
            停止评估
          </el-button>
          <el-button
            v-if="project.project_status === 'running'"
            type="success"
            @click="goToMonitor"
          >
            实时监控
          </el-button>
          <el-button
            v-if="allowedActions.includes('results')"
            @click="goToVulnerabilities"
          >
            查看漏洞
          </el-button>
          <el-button
            v-if="allowedActions.includes('report')"
            @click="goToReport"
          >
            查看报告
          </el-button>
          <el-button
            v-if="canDelete"
            type="danger"
            :loading="actionLoading === 'delete'"
            @click="deleteDialogVisible = true"
          >
            删除项目
          </el-button>
        </template>
      </AppPageHeader>

      <!-- 操作消息 -->
      <el-alert
        v-if="actionMsg"
        :title="actionMsg"
        :type="actionMsg.includes('失败') ? 'error' : 'success'"
        show-icon
        :closable="true"
        class="detail-alert"
        @close="actionMsg = ''"
      />

      <div class="detail-grid">
        <!-- 基本信息 -->
        <div class="detail-section">
          <h2 class="detail-section__title">基本信息</h2>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="项目状态">
              <AppStatusTag
                :value="project.project_status"
                :map="PROJECT_STATUS_MAP as Record<string, StatusDisplay>"
              />
              <el-tag
                v-if="isStopRequested && project.project_status === 'running'"
                type="warning"
                size="small"
                style="margin-left: 8px"
                effect="plain"
              >
                停止中
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="源码类型">
              {{ project.source_type === 'local' ? '本地源码' : 'Git 仓库' }}
            </el-descriptions-item>
            <el-descriptions-item label="源码地址" :span="2">
              <code>{{ project.source_path }}</code>
            </el-descriptions-item>
            <el-descriptions-item label="隔离环境">
              <el-tag size="small" type="info" effect="plain">
                {{ project.environment_type }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="报告状态">
              <AppStatusTag
                v-if="project.report_status"
                :value="project.report_status"
                :map="REPORT_STATUS_MAP as Record<string, StatusDisplay>"
                size="small"
              />
              <span v-else>-</span>
            </el-descriptions-item>
            <el-descriptions-item label="创建时间">
              {{ formatDateTime(project.created_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="更新时间">
              {{ formatDateTime(project.updated_at) }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 评估任务 -->
        <div class="detail-section">
          <h2 class="detail-section__title">评估任务</h2>
          <p class="task-content">{{ project.task_content }}</p>
        </div>

        <!-- 运行环境 -->
        <div v-if="project.runtime" class="detail-section">
          <h2 class="detail-section__title">运行环境</h2>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="环境标识">
              {{ project.runtime.runtime_identifier ?? '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="容器状态">
              <AppStatusTag
                :value="project.runtime.container_status"
                :map="CONTAINER_STATUS_MAP as Record<string, StatusDisplay>"
                size="small"
              />
            </el-descriptions-item>
            <el-descriptions-item label="启动时间">
              {{ formatDateTime(project.runtime.started_at) }}
            </el-descriptions-item>
            <el-descriptions-item label="停止时间">
              {{ formatDateTime(project.runtime.stopped_at) }}
            </el-descriptions-item>
            <el-descriptions-item
              v-if="project.runtime.error_message"
              label="错误信息"
              :span="2"
            >
              <span class="error-text">{{ project.runtime.error_message }}</span>
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 统计 -->
        <div class="detail-section">
          <h2 class="detail-section__title">评估统计</h2>
          <div class="stat-cards">
            <div class="stat-card">
              <div class="stat-card__num">
                {{ project.statistics.vulnerability_count }}
              </div>
              <div class="stat-card__label">漏洞总数</div>
            </div>
            <div class="stat-card stat-card--success">
              <div class="stat-card__num">
                {{ project.statistics.verified_vulnerability_count }}
              </div>
              <div class="stat-card__label">已验证漏洞</div>
            </div>
            <div class="stat-card stat-card--warning">
              <div class="stat-card__num">
                {{ project.statistics.attack_path_count }}
              </div>
              <div class="stat-card__label">攻击路径</div>
            </div>
            <div class="stat-card stat-card--info">
              <div class="stat-card__num">
                {{ project.statistics.worker_task_count }}
              </div>
              <div class="stat-card__label">角色任务</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 停止确认 -->
      <AppConfirmDialog
        v-model:visible="stopDialogVisible"
        title="停止评估"
        message="确认停止当前评估吗？已保存的结果将保留。"
        confirm-text="确认停止"
        confirm-type="warning"
        :loading="actionLoading === 'stop'"
        @confirm="handleStop"
        @cancel="stopDialogVisible = false"
      />

      <!-- 删除确认 -->
      <AppConfirmDialog
        v-model:visible="deleteDialogVisible"
        title="删除项目"
        message="此操作不可恢复。项目相关的所有数据（漏洞、攻击路径、报告、日志）将被永久删除。"
        confirm-text="删除项目"
        confirm-type="danger"
        :require-name-input="true"
        :expected-name="project.project_name"
        :loading="actionLoading === 'delete'"
        @confirm="handleDelete"
        @cancel="deleteDialogVisible = false"
      />
    </template>
  </div>
</template>

<style scoped>
.detail-alert {
  margin-bottom: var(--spacing-lg);
}

.detail-grid {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.task-content {
  font-size: var(--font-size-base);
  color: var(--color-text-regular);
  line-height: 1.8;
  white-space: pre-wrap;
}

.error-text {
  color: var(--color-danger);
  font-size: var(--font-size-sm);
}

.stat-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
}

.stat-card {
  text-align: center;
  padding: var(--spacing-lg);
  background: var(--color-bg-page);
  border-radius: var(--radius-md);
}

.stat-card__num {
  font-size: var(--font-size-3xl);
  font-weight: 700;
  color: var(--color-text-primary);
  line-height: 1.2;
}

.stat-card__label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-xs);
}

.stat-card--success .stat-card__num {
  color: var(--color-success);
}

.stat-card--warning .stat-card__num {
  color: var(--color-warning);
}

.stat-card--info .stat-card__num {
  color: var(--color-info);
}

@media (max-width: 768px) {
  .stat-cards {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
