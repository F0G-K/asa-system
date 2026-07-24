<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  KNOWLEDGE_TYPE_MAP,
  ENTRY_STATUS_MAP,
  RISK_LEVEL_MAP,
  KNOWLEDGE_SOURCE_TYPE_MAP,
  type StatusDisplay,
  type KnowledgeType,
  type EntryStatus,
  type KnowledgeSourceType,
  type RiskLevel,
} from '@asa/contracts'
import type {
  KnowledgeEntrySummary,
  KnowledgeEntryDetail,
  KnowledgeSearchData,
} from '@asa/contracts'
import {
  listKnowledgeEntries,
  createKnowledgeEntry,
  updateKnowledgeEntry,
  deleteKnowledgeEntry,
  semanticSearch,
  getKnowledgeEntryDetail,
} from '../api/knowledge.api'
import type {
  KnowledgeEntryListParams,
} from '../api/knowledge.api'
import { ApiError } from '@/services/http/errors'
import { formatDateTime } from '@/shared/utils/format'
import AppPageHeader from '@/shared/components/AppPageHeader.vue'
import AppStatusTag from '@/shared/components/AppStatusTag.vue'
import AppErrorBlock from '@/shared/components/AppErrorBlock.vue'
import AppEmptyState from '@/shared/components/AppEmptyState.vue'

// ===== Types =====
interface SearchResultItem {
  entry_id: string
  title: string
  knowledge_type: KnowledgeType
  content_text: string
  risk_level: string | null
  tags: string[]
  similarity: number
}

// ===== State =====
const entries = ref<KnowledgeEntrySummary[]>([])
const loading = ref(false)
const error = ref<ApiError | null>(null)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const activeTab = ref<'entries' | 'search'>('entries')

// Filters
const filters = reactive({
  knowledge_type: '' as string,
  risk_level: '' as string,
  language: '' as string,
  entry_status: '' as string,
  keyword: '' as string,
  tags_filter: '' as string,
  sort: 'updated_at:desc' as string,
})

// Semantic search
const searchQuery = ref('')
const searchResults = ref<SearchResultItem[]>([])
const searchLoading = ref(false)
const searchPerformed = ref(false)
const searchMeta = ref<Pick<KnowledgeSearchData, 'total_scanned' | 'total_matched' | 'searched_knowledge_types'> | null>(null)

// Modal
const modalVisible = ref(false)
const modalTitle = ref('新建知识条目')
const isEditing = ref(false)
const editingId = ref<string | null>(null)
const editVersion = ref(0)
const saving = ref(false)
const detailLoading = ref(false)

const form = reactive({
  title: '',
  content_text: '',
  knowledge_type: 'vulnerability_pattern' as KnowledgeType,
  risk_level: '' as string,
  language: '',
  framework: '',
  tags: '',
  source_type: 'manual' as KnowledgeSourceType,
  source_url: '',
})

// Confirm dialog
const confirmVisible = ref(false)
const confirmMessage = ref('')
const confirmAction = ref<(() => void) | null>(null)

// Stat cards
const statCards = computed(() => {
  const counts: Record<string, number> = {
    vulnerability_pattern: 0,
    security_standard: 0,
    remediation_advice: 0,
    historical_assessment: 0,
  }
  entries.value.forEach((e) => {
    if (e.knowledge_type in counts) {
      counts[e.knowledge_type] = (counts[e.knowledge_type] ?? 0) + 1
    }
  })
  return [
    { type: 'vulnerability_pattern', count: counts.vulnerability_pattern, desc: 'CVE/NVD · OWASP Top 10 · CWE' },
    { type: 'security_standard', count: counts.security_standard, desc: 'OWASP Cheat Sheets · 语言安全指南' },
    { type: 'remediation_advice', count: counts.remediation_advice, desc: '代码修复片段 · 依赖升级 · 配置加固' },
    { type: 'historical_assessment', count: counts.historical_assessment, desc: '已完成评估的已验证漏洞特征 · 有效修复' },
  ]
})

const hasActiveFilters = computed(
  () =>
    filters.knowledge_type !== '' ||
    filters.risk_level !== '' ||
    filters.language !== '' ||
    filters.entry_status !== '' ||
    filters.keyword.trim() !== '' ||
    filters.tags_filter.trim() !== '',
)

