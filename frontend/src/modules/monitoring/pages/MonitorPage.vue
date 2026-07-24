<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  STAGE_NAME_MAP,
  STAGE_STATUS_MAP,
  TASK_STATUS_MAP,
  WORKER_ROLE_MAP,
  LOG_LEVEL_MAP,
  type StatusDisplay,
  type StageItem,
  type WorkerTask,
  type ChatMessage,
  type RuntimeLog,
  type ResourceSample,
} from '@/contracts'
import {
  getStages,
  getWorkers,
  getMessages,
  getLogs,
  getResources,
} from '../api/monitoring.api'
import { getProjectDetail } from '@/modules/projects/api/project.api'
import { WsConnection, type EventHandler } from '@/services/realtime/connection'
import { ApiError } from '@/services/http/errors'
import {
  formatTime,
  formatBytes,
  formatCpuPercent,
  formatTokenCount,
} from '@/shared/utils/format'
import AppStatusTag from '@/shared/components/AppStatusTag.vue'
import AppPageHeader from '@/shared/components/AppPageHeader.vue'
import AppLoadingSkeleton from '@/shared/components/AppLoadingSkeleton.vue'
import type { ProjectDetail, WsEvent, WsConnectionStatus } from '@/contracts'

const route = useRoute()
const router = useRouter()
const projectId = route.params.projectId as string

// ===== State =====
const project = ref<ProjectDetail | null>(null)
const stages = ref<StageItem[]>([])
const workers = ref<WorkerTask[]>([])
const messages = ref<ChatMessage[]>([])
const logs = ref<RuntimeLog[]>([])
const resources = ref<ResourceSample[]>([])
const resourceUnits = ref({ cpu_usage: 'percent', memory_usage: 'bytes', token_count: 'count' })

const loading = ref(true)
const snapshotError = ref<ApiError | null>(null)
const wsStatus = ref<WsConnectionStatus>('disconnected')
const compensating = ref(false)

const logLevelFilter = ref<string[]>([])
const logAutoScroll = ref(true)
const logContainer = ref<HTMLElement | null>(null)
const MAX_LOG_ROWS = 500

// ===== WebSocket =====
let ws: WsConnection | null = null

const connectionStatusText = computed(() => {
  const map: Record<WsConnectionStatus, string> = {
    disconnected: '已断开',
    connecting: '连接中',
    connected: '实时',
    reconnecting: '重连中',
    compensating: '数据补偿中',
  }
  return map[wsStatus.value] ?? '未知'
})

const connectionStatusType = computed(() => {
  if (wsStatus.value === 'connected') return 'success'
  if (wsStatus.value === 'reconnecting' || wsStatus.value === 'connecting' || wsStatus.value === 'compensating') return 'warning'
  return 'danger'
})

// ===== Snapshot =====
async function loadSnapshot() {
  loading.value = true
  snapshotError.value = null
  try {
    const [detailData, stagesData, workersData, messagesData, logsData, resourcesData] =
      await Promise.all([
        getProjectDetail(projectId),
        getStages(projectId),
        getWorkers(projectId, { page_size: 50 }),
        getMessages(projectId, { limit: 100 }),
        getLogs(projectId, { limit: 100, order: 'asc' }),
        getResources(projectId, { limit: 300 }),
      ])

    project.value = detailData
    stages.value = stagesData.items
    workers.value = workersData.items
    messages.value = messagesData.items
    logs.value = logsData.items
    resources.value = resourcesData.items
    if ('units' in resourcesData) {
      resourceUnits.value = resourcesData.units
    }

    loading.value = false
  } catch (e) {
    if (e instanceof ApiError) snapshotError.value = e
    loading.value = false
  }
}

// ===== Event processor =====
const seenEventIds = new Set<string>()
let lastSequence = 0

function getSavedSequence(): number {
  const saved = sessionStorage.getItem(`asa_seq_${projectId}`)
  return saved ? parseInt(saved, 10) : 0
}

function saveSequence(seq: number) {
  sessionStorage.setItem(`asa_seq_${projectId}`, String(seq))
}

