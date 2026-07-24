<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { RISK_LEVEL_MAP, VERIFY_STATUS_MAP, type StatusDisplay } from '@/contracts'
import { getAttackPathDetail } from '../api/attack-path.api'
import { ApiError } from '@/services/http/errors'
import { formatDateTime } from '@/shared/utils/format'
import AppStatusTag from '@/shared/components/AppStatusTag.vue'
import AppPageHeader from '@/shared/components/AppPageHeader.vue'
import AppErrorBlock from '@/shared/components/AppErrorBlock.vue'
import AppLoadingSkeleton from '@/shared/components/AppLoadingSkeleton.vue'
import type { AttackPathDetail } from '@/contracts'

const route = useRoute()
const router = useRouter()
const projectId = route.params.projectId as string
const pathId = route.params.attackPathId as string

const path = ref<AttackPathDetail | null>(null)
const loading = ref(false)
const error = ref<ApiError | null>(null)

async function fetchDetail() {
  loading.value = true
  error.value = null
  try {
    path.value = await getAttackPathDetail(projectId, pathId)
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

function goToVuln(vulnId: string) {
  router.push(`/projects/${projectId}/vulnerabilities/${vulnId}`)
}

onMounted(() => fetchDetail())
</script>

<template>
  <div class="page-container">
    <AppLoadingSkeleton v-if="loading" variant="detail" />

    <AppErrorBlock
      v-else-if="error"
      :message="error.message"
      :request-id="error.requestId"
      retryable
      @retry="fetchDetail"
    />

    <template v-else-if="path">
      <AppPageHeader :title="path.path_title">
        <template #actions>
          <el-button @click="router.push(`/projects/${projectId}/attack-paths`)">
            返回列表
          </el-button>
        </template>
      </AppPageHeader>

      <div class="detail-grid">
        <!-- 基本信息 -->
        <div class="detail-section">
          <h2 class="detail-section__title">基本信息</h2>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="路径编号">
              {{ path.path_code }}
            </el-descriptions-item>
            <el-descriptions-item label="路径摘要">
              {{ path.path_summary }}
            </el-descriptions-item>
            <el-descriptions-item label="最终影响">
              <span class="impact-text">{{ path.final_impact_text }}</span>
            </el-descriptions-item>
            <el-descriptions-item label="发现时间">
              {{ formatDateTime(path.created_at) }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <!-- 攻击步骤 -->
        <div class="detail-section">
          <h2 class="detail-section__title">
            攻击步骤（{{ path.steps.length }} 步）
          </h2>

          <el-timeline>
            <el-timeline-item
              v-for="step in path.steps"
              :key="step.step_order"
              :timestamp="`步骤 ${step.step_order}`"
              placement="top"
            >
              <div class="step-card">
                <p class="step-card__text">{{ step.step_text }}</p>
                <div class="step-card__vuln">
                  <span class="step-card__label">关联漏洞：</span>
                  <el-button
                    text
                    type="primary"
                    @click="goToVuln(step.vulnerability.id)"
                  >
                    {{ step.vulnerability.vuln_code }}
                    {{ step.vulnerability.vuln_title }}
                  </el-button>
                  <AppStatusTag
                    :value="step.vulnerability.risk_level"
                    :map="RISK_LEVEL_MAP as Record<string, StatusDisplay>"
                    size="small"
                  />
                  <AppStatusTag
                    :value="step.vulnerability.verify_status"
                    :map="VERIFY_STATUS_MAP as Record<string, StatusDisplay>"
                    size="small"
                  />
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.detail-grid {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-lg);
}

.impact-text {
  color: var(--color-danger);
  font-weight: 500;
}

.step-card {
  padding: var(--spacing-md);
  background: var(--color-bg-page);
  border-radius: var(--radius-md);
}

.step-card__text {
  font-size: var(--font-size-base);
  color: var(--color-text-regular);
  line-height: 1.7;
  margin-bottom: var(--spacing-sm);
}

.step-card__vuln {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.step-card__label {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
}
</style>