// ===== API Calls =====
async function fetchEntries() {
  loading.value = true
  error.value = null

  try {
    const params: KnowledgeEntryListParams = {
      page: page.value,
      page_size: pageSize.value,
      sort: filters.sort,
    }
    if (filters.knowledge_type) params.knowledge_type = filters.knowledge_type
    if (filters.risk_level) params.risk_level = filters.risk_level
    if (filters.language) params.language = filters.language
    if (filters.entry_status) params.entry_status = filters.entry_status
    if (filters.keyword.trim()) params.keyword = filters.keyword.trim()
    if (filters.tags_filter.trim()) {
      params.tags = filters.tags_filter
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
    }

    const result = await listKnowledgeEntries(params)
    entries.value = result.items
    total.value = result.total
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e
    }
  } finally {
    loading.value = false
  }
}

async function doSearch() {
  const q = searchQuery.value.trim()
  if (!q) return

  searchLoading.value = true
  searchPerformed.value = true
  searchMeta.value = null

  try {
    const result = await semanticSearch({
      query_text: q,
      top_k: 8,
      min_similarity: 0.7,
      knowledge_types: filters.knowledge_type
        ? [filters.knowledge_type as KnowledgeType]
        : undefined,
      language: filters.language || undefined,
      risk_level: filters.risk_level
        ? (filters.risk_level as RiskLevel)
        : undefined,
    })
    searchResults.value = result.items
    searchMeta.value = {
      total_scanned: result.total_scanned,
      total_matched: result.total_matched,
      searched_knowledge_types: result.searched_knowledge_types,
    }
  } catch (e) {
    if (e instanceof ApiError) {
      error.value = e
    }
    searchResults.value = []
  } finally {
    searchLoading.value = false
  }
}

function clearSearch() {
  searchQuery.value = ''
  searchResults.value = []
  searchPerformed.value = false
  searchMeta.value = null
}

// ===== CRUD =====
function openCreateModal() {
  isEditing.value = false
  editingId.value = null
  editVersion.value = 0
  detailLoading.value = false
  modalTitle.value = '新建知识条目'
  form.title = ''
  form.content_text = ''
  form.knowledge_type = 'vulnerability_pattern'
  form.risk_level = ''
  form.language = ''
  form.framework = ''
  form.tags = ''
  form.source_type = 'manual'
  form.source_url = ''
  modalVisible.value = true
}

function openEditModal(entry: KnowledgeEntrySummary) {
  isEditing.value = true
  editingId.value = entry.id
  editVersion.value = entry.version
  detailLoading.value = true
  modalTitle.value = '编辑知识条目'
  // Pre-fill from summary; content_text/source_url loaded async
  form.title = entry.title
  form.content_text = ''
  form.knowledge_type = entry.knowledge_type
  form.risk_level = entry.risk_level ?? ''
  form.language = entry.language ?? ''
  form.framework = entry.framework ?? ''
  form.tags = (entry.tags ?? []).join(', ')
  form.source_type = (entry.source_type as KnowledgeSourceType) ?? 'manual'
  form.source_url = ''
  modalVisible.value = true
  // Fetch full detail for content_text and source_url
  fetchEntryDetail(entry.id)
}

async function fetchEntryDetail(id: string) {
  detailLoading.value = true
  try {
    const detail = await getKnowledgeEntryDetail(id)
    form.content_text = detail.content_text
    form.source_url = detail.source_url ?? ''
    editVersion.value = detail.version
  } catch {
    // Keep existing content; version stays as summary version
  } finally {
    detailLoading.value = false
  }
}

async function handleSave() {
  if (!form.title.trim() || !form.content_text.trim()) {
    ElMessage.warning('标题和正文为必填项')
    return
  }

  saving.value = true
  try {
    const tags = form.tags
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)

    if (isEditing.value && editingId.value) {
      await updateKnowledgeEntry(editingId.value, {
        title: form.title.trim(),
        content_text: form.content_text.trim(),
        knowledge_type: form.knowledge_type,
        language: form.language.trim() || null,
        framework: form.framework.trim() || null,
        risk_level: (form.risk_level || null) as KnowledgeEntryDetail['risk_level'],
        tags,
        source_url: form.source_url.trim() || null,
        expected_version: editVersion.value,
      })
      ElMessage.success('条目已更新')
    } else {
      await createKnowledgeEntry({
        title: form.title.trim(),
        content_text: form.content_text.trim(),
        knowledge_type: form.knowledge_type,
        language: form.language.trim() || null,
        framework: form.framework.trim() || null,
        risk_level: (form.risk_level || null) as KnowledgeEntryDetail['risk_level'],
        tags,
        source_type: form.source_type,
        source_url: form.source_url.trim() || null,
      })
      ElMessage.success('条目已创建（草稿状态，待审核）')
    }
    modalVisible.value = false
    fetchEntries()
  } catch (e) {
    if (e instanceof ApiError) {
      if (e.code === 'ENTRY_VERSION_CONFLICT') {
        ElMessage.warning('条目已被其他管理员更新，请关闭后重新打开编辑')
      } else {
        ElMessage.error(e.message)
      }
    }
  } finally {
    saving.value = false
  }
}