const handleEvent: EventHandler = (event: WsEvent) => {
  // 去重
  if (seenEventIds.has(event.event_id)) return
  seenEventIds.add(event.event_id)
  // 限制集合大小
  if (seenEventIds.size > 10000) {
    const toRemove = Array.from(seenEventIds).slice(0, 5000)
    for (const id of toRemove) seenEventIds.delete(id)
  }

  // 序号检查
  if (event.sequence <= lastSequence) return
  lastSequence = event.sequence
  saveSequence(event.sequence)

  // 路由事件
  switch (event.event_type) {
    case 'project_status': {
      if (project.value && event.data) {
        const d = event.data as { project_status: string; stop_requested_at: string | null }
        project.value = {
          ...project.value,
          project_status: d.project_status as ProjectDetail['project_status'],
          stop_requested_at: d.stop_requested_at,
        }
      }
      break
    }
    case 'stage_status': {
      if (event.data) {
        const d = event.data as { stage_id: string; stage_name: string; stage_status: string }
        const idx = stages.value.findIndex((s: StageItem) => s.id === d.stage_id)
        if (idx >= 0) {
          stages.value[idx] = { ...stages.value[idx]!, stage_status: d.stage_status as StageItem['stage_status'] }
        }
      }
      break
    }
    case 'worker_status': {
      if (event.data) {
        const d = event.data as { worker_task_id: string; worker_role: string; task_status: string }
        const idx = workers.value.findIndex((w: WorkerTask) => w.id === d.worker_task_id)
        if (idx >= 0) {
          workers.value[idx] = { ...workers.value[idx]!, task_status: d.task_status as WorkerTask['task_status'] }
        }
      }
      break
    }
    case 'chat_message': {
      if (event.data) {
        const d = event.data as { message_id: number; worker_role: string; message_type: string; message_text: string }
        messages.value.push({
          id: d.message_id,
          stage_id: '',
          worker_task_id: '',
          worker_role: d.worker_role as ChatMessage['worker_role'],
          message_type: d.message_type,
          message_text: d.message_text,
          created_at: event.occurred_at,
        })
      }
      break
    }
    case 'runtime_log': {
      if (event.data) {
        const d = event.data as { log_id: number; log_level: string; log_content: string }
        logs.value.push({
          id: d.log_id,
          stage_id: '',
          worker_task_id: null,
          request_id: null,
          log_level: d.log_level as RuntimeLog['log_level'],
          log_content: d.log_content,
          created_at: event.occurred_at,
        })
        // 限制 DOM 行数
        if (logs.value.length > MAX_LOG_ROWS) {
          logs.value.splice(0, logs.value.length - MAX_LOG_ROWS)
        }
      }
      break
    }
    case 'resource_usage': {
      if (event.data) {
        const d = event.data as { resource_usage_id: number; cpu_usage: number; memory_usage: number; token_count: number }
        resources.value.push({
          id: d.resource_usage_id,
          runtime_id: '',
          cpu_usage: d.cpu_usage,
          memory_usage: d.memory_usage,
          token_count: d.token_count,
          recorded_at: event.occurred_at,
        })
      }
      break
    }
    case 'vulnerability_found': {
      // 更新计数
      if (project.value && event.data) {
        project.value = {
          ...project.value,
          statistics: {
            ...project.value.statistics,
            vulnerability_count: project.value.statistics.vulnerability_count + 1,
          },
        }
      }
      break
    }
    case 'report_ready': {
      if (project.value && event.data) {
        const d = event.data as { report_id: string; version: number; report_status: string }
        project.value = {
          ...project.value,
          report_status: d.report_status as ProjectDetail['report_status'],
        }
      }
      break
    }
  }
}

function handleWsStatus(status: WsConnectionStatus) {
  wsStatus.value = status
  if (status === 'compensating') {
    compensating.value = true
    loadSnapshot().then(() => {
      compensating.value = false
      // 全量补偿后重连
      ws?.disconnect()
      connectWs()
    })
  }
}

function connectWs() {
  const seq = getSavedSequence()
  ws = new WsConnection({ projectId, afterSequence: seq })
  ws.onEvent(handleEvent)
  ws.onStatusChange(handleWsStatus)
  ws.connect()
}

function handleManualReconnect() {
  if (ws) {
    ws.disconnect()
  }
  connectWs()
}

// ===== Log scroll =====
function onLogScroll() {
  if (!logContainer.value) return
  const el = logContainer.value
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
  logAutoScroll.value = atBottom
}

