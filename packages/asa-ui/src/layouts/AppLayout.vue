<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

interface NavItem {
  index: string
  title: string
  icon: string
  requiresProject: boolean
}

const isAuthPage = computed(
  () => route.name === 'SystemInit' || route.name === 'Login',
)

const isFullPage = computed(
  () =>
    isAuthPage.value ||
    route.name === 'Forbidden' ||
    route.name === 'NotFound',
)

const currentProjectId = computed(
  () => (route.params.projectId as string) ?? null,
)

const navItems = computed<NavItem[]>(() => {
  const items: NavItem[] = [
    { index: '/projects', title: '项目列表', icon: '⊞', requiresProject: false },
    { index: '/projects/:projectId/monitor', title: '实时监控', icon: '◉', requiresProject: true },
    { index: '/projects/:projectId/vulnerabilities', title: '漏洞管理', icon: '⚠', requiresProject: true },
    { index: '/projects/:projectId/attack-paths', title: '攻击路径', icon: '⛓', requiresProject: true },
    { index: '/projects/:projectId/report', title: '报告中心', icon: '☰', requiresProject: true },
  ]
  if (authStore.isAdmin) {
    items.push({ index: '/knowledge', title: '知识库', icon: '📚', requiresProject: false })
    items.push({ index: '/system/config', title: '系统配置', icon: '⚙', requiresProject: false })
  }
  return items
})

function resolveNavPath(item: NavItem): string {
  if (!item.requiresProject) return item.index
  if (currentProjectId.value) {
    return item.index.replace(':projectId', currentProjectId.value)
  }
  return '#'
}

function isNavActive(item: NavItem): boolean {
  if (item.index === '/projects') {
    return (
      route.path === '/projects' ||
      route.path === '/projects/new'
    )
  }
  if (item.requiresProject && currentProjectId.value) {
    const resolved = item.index.replace(':projectId', currentProjectId.value)
    return route.path.startsWith(resolved)
  }
  if (item.index === '/knowledge') {
    return route.path.startsWith('/knowledge')
  }
  if (item.index === '/system/config') {
    return route.path.startsWith('/system/config')
  }
  return false
}

function isNavDisabled(item: NavItem): boolean {
  return item.requiresProject && !currentProjectId.value
}

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>

<template>
  <div v-if="isFullPage" class="auth-layout">
    <slot />
  </div>
  <el-container v-else class="app-layout">
    <!-- 侧边栏 -->
    <aside class="app-sidebar">
      <!-- Logo 区 -->
      <div class="sidebar-logo">
        <span class="sidebar-logo__icon">⬡</span>
        <span class="sidebar-logo__text">ASA System</span>
      </div>

      <!-- 导航区 -->
      <nav class="sidebar-nav">
        <router-link
          v-for="item in navItems"
          :key="item.index"
          :to="isNavDisabled(item) ? '' : resolveNavPath(item)"
          class="sidebar-nav__item"
          :class="{
            'sidebar-nav__item--active': isNavActive(item),
            'sidebar-nav__item--disabled': isNavDisabled(item),
          }"
          :tabindex="isNavDisabled(item) ? -1 : undefined"
          @click.prevent="
            isNavDisabled(item)
              ? undefined
              : router.push(resolveNavPath(item))
          "
        >
          <span class="sidebar-nav__icon">{{ item.icon }}</span>
          <span class="sidebar-nav__label">{{ item.title }}</span>
        </router-link>
      </nav>

      <!-- 底部用户区 -->
      <div class="sidebar-bottom">
        <div class="sidebar-avatar">
          {{ (authStore.username ?? 'U').charAt(0).toUpperCase() }}
        </div>
        <span class="sidebar-username">{{ authStore.username }}</span>
      </div>
    </aside>

    <!-- 主区域 -->
    <el-container>
      <el-header class="app-layout__header" height="56px">
        <div class="app-layout__header-left">
          <el-breadcrumb separator="›">
            <el-breadcrumb-item :to="{ path: '/projects' }">
              首页
            </el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta.title">
              {{ route.meta.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="app-layout__header-right">
          <span class="app-layout__user">
            {{ authStore.username }}
            <el-tag
              v-if="authStore.isAdmin"
              size="small"
              type="danger"
              effect="plain"
            >
              管理员
            </el-tag>
          </span>
          <el-button text type="danger" @click="handleLogout">
            退出
          </el-button>
        </div>
      </el-header>
      <el-main class="app-layout__main">
        <slot />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
}

/* ===== 侧边栏 ===== */

.app-sidebar {
  width: 240px;
  background: var(--color-bg-card);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-logo {
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-bottom: 1px solid var(--color-border);
  padding: 0 var(--spacing-md);
}

.sidebar-logo__icon {
  font-size: 22px;
  color: var(--color-primary);
}

.sidebar-logo__text {
  font-size: var(--font-size-lg);
  font-weight: 700;
  color: var(--color-primary);
  letter-spacing: 1px;
}

/* 导航 */
.sidebar-nav {
  flex: 1;
  padding: var(--spacing-sm);
  display: flex;
  flex-direction: column;
  gap: 4px;
  overflow-y: auto;
}

.sidebar-nav__item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  font-size: var(--font-size-base);
  text-decoration: none;
  color: var(--color-text-secondary);
  transition: background var(--transition-fast), color var(--transition-fast);
  cursor: pointer;
}

.sidebar-nav__item:hover:not(.sidebar-nav__item--disabled) {
  background: var(--color-fill-hover);
  color: var(--color-text-regular);
}

.sidebar-nav__item--active {
  background: var(--color-primary);
  color: #ffffff;
}

.sidebar-nav__item--active .sidebar-nav__icon {
  color: #ffffff;
}

.sidebar-nav__item--disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.sidebar-nav__icon {
  font-size: 18px;
  width: 22px;
  text-align: center;
  flex-shrink: 0;
}

.sidebar-nav__label {
  white-space: nowrap;
  font-weight: 400;
}

/* 底部 */
.sidebar-bottom {
  padding: var(--spacing-md);
  border-top: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  gap: 10px;
}

.sidebar-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--font-size-base);
  font-weight: 600;
  flex-shrink: 0;
}

.sidebar-username {
  font-size: var(--font-size-sm);
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* ===== Header ===== */

.app-layout__header {
  background: var(--color-bg-card);
  border-bottom: 1px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--spacing-lg);
}

.app-layout__header-left {
  display: flex;
  align-items: center;
}

.app-layout__header-right {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
}

.app-layout__user {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  font-size: var(--font-size-base);
  color: var(--color-text-regular);
}

/* ===== Main ===== */

.app-layout__main {
  background: var(--color-bg-page);
  min-height: calc(100vh - var(--header-height));
}

/* ===== Auth 页面 ===== */

.auth-layout {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-page);
}
</style>