function confirmDelete(entry: KnowledgeEntrySummary) {
  confirmMessage.value = `确定要删除「${entry.title}」？删除不可恢复。`
  confirmAction.value = async () => {
    try {
      await deleteKnowledgeEntry(entry.id)
      ElMessage.success('条目已删除')
      fetchEntries()
    } catch (e) {
      if (e instanceof ApiError) {
        ElMessage.error(e.message)
      }
    }
  }
  confirmVisible.value = true
}

function confirmActivate(entry: KnowledgeEntrySummary) {
  confirmMessage.value = `审核激活「${entry.title}」后将异步生成 Embedding 向量，条目开始参与检索。`
  confirmAction.value = async () => {
    try {
      await updateKnowledgeEntry(entry.id, {
        entry_status: 'active' as EntryStatus,
        expected_version: entry.version,
      })
      ElMessage.success('条目已激活，向量生成中...')
      fetchEntries()
    } catch (e) {
      if (e instanceof ApiError) {
        ElMessage.error(e.message)
      }
    }
  }
  confirmVisible.value = true
}

function confirmDisable(entry: KnowledgeEntrySummary) {
  confirmMessage.value = `禁用「${entry.title}」后该条目不参与语义检索，但保留向量数据。`
  confirmAction.value = async () => {
    try {
      await updateKnowledgeEntry(entry.id, {
        entry_status: 'disabled' as EntryStatus,
        expected_version: entry.version,
      })
      ElMessage.success('条目已禁用')
      fetchEntries()
    } catch (e) {
      if (e instanceof ApiError) {
        ElMessage.error(e.message)
      }
    }
  }
  confirmVisible.value = true
}

function executeConfirm() {
  if (confirmAction.value) {
    confirmAction.value()
  }
  confirmVisible.value = false
  confirmAction.value = null
}

// ===== Helpers =====
function asEntry(row: unknown): KnowledgeEntrySummary {
  return row as KnowledgeEntrySummary
}

function searchedTypesText(): string {
  if (!searchMeta.value?.searched_knowledge_types?.length) return ''
  return searchMeta.value.searched_knowledge_types
    .map((t) => (KNOWLEDGE_TYPE_MAP as Record<string, StatusDisplay>)[t]?.text ?? t)
    .join('、')
}

// ===== Filters =====
function handleSearch() {
  page.value = 1
  fetchEntries()
}

function handleReset() {
  filters.knowledge_type = ''
  filters.risk_level = ''
  filters.language = ''
  filters.entry_status = ''
  filters.keyword = ''
  filters.tags_filter = ''
  filters.sort = 'updated_at:desc'
  page.value = 1
  fetchEntries()
}

function handlePageChange(p: number) {
  page.value = p
  fetchEntries()
}

function handleSizeChange(s: number) {
  pageSize.value = s
  page.value = 1
  fetchEntries()
}

onMounted(() => {
  fetchEntries()
})
</script>

