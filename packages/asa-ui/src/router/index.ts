import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth.store'

const routes: RouteRecordRaw[] = [
  {
    path: '/system/init',
    name: 'SystemInit',
    component: () => import('@/modules/auth/pages/SystemInitPage.vue'),
    meta: { requiresInit: true, title: '系统初始化' },
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/modules/auth/pages/LoginPage.vue'),
    meta: { requiresGuest: true, title: '登录' },
  },
  {
    path: '/',
    redirect: '/projects',
  },
  {
    path: '/projects',
    name: 'ProjectList',
    component: () => import('@/modules/projects/pages/ProjectListPage.vue'),
    meta: { requiresAuth: true, title: '项目列表' },
  },
  {
    path: '/projects/new',
    name: 'ProjectCreate',
    component: () => import('@/modules/projects/pages/ProjectCreatePage.vue'),
    meta: { requiresAuth: true, title: '创建项目' },
  },
  {
    path: '/projects/:projectId',
    name: 'ProjectDetail',
    component: () => import('@/modules/projects/pages/ProjectDetailPage.vue'),
    meta: { requiresAuth: true, title: '项目详情' },
    props: true,
  },
  {
    path: '/projects/:projectId/monitor',
    name: 'ProjectMonitor',
    component: () => import('@/modules/monitoring/pages/MonitorPage.vue'),
    meta: { requiresAuth: true, title: '实时监控' },
    props: true,
  },
  {
    path: '/projects/:projectId/vulnerabilities',
    name: 'VulnerabilityList',
    component: () => import('@/modules/vulnerabilities/pages/VulnerabilityListPage.vue'),
    meta: { requiresAuth: true, title: '漏洞列表' },
    props: true,
  },
  {
    path: '/projects/:projectId/vulnerabilities/:vulnerabilityId',
    name: 'VulnerabilityDetail',
    component: () => import('@/modules/vulnerabilities/pages/VulnerabilityDetailPage.vue'),
    meta: { requiresAuth: true, title: '漏洞详情' },
    props: true,
  },
  {
    path: '/projects/:projectId/attack-paths',
    name: 'AttackPathList',
    component: () => import('@/modules/attack-paths/pages/AttackPathListPage.vue'),
    meta: { requiresAuth: true, title: '攻击路径列表' },
    props: true,
  },
  {
    path: '/projects/:projectId/attack-paths/:attackPathId',
    name: 'AttackPathDetail',
    component: () => import('@/modules/attack-paths/pages/AttackPathDetailPage.vue'),
    meta: { requiresAuth: true, title: '攻击路径详情' },
    props: true,
  },
  {
    path: '/projects/:projectId/report',
    name: 'ProjectReport',
    component: () => import('@/modules/reports/pages/ReportPage.vue'),
    meta: { requiresAuth: true, title: '评估报告' },
    props: true,
  },
  {
    path: '/system/config',
    name: 'SystemConfig',
    component: () => import('@/modules/config/pages/SystemConfigPage.vue'),
    meta: { requiresAuth: true, requiresAdmin: true, title: '系统配置' },
  },
  {
    path: '/403',
    name: 'Forbidden',
    component: () => import('@/modules/auth/pages/ForbiddenPage.vue'),
    meta: { title: '无权访问' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/modules/auth/pages/NotFoundPage.vue'),
    meta: { title: '页面不存在' },
  },
]

export const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

// UUID 格式校验
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i

router.beforeEach(async (to, _from, next) => {
  const authStore = useAuthStore()

  // 校验路由参数中的 UUID
  const projectId = to.params.projectId as string | undefined
  const vulnerabilityId = to.params.vulnerabilityId as string | undefined
  const attackPathId = to.params.attackPathId as string | undefined

  if (projectId && !UUID_RE.test(projectId)) {
    next({ name: 'NotFound' })
    return
  }
  if (vulnerabilityId && !UUID_RE.test(vulnerabilityId)) {
    next({ name: 'NotFound' })
    return
  }
  if (attackPathId && !UUID_RE.test(attackPathId)) {
    next({ name: 'NotFound' })
    return
  }

  // 初始化页：仅系统未初始化时允许
  if (to.meta.requiresInit) {
    if (authStore.isSystemInitialized === true) {
      next({ name: 'Login' })
      return
    }
    next()
    return
  }

  // 游客页（登录页）：已登录用户重定向到项目列表
  if (to.meta.requiresGuest) {
    if (authStore.isAuthenticated) {
      next({ name: 'ProjectList' })
      return
    }
    // 系统未初始化则跳初始化页
    if (authStore.isSystemInitialized === false) {
      next({ name: 'SystemInit' })
      return
    }
    next()
    return
  }

  // 需要认证的页面
  if (to.meta.requiresAuth) {
    // 系统状态未确定时等待
    if (authStore.isSystemInitialized === null) {
      try {
        await authStore.checkSystemStatus()
      } catch {
        next({ name: 'Login' })
        return
      }
    }

    if (!authStore.isAuthenticated) {
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }

    // 管理员页面
    if (to.meta.requiresAdmin && !authStore.isAdmin) {
      next({ name: 'Forbidden' })
      return
    }

    next()
    return
  }

  next()
})

// 设置页面标题
router.afterEach((to) => {
  const title = (to.meta.title as string) ?? 'ASA System'
  document.title = `${title} - ASA`
})
