<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  PROJECT_STATUS_MAP,
  SOURCE_TYPE_MAP,
  PROJECT_ALLOWED_ACTIONS,
  type StatusDisplay,
} from '@/contracts'
import { listProjects, type ProjectListParams } from '../api/project.api'
import { ApiError } from '@/services/http/errors'
import { formatDateTime } from '@/shared/utils/format'
import AppStatusTag from '@/shared/components/AppStatusTag.vue'
import AppPageHeader from '@/shared/components/AppPageHeader.vue'
import AppErrorBlock from '@/shared/components/AppErrorBlock.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import type { ProjectSummary } from '@/contracts'

function asProject(row: unknown): ProjectSummary {
  return row as ProjectSummary
}

const router = useRouter()

// ===== State =====
const projects = ref<ProjectSummary[]>([])
const loading = ref(false)
const error = ref<ApiError | null>(null)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const filters = reactive({
  keyword: '',
  project_status: '' as string,
  source_type: '' as string,
  sort: 'created_at:desc' as string,
})

// ===== Computed =====
const hasActiveFilters = computed(
  () =>
    filters.keyword.trim() !== '' ||
    filters.project_status !== '' ||
    filters.source_type !== '',
)

function canAct(project: ProjectSummary, action: string): boolean {
  const allowed = PROJECT_ALLOWED_ACTIONS[project.project_status] ?? []
  return allowed.includes(action)
}

// ===== Actions =====
async function fetchProjects() {
  loading.value = true
  error.value = null

  try {
    const params: ProjectListParams = {
      page: page.value,
      page_size: pageSize.value,
      sort: filters.sort,
    }
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    if (filters.project_status) params.project_status = filters.project_status
    if (filters.source_type) params.source_type = filters.source_type

    const result = await listProjects(params)
    projects.value = result.items
    total.value = result.total
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e
    }
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchProjects()
}

function handleReset() {
  filters.keyword = ''
  filters.project_status = ''
  filters.source_type = ''
  filters.sort = 'created_at:desc'
  page.value = 1
  fetchProjects()
}

function handlePageChange(p: number) {
  page.value = p
  fetchProjects()
}

function handleSizeChange(s: number) {
  pageSize.value = s
  page.value = 1
  fetchProjects()
}

function goToDetail(id: string) {
  router.push(`/projects/${id}`)
}

function goToMonitor(id: string) {
  router.push(`/projects/${id}/monitor`)
}

function goToCreate() {
  router.push('/projects/new')
}

onMounted(() => {
  fetchProjects()
})
</script>

<template>
  <div class="page-container">
    <AppPageHeader title="项目列表">
      <template #actions>
        <el-button type="primary" @click="goToCreate">
          <el-icon><Plus /></el-icon>
          创建项目
        </el-button>
      </template>
    </AppPageHeader>

    <!-- 筛选区 -->
    <div class="filter-bar">
      <el-input
        v-model="filters.keyword"
        placeholder="搜索项目名称"
        clearable
        style="width: 240px"
        @clear="handleSearch"
        @keyup.enter="handleSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>

      <el-select
        v-model="filters.project_status"
        placeholder="项目状态"
        clearable
        style="width: 140px"
        @change="handleSearch"
      >
        <el-option
          v-for="(display, key) in PROJECT_STATUS_MAP"
          :key="key"
          :label="display.text"
          :value="key"
        />
      </el-select>

      <el-select
        v-model="filters.source_type"
        placeholder="源码类型"
        clearable
        style="width: 140px"
        @change="handleSearch"
      >
        <el-option
          v-for="(display, key) in SOURCE_TYPE_MAP"
          :key="key"
          :label="display.text"
          :value="key"
        />
      </el-select>

      <el-select
        v-model="filters.sort"
        style="width: 160px"
        @change="handleSearch"
      >
        <el-option label="最近创建" value="created_at:desc" />
        <el-option label="最早创建" value="created_at:asc" />
        <el-option label="最近更新" value="updated_at:desc" />
        <el-option label="最早更新" value="updated_at:asc" />
      </el-select>

      <el-button @click="handleSearch">
        <el-icon><Search /></el-icon>
        搜索
      </el-button>
      <el-button v-if="hasActiveFilters" @click="handleReset">
        重置
      </el-button>
    </div>

    <!-- 错误 -->
    <AppErrorBlock
      v-if="error"
      :message="error.message"
      :request-id="error.requestId"
      retryable
      class="list-error"
      @retry="fetchProjects"
    />

    <!-- 空态 -->
    <AppEmptyState
      v-else-if="!loading && projects.length === 0"
      :title="hasActiveFilters ? '没有匹配的项目' : '暂无项目'"
      :description="
        hasActiveFilters
          ? '尝试调整筛选条件'
          : '创建您的第一个安全评估项目'
      "
      :action-text="hasActiveFilters ? '' : '创建项目'"
      @action="goToCreate"
    />

    <!-- 表格 -->
    <template v-else>
      <el-table
        v-loading="loading"
        :data="projects"
        stripe
        row-key="id"
        class="project-table"
        @row-click="(row: ProjectSummary) => goToDetail(row.id)"
      >
        <el-table-column label="项目名称" prop="project_name" min-width="200">
          <template #default="{ row }">
            <span class="project-name">
              {{ row.project_name }}
            </span>
          </template>
        </el-table-column>

        <el-table-column label="源码类型" width="110">
          <template #default="{ row }">
            <AppStatusTag
              :value="row.source_type"
              :map="SOURCE_TYPE_MAP as Record<string, StatusDisplay>"
              size="small"
            />
          </template>
        </el-table-column>

        <el-table-column label="项目状态" width="110">
          <template #default="{ row }">
            <AppStatusTag
              :value="row.project_status"
              :map="PROJECT_STATUS_MAP as Record<string, StatusDisplay>"
              size="small"
            />
          </template>
        </el-table-column>

        <el-table-column label="环境" width="120">
          <template #default="{ row }">
            <el-tag size="small" type="info" effect="plain">
              {{ row.environment_type }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="最近运行" width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.last_started_at) }}
          </template>
        </el-table-column>

        <el-table-column label="创建时间" width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <div class="table-actions" @click.stop>
              <el-button
                text
                size="small"
                type="primary"
                @click="goToDetail(row.id)"
              >
                查看
              </el-button>
              <el-button
                v-if="canAct(asProject(row), 'monitor')"
                text
                size="small"
                type="success"
                @click="goToMonitor(row.id)"
              >
                监控
              </el-button>
              <el-button
                v-if="canAct(asProject(row), 'delete')"
                text
                size="small"
                type="danger"
                @click="goToDetail(row.id)"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="list-pagination">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          background
          layout="total, sizes, prev, pager, next"
          @current-change="handlePageChange"
          @size-change="handleSizeChange"
        />
      </div>
    </template>
  </div>
</template>

<style scoped>
.filter-bar {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
  flex-wrap: wrap;
}

.list-error {
  margin-bottom: var(--spacing-lg);
}

.project-table {
  cursor: pointer;
}

.project-name {
  color: var(--color-primary);
  font-weight: 500;
}

.list-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--spacing-lg);
}
</style>
