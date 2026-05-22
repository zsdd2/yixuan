<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="sidebar-brand">
        <span class="brand-icon">📷</span>
        <span class="brand-text">摄影项目管理</span>
      </div>

      <nav class="sidebar-nav">
        <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
          <span class="nav-icon">🗂️</span>
          <span>进度控制台</span>
        </router-link>
        <router-link to="/projects" class="nav-item" :class="{ active: $route.path === '/projects' }">
          <span class="nav-icon">📁</span>
          <span>项目中心</span>
        </router-link>
        <router-link to="/portfolio" class="nav-item" :class="{ active: $route.path === '/portfolio' }">
          <span class="nav-icon">🖼️</span>
          <span>作品中心</span>
        </router-link>
        <router-link to="/materials" class="nav-item" :class="{ active: $route.path === '/materials' }">
          <span class="nav-icon">▣</span>
          <span>素材中心</span>
        </router-link>
        <router-link to="/clients" class="nav-item" :class="{ active: $route.path === '/clients' }">
          <span class="nav-icon">👤</span>
          <span>客户中心</span>
        </router-link>
        <router-link v-if="userStore.isAdmin" to="/admin/users" class="nav-item" :class="{ active: $route.path === '/admin/users' }">
          <span class="nav-icon">👥</span>
          <span>用户管理</span>
        </router-link>
        <div class="nav-group-title" @click="toggleSettings">
          <span class="nav-icon">⚙️</span>
          <span>设置中心</span>
          <span class="nav-arrow" :class="{ expanded: settingsExpanded || isSettingsPage }">›</span>
        </div>
        <template v-if="settingsExpanded || isSettingsPage">
          <router-link to="/settings/basic" class="nav-item sub-item" :class="{ active: $route.path === '/settings/basic' }">
            <span>基础设置</span>
          </router-link>
          <router-link to="/settings/images" class="nav-item sub-item" :class="{ active: $route.path === '/settings/images' }">
            <span>系统图库</span>
          </router-link>
          <router-link to="/settings/templates" class="nav-item sub-item" :class="{ active: $route.path === '/settings/templates' }">
            <span>项目模板</span>
          </router-link>
          <router-link to="/settings/tags" class="nav-item sub-item" :class="{ active: $route.path === '/settings/tags' }">
            <span>标签管理</span>
          </router-link>
          <router-link v-if="userStore.isAdmin" to="/settings/users" class="nav-item sub-item" :class="{ active: $route.path === '/settings/users' }">
            <span>用户管理</span>
          </router-link>
        </template>
      </nav>

      <div class="sidebar-footer">
        <el-dropdown trigger="click" @command="handleCommand">
          <div class="user-info">
            <div class="user-avatar">{{ userStore.userInfo?.display_name?.charAt(0) || 'U' }}</div>
            <div class="user-details">
              <div class="user-name">{{ userStore.userInfo?.display_name }}</div>
              <div class="user-role">{{ roleLabel }}</div>
            </div>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人中心</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </aside>

    <main class="main-content">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useUserStore } from '@/stores/userStore'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const settingsExpanded = ref(false)

const isSettingsPage = computed(() => route.path.startsWith('/settings'))

const roleLabel = computed(() => {
  const roleMap: Record<string, string> = {
    super_admin: '超级管理员',
    admin: '管理员',
    staff: '普通员工',
    client: '客户',
  }
  return roleMap[userStore.userInfo?.role || ''] || '未知'
})

function toggleSettings() {
  settingsExpanded.value = !settingsExpanded.value
}

function handleCommand(command: string) {
  if (command === 'profile') {
    router.push('/user-center')
  } else if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      type: 'warning',
    }).then(() => {
      userStore.logout()
    }).catch(() => {
      // 用户取消
    })
  }
}
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: 210px;
  min-width: 210px;
  background: #FFFFFF;
  border-right: 1px solid #F0F0F0;
  display: flex;
  flex-direction: column;
}

.sidebar-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 32px 24px 28px;
  border-bottom: 1px solid #F0F0F0;
}

.brand-icon {
  font-size: 18px;
}

.brand-text {
  font-size: 15px;
  font-weight: 700;
  color: #111827;
  letter-spacing: 0.01em;
}

.sidebar-nav {
  flex: 1;
  padding: 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.nav-divider {
  height: 1px;
  background: #F0F0F0;
  margin: 10px 8px;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  border-radius: 12px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: #4B5563;
  transition: all 0.15s ease;
  text-decoration: none;
}

.nav-item:hover {
  background: #F9FAFB;
  color: #374151;
}

.nav-item.active {
  background: #EFF6FF;
  color: #2563EB;
  font-weight: 600;
}

.nav-icon {
  font-size: 16px;
  width: 22px;
  text-align: center;
  flex-shrink: 0;
}

.nav-group-title {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px 6px;
  font-size: 12px;
  font-weight: 600;
  color: #9CA3AF;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  cursor: pointer;
  user-select: none;
  transition: color 0.15s;
}

.nav-group-title:hover {
  color: #6B7280;
}

.nav-arrow {
  margin-left: auto;
  font-size: 14px;
  transition: transform 0.2s ease;
  transform: rotate(0deg);
}

.nav-arrow.expanded {
  transform: rotate(90deg);
}

.sub-item {
  padding-left: 52px !important;
  font-size: 13px;
}

.main-content {
  flex: 1;
  overflow-y: auto;
  background: #F9FAFB;
}

.sidebar-footer {
  padding: 16px;
  border-top: 1px solid #F0F0F0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.user-info:hover {
  background: #F9FAFB;
}

.user-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}

.user-details {
  flex: 1;
  min-width: 0;
}

.user-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-role {
  font-size: 12px;
  color: #6B7280;
  margin-top: 2px;
}
</style>
