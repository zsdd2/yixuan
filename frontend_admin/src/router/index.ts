import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/userStore'
import { ElMessage } from 'element-plus'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('../views/LoginView.vue'),
      meta: { requiresAuth: false },
    },
    {
      path: '/',
      redirect: '/analytics',
      meta: { requiresAuth: true },
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('../views/Dashboard.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/analytics',
      name: 'AnalyticsCompass',
      component: () => import('../views/AnalyticsCompass.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/project/:id',
      name: 'ProjectDetail',
      component: () => import('../views/ProjectDetail.vue'),
      props: true,
      meta: { requiresAuth: true },
    },
    {
      path: '/project/:id/edit',
      name: 'ProjectEdit',
      component: () => import('../views/ProjectEdit.vue'),
      props: true,
      meta: { requiresAuth: true },
    },
    {
      path: '/project/:id/import',
      name: 'ImportCenter',
      component: () => import('../views/ImportCenter.vue'),
      props: true,
      meta: { requiresAuth: true },
    },
    {
      path: '/projects',
      name: 'ProjectCenter',
      component: () => import('../views/ProjectCenter.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/portfolio',
      name: 'PortfolioCenter',
      component: () => import('../views/PortfolioCenter.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/materials',
      name: 'MaterialCenter',
      component: () => import('../views/MaterialCenter.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/clients',
      name: 'ClientCenter',
      component: () => import('../views/ClientCenter.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/clients/:clientId/projects',
      name: 'ClientProjects',
      component: () => import('../views/ClientProjects.vue'),
      props: true,
      meta: { requiresAuth: true },
    },
    {
      path: '/user-center',
      name: 'UserCenter',
      component: () => import('../views/UserCenter.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/admin/users',
      name: 'AdminUserPanel',
      component: () => import('../views/AdminUserPanel.vue'),
      meta: { requiresAuth: true, roles: ['super_admin', 'admin'] },
    },
    {
      path: '/settings',
      redirect: '/settings/basic',
    },
    {
      path: '/settings/basic',
      name: 'SettingsBasic',
      component: () => import('../views/SettingsBasic.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/settings/images',
      name: 'SettingsImages',
      component: () => import('../views/SettingsImages.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/settings/templates',
      name: 'SettingsTemplates',
      component: () => import('../views/SettingsTemplates.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/settings/tags',
      name: 'SettingsTags',
      component: () => import('../views/SettingsTags.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/settings/users',
      name: 'SettingsUsers',
      component: () => import('../views/SettingsUsers.vue'),
      meta: { requiresAuth: true, roles: ['super_admin', 'admin'] },
    },
    {
      path: '/share/:token',
      name: 'ReviewPage',
      component: () => import('../views/ReviewPage.vue'),
      props: true,
      meta: { requiresAuth: false },
    },
    {
      path: '/delivery/:token',
      name: 'DeliveryPage',
      component: () => import('../views/DeliveryPage.vue'),
      props: true,
      meta: { requiresAuth: false },
    },
    {
      path: '/kanban-demo',
      name: 'KanbanDemo',
      component: () => import('../views/KanbanDemo.vue'),
      meta: { requiresAuth: true },
    },
  ],
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const userStore = useUserStore()

  // 公开页面（审核页、交付页）直接放行
  if (to.path.startsWith('/share/') || to.path.startsWith('/delivery/')) {
    return next()
  }

  // 登录页：已登录用户重定向至首页
  if (to.path === '/login') {
    if (userStore.isAuthenticated) {
      return next('/analytics')
    }
    return next()
  }

  // 需要认证的页面
  if (to.meta.requiresAuth && !userStore.isAuthenticated) {
    return next('/login')
  }

  // 角色权限检查
  if (to.meta.roles && Array.isArray(to.meta.roles)) {
    const userRole = userStore.userInfo?.role
    if (!userRole || !to.meta.roles.includes(userRole)) {
      ElMessage.error('无权访问此页面')
      return next('/')
    }
  }

  next()
})

export default router
