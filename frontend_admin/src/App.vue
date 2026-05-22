<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import Layout from './components/Layout.vue'

const route = useRoute()

// 客户审核页面、交付页面、登录页面不使用 Admin 布局
const isGuestPage = computed(() =>
  route.path.startsWith('/share/') ||
  route.path.startsWith('/delivery/') ||
  route.path === '/login'
)
</script>

<template>
  <div id="app">
    <!-- 客户审核页面：独立布局，无 Admin 侧边栏 -->
    <router-view v-if="isGuestPage" />

    <!-- Admin 页面：使用 Layout 组件（含侧边栏） -->
    <Layout v-else />
  </div>
</template>

<style>
/* 仅为 body 和 #app 设置基础样式，避免全局污染 */
body {
  margin: 0;
  padding: 0;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f5f7fa;
}

#app {
  width: 100%;
  height: 100vh;
}

/* 仅为管理后台布局内的元素应用 box-sizing */
#app > .layout *,
#app > .layout *::before,
#app > .layout *::after {
  box-sizing: border-box;
}
</style>