function scrollToBottom() {
  if (logContainer.value) {
    logContainer.value.scrollTop = logContainer.value.scrollHeight
  }
}

// ===== Filtered logs =====
const filteredLogs = computed(() => {
  if (logLevelFilter.value.length === 0) return logs.value
  return logs.value.filter((l: RuntimeLog) => logLevelFilter.value.includes(l.log_level))
})

// ===== Lifecycle =====
onMounted(async () => {
  await loadSnapshot()
  connectWs()
})

onUnmounted(() => {
  if (ws) {
    ws.disconnect()
    ws = null
  }
  seenEventIds.clear()
})
</script>

<template>
  <div class="page-container">
    <AppPageHeader :title="project?.project_name ?? '实时监控'">
      <template #actions>
        <div class="monitor-actions">
          <el-tag :type="connectionStatusType" size="small" effect="dark">
            {{ connectionStatusText }}
          </el-tag>
          <el-button
            v-if="wsStatus === 'disconnected'"
            size="small"
            @click="handleManualReconnect"
          >
            重新连接
          </el-button>
          <el-button @click="router.push(`/projects/${projectId}`)">
            返回详情
          </el-button>
        </div>
      </template>
    </AppPageHeader>

    <el-alert
      v-if="compensating"
      title="数据补偿中，正在重新加载完整数据..."
      type="info"
      show-icon
      :closable="false"
      class="monitor-banner"
    />

    <el-alert
      v-if="snapshotError"
      :title="snapshotError.message"
      type="error"
      show-icon
      :closable="true"
      class="monitor-banner"
    />

    <AppLoadingSkeleton v-if="loading" variant="detail" />

    <template v-else>
      <div class="monitor-layout monitor-layout--full">
        <!-- 阶段进度 -->
        <div class="monitor-panel monitor-panel--wide">
          <div class="monitor-panel__header">
            <span>评估阶段</span>
          </div>
          <div class="monitor-panel__body">
            <div class="stage-pipeline">
              <div
                v-for="stage in stages"
                :key="stage.id"
                class="stage-item"
                :class="`stage-item--${stage.stage_status}`"
              >
                <div class="stage-item__order">{{ stage.stage_order }}</div>
                <div class="stage-item__name">
                  {{ STAGE_NAME_MAP[stage.stage_name]?.text ?? stage.stage_name }}
                </div>
                <AppStatusTag
                  :value="stage.stage_status"
                  :map="STAGE_STATUS_MAP as Record<string, StatusDisplay>"
                  size="small"
                />
                <div v-if="stage.started_at" class="stage-item__time">
                  {{ formatTime(stage.started_at) }}
                </div>
                <div
                  v-if="stage.error_message"
                  class="stage-item__error"
                  :title="stage.error_message"
                >
                  {{ stage.error_message }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 角色任务 -->
        <div class="monitor-panel">
          <div class="monitor-panel__header">
            <span>角色任务</span>
            <el-tag size="small" type="info" effect="plain">
              {{ workers.length }} 个任务
            </el-tag>
          </div>
          <div class="monitor-panel__body panel-scroll">
            <div
              v-for="worker in workers"
              :key="worker.id"
              class="worker-item"
            >
              <div class="worker-item__header">
                <AppStatusTag
                  :value="worker.worker_role"
                  :map="WORKER_ROLE_MAP as Record<string, StatusDisplay>"
                  size="small"
                />
                <AppStatusTag
                  :value="worker.task_status"
                  :map="TASK_STATUS_MAP as Record<string, StatusDisplay>"
                  size="small"
                />
              </div>
              <div class="worker-item__content">
                {{ worker.task_content || '等待任务分配...' }}
              </div>
              <div
                v-if="worker.result_summary"
                class="worker-item__result"
              >
                {{ worker.result_summary }}
              </div>
              <div
                v-if="worker.error_message"
                class="worker-item__error"
              >
                {{ worker.error_message }}
              </div>
            </div>
            <div v-if="workers.length === 0" class="panel-empty">
              暂无角色任务
            </div>
          </div>
        </div>
      </div>

      <div class="monitor-layout monitor-layout--full">
        <!-- 角色消息 -->
        <div class="monitor-panel">
          <div class="monitor-panel__header">
            <span>角色消息</span>
          </div>
          <div class="monitor-panel__body message-panel">
            <div
              v-for="msg in messages.slice(-30)"
              :key="msg.id"
              class="message-item"
            >
              <div class="message-item__header">
                <AppStatusTag
                  :value="msg.worker_role"
                  :map="WORKER_ROLE_MAP as Record<string, StatusDisplay>"
                  size="small"
                />
                <span class="message-item__type">{{ msg.message_type }}</span>
                <span class="message-item__time">
                  {{ formatTime(msg.created_at) }}
                </span>
              </div>
              <div class="message-item__text">{{ msg.message_text }}</div>
            </div>
            <div v-if="messages.length === 0" class="panel-empty">
              暂无角色消息
            </div>
          </div>
        </div>

        <!-- 运行日志 -->
        <div class="monitor-panel">
          <div class="monitor-panel__header">
            <span>运行日志</span>
            <div class="log-controls">
              <el-select
                v-model="logLevelFilter"
                multiple
                placeholder="日志级别"
                size="small"
                style="width: 180px"
                collapse-tags
              >
                <el-option
                  v-for="(display, key) in LOG_LEVEL_MAP"
                  :key="key"
                  :label="display.text"
                  :value="key"
                />
              </el-select>
              <el-button
                v-if="!logAutoScroll"
                size="small"
                @click="scrollToBottom"
              >
                回到最新
              </el-button>
            </div>
          </div>
          <div
            ref="logContainer"
            class="monitor-panel__body log-panel"
            @scroll="onLogScroll"
          >
            <div
              v-for="log in filteredLogs"
              :key="log.id"
              class="log-item"
              :class="`log-item--${log.log_level}`"
            >
              <span class="log-item__time">{{ formatTime(log.created_at) }}</span>
              <AppStatusTag
                :value="log.log_level"
                :map="LOG_LEVEL_MAP as Record<string, StatusDisplay>"
                size="small"
              />
              <span class="log-item__content">{{ log.log_content }}</span>
            </div>
            <div v-if="filteredLogs.length === 0" class="panel-empty">
              暂无日志
            </div>
          </div>
        </div>
      </div>

      <!-- 资源消耗图表 -->
      <div class="monitor-panel" style="margin-top: var(--spacing-md)">
        <div class="monitor-panel__header">
          <span>资源消耗</span>
        </div>
        <div class="monitor-panel__body">
          <div class="resource-summary">
            <div class="resource-card">
              <div class="resource-card__label">CPU 使用率</div>
              <div class="resource-card__value">
                {{
                  resources.length > 0
                    ? formatCpuPercent(resources[resources.length - 1]!.cpu_usage)
                    : '-'
                }}
              </div>
              <div class="resource-card__time">
                {{
                  resources.length > 0
                    ? formatTime(resources[resources.length - 1]!.recorded_at)
                    : '-'
                }}
              </div>
            </div>
            <div class="resource-card">
              <div class="resource-card__label">内存使用</div>
              <div class="resource-card__value">
                {{
                  resources.length > 0
                    ? formatBytes(resources[resources.length - 1]!.memory_usage)
                    : '-'
                }}
              </div>
              <div class="resource-card__time">
                {{
                  resources.length > 0
                    ? formatTime(resources[resources.length - 1]!.recorded_at)
                    : '-'
                }}
              </div>
            </div>
            <div class="resource-card">
              <div class="resource-card__label">Token 消耗</div>
              <div class="resource-card__value">
                {{
                  resources.length > 0
                    ? formatTokenCount(resources[resources.length - 1]!.token_count)
                    : '-'
                }}
              </div>
              <div class="resource-card__time">
                {{
                  resources.length > 0
                    ? formatTime(resources[resources.length - 1]!.recorded_at)
                    : '-'
                }}
              </div>
            </div>
          </div>
          <div v-if="resources.length === 0" class="panel-empty">
            暂无资源数据
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.monitor-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.monitor-banner {
  margin-bottom: var(--spacing-md);
}

.monitor-layout {
  display: grid;
  gap: var(--spacing-md);
}

.monitor-layout--full {
  grid-template-columns: 1fr 1fr;
  margin-bottom: var(--spacing-md);
}

.monitor-panel--wide {
  grid-column: 1 / -1;
}

.panel-scroll {
  max-height: 360px;
  overflow-y: auto;
}

.panel-empty {
  text-align: center;
  color: var(--color-text-placeholder);
  padding: var(--spacing-xl);
  font-size: var(--font-size-sm);
}

/* ===== 阶段管道 ===== */
.stage-pipeline {
  display: flex;
  gap: var(--spacing-md);
  overflow-x: auto;
  padding: var(--spacing-sm) 0;
}

.stage-item {
  flex: 1;
  min-width: 140px;
  text-align: center;
  padding: var(--spacing-md);
  border-radius: var(--radius-md);
  background: var(--color-bg-page);
  border: 2px solid var(--color-border-light);
  transition: border-color var(--transition-normal);
}

.stage-item--running {
  border-color: var(--color-primary);
  background: rgba(22, 119, 255, 0.1);
}

.stage-item--success {
  border-color: var(--color-success);
}

.stage-item--failed {
  border-color: var(--color-danger);
  background: rgba(255, 77, 79, 0.1);
}

.stage-item__order {
  font-size: var(--font-size-xs);
  color: var(--color-text-placeholder);
  margin-bottom: 4px;
}

.stage-item__name {
  font-size: var(--font-size-sm);
  font-weight: 600;
  margin-bottom: var(--spacing-sm);
}

.stage-item__time {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-xs);
}

