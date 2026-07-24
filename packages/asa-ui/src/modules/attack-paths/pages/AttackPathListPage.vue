<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listAttackPaths, type PathListParams } from '../api/attack-path.api'
import { ApiError } from '@/services/http/errors'
import { formatDateTime } from '@/shared/utils/format'
import AppPageHeader from '@/shared/components/AppPageHeader.vue'
import AppErrorBlock from '@/shared/components/AppErrorBlock.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'
import type { AttackPathSummary } from '@asa/contracts'

const route = useRoute()
const router = useRouter()
const projectId = route.params.projectId as string

const paths = ref<AttackPathSummary[]>([])
const loading = ref(false)
const error = ref<ApiError | null>(null)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const keyword = ref('')

async function fetchPaths() {
  loading.value = true
  error.value = null
  try {
    const params: PathListParams = {
      page: page.value,
      page_size: pageSize.value,
    }
    if (keyword.value.trim()) params.keyword = keyword.value.trim()
    const result = await listAttackPaths(projectId, params)
    paths.value = result.items
    total.value = result.total
  } catch (e) {
    if (e instanceof ApiError) error.value = e
  } finally {
    loading.value = false
  }
}

function handleSearch() {
  page.value = 1
  fetchPaths()
}

function goToDetail(pathId: string) {
  router.push(`/projects/${projectId}/attack-paths/${pathId}`)
}

onMounted(() => fetchPaths())
</script>

<template>
  <div class="page-container">
    <AppPageHeader title="攻击路径列表">
      <template #actions>
        <el-button @click="router.push(`/projects/${projectId}`)">
          返回详情
        </el-button>
      </template>
    </AppPageHeader>

    <div class="filter-bar">
      <el-input
        v-model="keyword"
        placeholder="搜索路径编号或标题"
        clearable
        style="width: 280px"
        @clear="handleSearch"
        @keyup.enter="handleSearch"
      />
      <el-button @click="handleSearch">搜索</el-button>
      <el-button v-if="keyword" @click="keyword = ''; handleSearch()">重置</el-button>
    </div>

    <AppErrorBlock
      v-if="error"
      :message="error.message"
      :request-id="error.requestId"
      retryable
      @retry="fetchPaths"
    />

    <AppEmptyState
      v-else-if="!loading && paths.length === 0"
      title="暂无攻击路径"
      description="项目尚未发现攻击路径"
    />

    <template v-else>
      <el-table
        v-loading="loading"
        :data="paths"
        stripe
        row-key="id"
        @row-click="(row: AttackPathSummary) => goToDetail(row.id)"
      >
        <el-table-column label="路径编号" prop="path_code" width="150" />
        <el-table-column label="路径标题" prop="path_title" min-width="200">
          <template #default="{ row }">
            <span class="path-title">{{ row.path_title }}</span>
          </template>
        </el-table-column>
        <el-table-column label="摘要" prop="path_summary" min-width="300" show-overflow-tooltip />
        <el-table-column label="步骤数" width="80">
          <template #default="{ row }">
            <el-tag size="small" type="warning" effect="plain">
              {{ row.step_count }} 步
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="关联漏洞" width="200">
          <template #default="{ row }">
            <div class="vuln-codes">
              <el-tag
                v-for="code in row.vulnerability_codes"
                :key="code"
                size="small"
                type="danger"
                effect="plain"
                style="margin: 2px"
              >
                {{ code }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="发现时间" width="170">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
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
          @current-change="(p: number) => { page = p; fetchPaths() }"
          @size-change="(s: number) => { pageSize = s; page = 1; fetchPaths() }"
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
}

.path-title {
  color: var(--color-primary);
  font-weight: 500;
  cursor: pointer;
}

.vuln-codes {
  display: flex;
  flex-wrap: wrap;
}

.list-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--spacing-lg);
}
</style>
