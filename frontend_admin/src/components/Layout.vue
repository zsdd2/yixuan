<template>
  <div class="layout">
    <aside class="sidebar">
      <div class="brand">
        <div class="brand-mark">艺</div>
        <div>
          <div class="brand-name">艺选</div>
          <div class="brand-sub">YIXUAN</div>
        </div>
      </div>

      <nav class="nav">
        <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
          <el-icon><Monitor /></el-icon>
          <span>进度工作台</span>
        </router-link>
        <router-link to="/analytics" class="nav-item" :class="{ active: $route.path === '/analytics' }">
          <el-icon><DataAnalysis /></el-icon>
          <span>数据罗盘</span>
        </router-link>
        <router-link to="/projects" class="nav-item" :class="{ active: $route.path === '/projects' }">
          <el-icon><Folder /></el-icon>
          <span>项目管理</span>
        </router-link>
        <router-link to="/portfolio" class="nav-item" :class="{ active: $route.path === '/portfolio' }">
          <el-icon><Picture /></el-icon>
          <span>作品中心</span>
        </router-link>
        <router-link to="/materials" class="nav-item" :class="{ active: $route.path === '/materials' }">
          <el-icon><Collection /></el-icon>
          <span>素材中心</span>
        </router-link>
        <router-link to="/clients" class="nav-item" :class="{ active: $route.path === '/clients' }">
          <el-icon><User /></el-icon>
          <span>客户管理</span>
        </router-link>
        <router-link v-if="userStore.isAdmin" to="/admin/users" class="nav-item" :class="{ active: $route.path === '/admin/users' }">
          <el-icon><UserFilled /></el-icon>
          <span>用户管理</span>
        </router-link>
        <div class="nav-item nav-group" :class="{ active: isSettingsPage }" @click="toggleSettings">
          <el-icon><Setting /></el-icon>
          <span>设置中心</span>
        </div>
        <template v-if="settingsExpanded || isSettingsPage">
          <router-link to="/settings/basic" class="nav-item sub-item" :class="{ active: $route.path === '/settings/basic' }">基础设置</router-link>
          <router-link to="/settings/images" class="nav-item sub-item" :class="{ active: $route.path === '/settings/images' }">系统图库</router-link>
          <router-link to="/settings/templates" class="nav-item sub-item" :class="{ active: $route.path === '/settings/templates' }">项目模板</router-link>
          <router-link to="/settings/tags" class="nav-item sub-item" :class="{ active: $route.path === '/settings/tags' }">标签管理</router-link>
          <router-link v-if="userStore.isAdmin" to="/settings/users" class="nav-item sub-item" :class="{ active: $route.path === '/settings/users' }">用户设置</router-link>
        </template>
      </nav>

      <div class="sidebar-tools">
        <button class="tool-button">
          <el-icon><Bell /></el-icon>
          <span class="badge">12</span>
        </button>
        <button class="tool-button" @click="router.push('/settings/basic')">
          <el-icon><Setting /></el-icon>
        </button>
        <el-dropdown trigger="click" @command="handleCommand">
          <button class="tool-button">
            <el-icon><User /></el-icon>
          </button>
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
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import {
  Bell,
  Collection,
  DataAnalysis,
  Folder,
  Monitor,
  Picture,
  Setting,
  User,
  UserFilled,
} from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/userStore'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const settingsExpanded = ref(false)

const isSettingsPage = computed(() => route.path.startsWith('/settings'))

function toggleSettings() {
  settingsExpanded.value = !settingsExpanded.value
}

function handleCommand(command: string) {
  if (command === 'profile') {
    router.push('/user-center')
  } else if (command === 'logout') {
    ElMessageBox.confirm('确定要退出登录吗？', '提示', { type: 'warning' })
      .then(() => userStore.logout())
      .catch(() => {})
  }
}
</script>

<style scoped>
.layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: #f4f8fc;
}

.sidebar {
  width: 148px;
  min-width: 148px;
  height: 100vh;
  background: linear-gradient(180deg, #07192b 0%, #0a2035 54%, #07192b 100%);
  color: #c9d6e6;
  display: flex;
  flex-direction: column;
  box-shadow: 10px 0 28px rgba(8, 31, 54, 0.16);
}

.brand {
  height: 78px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 20px;
}

.brand-mark {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  color: #fff;
  font-weight: 800;
  background: linear-gradient(135deg, #0c8bff, #2563eb 58%, #63b3ff);
}

.brand-name {
  font-size: 18px;
  line-height: 20px;
  color: #fff;
  font-weight: 800;
  letter-spacing: 2px;
}

.brand-sub {
  margin-top: 2px;
  font-size: 8px;
  color: #8ba4bf;
  letter-spacing: 3px;
}

.nav {
  flex: 1;
  padding: 4px 10px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.nav-item {
  height: 42px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 12px;
  border-radius: 8px;
  color: #c9d6e6;
  text-decoration: none;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.18s ease, color 0.18s ease, transform 0.18s ease;
}

.nav-item .el-icon {
  font-size: 18px;
}

.nav-item:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}

.nav-item.active {
  color: #fff;
  background: linear-gradient(135deg, #1d75ff, #276ef1);
  box-shadow: 0 10px 22px rgba(29, 117, 255, 0.28);
}

.nav-group {
  user-select: none;
}

.sub-item {
  height: 34px;
  padding-left: 40px;
  font-size: 12px;
  color: #9eb0c4;
}

.sidebar-tools {
  padding: 0 0 22px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 18px;
}

.tool-button {
  position: relative;
  width: 34px;
  height: 34px;
  border: 0;
  border-radius: 10px;
  color: #b8c8da;
  background: transparent;
  display: grid;
  place-items: center;
  cursor: pointer;
}

.tool-button:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}

.tool-button .el-icon {
  font-size: 19px;
}

.badge {
  position: absolute;
  top: 0;
  right: 0;
  min-width: 17px;
  height: 17px;
  padding: 0 4px;
  border-radius: 999px;
  color: #fff;
  background: #ff3b2f;
  font-size: 10px;
  line-height: 17px;
}

.main-content {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  background: #f4f8fc;
}
</style>