.stage-item__error {
  font-size: var(--font-size-xs);
  color: var(--color-danger);
  margin-top: var(--spacing-xs);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== 角色任务 ===== */
.worker-item {
  padding: var(--spacing-sm) 0;
  border-bottom: 1px solid var(--color-border-lighter);
}

.worker-item:last-child {
  border-bottom: none;
}

.worker-item__header {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: 4px;
}

.worker-item__content {
  font-size: var(--font-size-sm);
  color: var(--color-text-regular);
  line-height: 1.5;
}

.worker-item__result {
  font-size: var(--font-size-xs);
  color: var(--color-success);
  margin-top: 4px;
}

.worker-item__error {
  font-size: var(--font-size-xs);
  color: var(--color-danger);
  margin-top: 4px;
}

/* ===== 消息 ===== */
.message-panel {
  max-height: 320px;
  overflow-y: auto;
}

.message-item {
  padding: var(--spacing-sm) 0;
  border-bottom: 1px solid var(--color-border-lighter);
}

.message-item:last-child {
  border-bottom: none;
}

.message-item__header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  margin-bottom: 4px;
}

.message-item__type {
  font-size: var(--font-size-xs);
  color: var(--color-text-placeholder);
}

.message-item__time {
  font-size: var(--font-size-xs);
  color: var(--color-text-placeholder);
  margin-left: auto;
}