<template>
  <div class="page-container">
    <AppPageHeader
      title="知识库管理"
      subtitle="管理安全知识条目，支持向量语义检索。分析阶段自动将匹配知识注入 AI 角色上下文。"
    >
      <template #actions>
        <el-button type="primary" @click="openCreateModal">
          <el-icon><Plus /></el-icon>
          新建条目
        </el-button>
      </template>
    </AppPageHeader>

    <!-- Stat cards -->
    <div class="stat-grid">
      <div
        v-for="card in statCards"
        :key="card.type"
        class="stat-card"
      >
        <div class="stat-card__label">
          {{ (KNOWLEDGE_TYPE_MAP as Record<string, StatusDisplay>)[card.type]?.text ?? card.type }}
        </div>
        <div class="stat-card__count">{{ card.count }}</div>
        <div class="stat-card__desc">{{ card.desc }}</div>
      </div>
    </div>

    <!-- Semantic search -->
    <div class="semantic-search">
      <el-input
        v-model="searchQuery"
        placeholder="自然语言语义检索，如「Python SQL 注入的检测模式和修复方案」"
        clearable
        class="semantic-search__input"
        @keyup.enter="doSearch"
        @clear="clearSearch"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
      <el-button type="primary" :loading="searchLoading" @click="doSearch">
        <el-icon><Search /></el-icon>
        语义检索
      </el-button>
      <el-button v-if="searchPerformed" @click="clearSearch">
        清除
      </el-button>
    </div>

    <!-- Search results -->
    <div v-if="searchPerformed" class="search-results">
      <div v-if="searchLoading" v-loading="searchLoading" style="min-height: 80px" />
      <template v-else-if="searchResults.length === 0">
        <AppEmptyState
          title="未找到匹配的知识条目"
          description="尝试调整检索表述或扩大检索范围"
        />
      </template>
      <template v-else>
        <div class="search-results__header">
          语义检索结果 — query: "{{ searchQuery }}"
          — 扫描 {{ searchMeta?.total_scanned ?? 0 }} 条，匹配 {{ searchMeta?.total_matched ?? searchResults.length }} 条，按相似度降序
          <template v-if="searchMeta?.searched_knowledge_types?.length">
            （子库：{{ searchedTypesText() }}）
          </template>
        </div>
        <div
          v-for="item in searchResults"
          :key="item.entry_id"
          class="search-result-item"
        >
          <div class="search-result-item__header">
            <span class="search-result-item__title">{{ item.title }}</span>
            <span class="search-result-item__similarity">
              相似度 {{ (item.similarity * 100).toFixed(1) }}%
            </span>
          </div>
          <div class="search-result-item__snippet">
            {{ item.content_text.slice(0, 200) }}{{ item.content_text.length > 200 ? '...' : '' }}
          </div>
          <div class="search-result-item__meta">
            <AppStatusTag
              :value="item.knowledge_type"
              :map="KNOWLEDGE_TYPE_MAP as Record<string, StatusDisplay>"
              size="small"
            />
            <AppStatusTag
              v-if="item.risk_level"
              :value="item.risk_level"
              :map="RISK_LEVEL_MAP as Record<string, StatusDisplay>"
              size="small"
            />
            <el-tag
              v-for="tag in item.tags.slice(0, 4)"
              :key="tag"
              size="small"
              type="info"
              effect="plain"
            >
              {{ tag }}
            </el-tag>
          </div>
        </div>
      </template>
    </div>

    <!-- Tab bar -->
    <el-card v-if="!searchPerformed" class="entries-card">
      <template #header>
        <div class="card-tabs">
          <span
            class="card-tab"
            :class="{ 'card-tab--active': activeTab === 'entries' }"
            @click="activeTab = 'entries'"
          >
            知识条目
          </span>
          <span
            class="card-tab"
            :class="{ 'card-tab--active': activeTab === 'search' }"
            @click="activeTab = 'search'"
          >
            语义检索
          </span>
        </div>
      </template>

      <!-- ===== Entries Tab ===== -->
      <template v-if="activeTab === 'entries'">
        <!-- Filters -->
        <div class="filter-bar">
          <el-select
            v-model="filters.knowledge_type"
            placeholder="全部子库"
            clearable
            style="width: 160px"
            @change="handleSearch"
          >
            <el-option
              v-for="(display, key) in KNOWLEDGE_TYPE_MAP"
              :key="key"
              :label="display.text"
              :value="key"
            />
          </el-select>

          <el-select
            v-model="filters.risk_level"
            placeholder="全部风险等级"
            clearable
            style="width: 140px"
            @change="handleSearch"
          >
            <el-option
              v-for="(display, key) in RISK_LEVEL_MAP"
              :key="key"
              :label="display.text"
              :value="key"
            />
          </el-select>

          <el-input
            v-model="filters.language"
            placeholder="语言过滤（如 python）"
            clearable
            style="width: 160px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />

          <el-select
            v-model="filters.entry_status"
            placeholder="全部状态"
            clearable
            style="width: 120px"
            @change="handleSearch"
          >
            <el-option
              v-for="(display, key) in ENTRY_STATUS_MAP"
              :key="key"
              :label="display.text"
              :value="key"
            />
          </el-select>

          <el-input
            v-model="filters.keyword"
            placeholder="搜索标题或正文..."
            clearable
            style="width: 200px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>

          <el-input
            v-model="filters.tags_filter"
            placeholder="标签过滤（逗号分隔）"
            clearable
            style="width: 200px"
            @clear="handleSearch"
            @keyup.enter="handleSearch"
          />

          <el-select
            v-model="filters.sort"
            style="width: 160px"
            @change="handleSearch"
          >
            <el-option label="最近更新" value="updated_at:desc" />
            <el-option label="最早更新" value="updated_at:asc" />
            <el-option label="最近创建" value="created_at:desc" />
            <el-option label="最早创建" value="created_at:asc" />
          </el-select>

          <el-button @click="handleSearch">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button v-if="hasActiveFilters" @click="handleReset">
            重置
          </el-button>
        </div>

        <!-- Error -->
        <AppErrorBlock
          v-if="error"
          :message="error.message"
          :request-id="error.requestId"
          retryable
          class="list-error"
          @retry="fetchEntries"
        />

        <!-- Empty -->
        <AppEmptyState
          v-else-if="!loading && entries.length === 0"
          :title="hasActiveFilters ? '没有匹配的知识条目' : '暂无知识条目'"
          :description="
            hasActiveFilters
              ? '尝试调整筛选条件'
              : '创建您的第一个安全知识条目'
          "
          :action-text="hasActiveFilters ? '' : '新建条目'"
          @action="openCreateModal"
        />

        <!-- Table -->
        <template v-else>
          <el-table
            v-loading="loading"
            :data="entries"
            stripe
            row-key="id"
            class="entries-table"
          >
            <el-table-column label="标题" prop="title" min-width="220">
              <template #default="{ row }">
                <div>
                  <span class="entry-title" @click="openEditModal(asEntry(row))">
                    {{ row.title }}
                  </span>
                  <div class="entry-tags">
                    <el-tag
                      v-for="tag in (row.tags ?? []).slice(0, 3)"
                      :key="tag"
                      size="small"
                      type="info"
                      effect="plain"
                    >
                      {{ tag }}
                    </el-tag>
                  </div>
                </div>
              </template>
            </el-table-column>

            <el-table-column label="子库" width="130">
              <template #default="{ row }">
                <AppStatusTag
                  :value="row.knowledge_type"
                  :map="KNOWLEDGE_TYPE_MAP as Record<string, StatusDisplay>"
                  size="small"
                />
              </template>
            </el-table-column>

            <el-table-column label="语言" width="120">
              <template #default="{ row }">
                <template v-if="row.language">
                  <el-tag
                    v-for="lang in row.language.split(',')"
                    :key="lang"
                    size="small"
                    type="info"
                    effect="plain"
                  >
                    {{ lang.trim() }}
                  </el-tag>
                </template>
                <span v-else class="text-muted">—</span>
              </template>
            </el-table-column>

            <el-table-column label="框架" width="120">
              <template #default="{ row }">
                <template v-if="row.framework">
                  <el-tag
                    v-for="fw in row.framework.split(',')"
                    :key="fw"
                    size="small"
                    effect="plain"
                  >
                    {{ fw.trim() }}
                  </el-tag>
                </template>
                <span v-else class="text-muted">—</span>
              </template>
            </el-table-column>

            <el-table-column label="风险等级" width="100">
              <template #default="{ row }">
                <AppStatusTag
                  v-if="row.risk_level"
                  :value="row.risk_level"
                  :map="RISK_LEVEL_MAP as Record<string, StatusDisplay>"
                  size="small"
                />
                <span v-else class="text-muted">—</span>
              </template>
            </el-table-column>

            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <AppStatusTag
                  :value="row.entry_status"
                  :map="ENTRY_STATUS_MAP as Record<string, StatusDisplay>"
                  size="small"
                />
              </template>
            </el-table-column>

            <el-table-column label="版本" width="70" align="center">
              <template #default="{ row }">
                <span class="text-muted">v{{ row.version }}</span>
              </template>
            </el-table-column>

            <el-table-column label="更新时间" width="170">
              <template #default="{ row }">
                {{ formatDateTime(row.updated_at) }}
              </template>
            </el-table-column>

            <el-table-column label="操作" width="220" fixed="right">
              <template #default="{ row }">
                <div class="table-actions" @click.stop>
                  <el-button
                    text
                    size="small"
                    type="primary"
                    @click="openEditModal(asEntry(row))"
                  >
                    编辑
                  </el-button>
                  <el-button
                    v-if="row.entry_status === 'draft' || row.entry_status === 'disabled'"
                    text
                    size="small"
                    type="success"
                    @click="confirmActivate(asEntry(row))"
                  >
                    激活
                  </el-button>
                  <el-button
                    v-if="row.entry_status === 'active'"
                    text
                    size="small"
                    type="warning"
                    @click="confirmDisable(asEntry(row))"
                  >
                    禁用
                  </el-button>
                  <el-button
                    text
                    size="small"
                    type="danger"
                    @click="confirmDelete(asEntry(row))"
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
      </template>

      <!-- ===== Search Tab (quick semantic search from card) ===== -->
      <template v-if="activeTab === 'search'">
        <div class="inline-search-section">
          <el-input
            v-model="searchQuery"
            placeholder="输入自然语言描述进行语义检索..."
            clearable
            class="semantic-search__input--inline"
            @keyup.enter="doSearch"
            @clear="clearSearch"
          >
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>
          <el-button type="primary" :loading="searchLoading" @click="doSearch">
            检索
          </el-button>
        </div>
        <div v-if="searchResults.length > 0" class="inline-results">
          <div class="search-results__header">
            扫描 {{ searchMeta?.total_scanned ?? 0 }} 条，匹配 {{ searchMeta?.total_matched ?? searchResults.length }} 条
          </div>
          <div
            v-for="item in searchResults"
            :key="item.entry_id"
            class="search-result-item"
          >
            <div class="search-result-item__header">
              <span class="search-result-item__title">{{ item.title }}</span>
              <span class="search-result-item__similarity">
                相似度 {{ (item.similarity * 100).toFixed(1) }}%
              </span>
            </div>
            <div class="search-result-item__snippet">
              {{ item.content_text.slice(0, 200) }}{{ item.content_text.length > 200 ? '...' : '' }}
            </div>
            <div class="search-result-item__meta">
              <AppStatusTag
                :value="item.knowledge_type"
                :map="KNOWLEDGE_TYPE_MAP as Record<string, StatusDisplay>"
                size="small"
              />
              <AppStatusTag
                v-if="item.risk_level"
                :value="item.risk_level"
                :map="RISK_LEVEL_MAP as Record<string, StatusDisplay>"
                size="small"
              />
            </div>
          </div>
        </div>
        <AppEmptyState
          v-else-if="searchLoading"
          title="检索中..."
        />
        <AppEmptyState
          v-else
          title="语义检索"
          description="输入自然语言描述，系统将基于向量相似度返回最匹配的知识条目"
        />
      </template>
    </el-card>

    <!-- ===== Create/Edit Modal ===== -->
    <el-dialog
      v-model="modalVisible"
      :title="modalTitle"
      width="720px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form v-loading="isEditing && detailLoading" :model="form" label-position="top">
        <el-form-item label="标题" required>
          <el-input
            v-model="form.title"
            placeholder="如：SQL 注入检测模式"
            maxlength="255"
          />
        </el-form-item>

        <el-form-item label="Markdown 正文" required>
          <el-input
            v-model="form.content_text"
            type="textarea"
            :rows="8"
            placeholder="## 漏洞模式&#10;&#10;### 常见危险函数&#10;- 拼接 SQL 字符串&#10;- ..."
          />
        </el-form-item>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="子库分类" required>
              <el-select v-model="form.knowledge_type" style="width: 100%">
                <el-option
                  v-for="(display, key) in KNOWLEDGE_TYPE_MAP"
                  :key="key"
                  :label="display.text"
                  :value="key"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="风险等级">
              <el-select
                v-model="form.risk_level"
                placeholder="— 不关联 —"
                clearable
                style="width: 100%"
              >
                <el-option
                  v-for="(display, key) in RISK_LEVEL_MAP"
                  :key="key"
                  :label="display.text"
                  :value="key"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="编程语言">
              <el-input
                v-model="form.language"
                placeholder="多值以逗号分隔，如 python,java,go"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="框架">
              <el-input
                v-model="form.framework"
                placeholder="多值以逗号分隔，如 django,spring"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-form-item label="标签">
              <el-input
                v-model="form.tags"
                placeholder="逗号分隔，如 sqli, injection, input-validation"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="来源类型">
              <el-select v-model="form.source_type" style="width: 100%">
                <el-option
                  v-for="(display, key) in KNOWLEDGE_SOURCE_TYPE_MAP"
                  :key="key"
                  :label="display.text"
                  :value="key"
                />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="外部来源链接">
          <el-input
            v-model="form.source_url"
            placeholder="如 https://cwe.mitre.org/data/definitions/89.html"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="modalVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" :disabled="detailLoading" @click="handleSave">
          {{ isEditing ? '保存修改' : '保存为草稿' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- ===== Confirm Dialog ===== -->
    <el-dialog
      v-model="confirmVisible"
      title="操作确认"
      width="420px"
      :close-on-click-modal="false"
    >
      <div class="confirm-content">
        <el-icon class="confirm-icon" :size="40" color="var(--color-warning)">
          <WarningFilled />
        </el-icon>
        <p class="confirm-text">{{ confirmMessage }}</p>
      </div>
      <template #footer>
        <el-button @click="confirmVisible = false">取消</el-button>
        <el-button type="danger" @click="executeConfirm">
          确认
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
/* Stat grid */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.stat-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-lg);
}