.message-item__text {
  font-size: var(--font-size-sm);
  color: var(--color-text-regular);
  line-height: 1.5;
  word-break: break-all;
}

/* ===== 日志 ===== */
.log-controls {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.log-panel {
  max-height: 320px;
  overflow-y: auto;
  font-family: var(--font-mono);
}

.log-item {
  display: flex;
  gap: var(--spacing-sm);
  padding: 2px 0;
  font-size: var(--font-size-xs);
  line-height: 1.6;
}

.log-item--error {
  background: rgba(255, 77, 79, 0.1);
}

.log-item--warning {
  background: rgba(255, 140, 0, 0.1);
}

.log-item__time {
  color: var(--color-text-placeholder);
  flex-shrink: 0;
}

.log-item__content {
  color: var(--color-text-regular);
  word-break: break-all;
}

/* ===== 资源 ===== */
.resource-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-md);
}

.resource-card {
  text-align: center;
  padding: var(--spacing-lg);
  background: var(--color-bg-page);
  border-radius: var(--radius-md);
}

.resource-card__label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-sm);
}

.resource-card__value {
  font-size: var(--font-size-xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.resource-card__time {
  font-size: var(--font-size-xs);
  color: var(--color-text-placeholder);
  margin-top: var(--spacing-sm);
}

@media (max-width: 1024px) {
  .monitor-layout--full {
    grid-template-columns: 1fr;
  }

  .resource-summary {
    grid-template-columns: 1fr;
  }
}
</style>