.stat-card__label {
  font-size: var(--font-size-xs);
  color: var(--color-text-placeholder);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--spacing-xs);
}

.stat-card__count {
  font-size: var(--font-size-2xl);
  font-weight: 700;
  color: var(--color-text-primary);
}

.stat-card__desc {
  font-size: var(--font-size-xs);
  color: var(--color-text-secondary);
  margin-top: var(--spacing-xs);
}

/* Semantic search */
.semantic-search {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
}

.semantic-search__input {
  flex: 1;
}

/* Search results */
.search-results {
  margin-bottom: var(--spacing-lg);
}

.search-results__header {
  font-size: var(--font-size-sm);
  color: var(--color-text-placeholder);
  margin-bottom: var(--spacing-sm);
}

.search-result-item {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--spacing-md);
  margin-bottom: var(--spacing-sm);
}

.search-result-item:hover {
  border-color: var(--color-primary-light);
}

.search-result-item__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--spacing-sm);
}

.search-result-item__title {
  font-size: var(--font-size-md);
  font-weight: 600;
  color: var(--color-primary);
}

.search-result-item__similarity {
  font-size: var(--font-size-xs);
  color: var(--color-text-placeholder);
  flex-shrink: 0;
  margin-left: var(--spacing-md);
}

.search-result-item__snippet {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

.search-result-item__meta {
  display: flex;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
  flex-wrap: wrap;
}

/* Card tabs */
.entries-card {
  margin-bottom: var(--spacing-lg);
}

.card-tabs {
  display: flex;
  gap: 0;
}

.card-tab {
  padding: 8px 20px;
  font-size: var(--font-size-base);
  color: var(--color-text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all var(--transition-fast);
  user-select: none;
}

.card-tab:hover {
  color: var(--color-text-regular);
}

.card-tab--active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
  font-weight: 500;
}

/* Inline search tab */
.inline-search-section {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
}

.semantic-search__input--inline {
  flex: 1;
}

.inline-results {
  margin-top: var(--spacing-md);
}

/* Filters */
.filter-bar {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
  flex-wrap: wrap;
}

.list-error {
  margin-bottom: var(--spacing-lg);
}

/* Table */
.entries-table {
  cursor: default;
}

.entry-title {
  color: var(--color-primary);
  font-weight: 500;
  cursor: pointer;
}

.entry-title:hover {
  text-decoration: underline;
}

.entry-tags {
  display: flex;
  gap: 4px;
  margin-top: 4px;
  flex-wrap: wrap;
}

.text-muted {
  color: var(--color-text-placeholder);
}

.table-actions {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

/* Pagination */
.list-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: var(--spacing-lg);
}

/* Confirm dialog */
.confirm-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: var(--spacing-md) 0;
}

.confirm-icon {
  margin-bottom: var(--spacing-md);
}

.confirm-text {
  font-size: var(--font-size-base);
  color: var(--color-text-regular);
  line-height: 1.6;
}

/* Responsive */
@media (max-width: 1200px) {
  .stat-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stat-grid {
    grid-template-columns: 1fr;
  }
}
</style>
