<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/userStore'

const router = useRouter()
const userStore = useUserStore()

const form = ref({
  username: '',
  password: '',
})

const loading = ref(false)

const handleLogin = async () => {
  if (!form.value.username || !form.value.password) {
    ElMessage.error('请输入用户名和密码')
    return
  }

  loading.value = true
  try {
    await userStore.login(form.value.username, form.value.password)
    ElMessage.success(`欢迎回来，${userStore.userInfo?.display_name}`)
    router.push('/')
  } catch (error: any) {
    ElMessage.error(error.message || '登录失败')
  } finally {
    loading.value = false
  }
}

const handleKeyPress = (e: KeyboardEvent) => {
  if (e.key === 'Enter') {
    handleLogin()
  }
}
</script>

<template>
  <div class="login-container">
    <!-- 左侧：摄影作品背景 -->
    <div class="login-left">
      <div class="background-overlay"></div>
      <div class="brand-info">
        <h1 class="brand-title">ArtSelect</h1>
        <p class="brand-subtitle">商业摄影选片系统 V5.0</p>
      </div>
    </div>

    <!-- 右侧：登录表单 -->
    <div class="login-right">
      <div class="login-form-wrapper">
        <div class="form-header">
          <h2 class="form-title">登录</h2>
          <p class="form-subtitle">欢迎回来，请登录您的账号</p>
        </div>

        <div class="form-body">
          <div class="form-item">
            <label class="form-label">用户名</label>
            <input
              v-model="form.username"
              type="text"
              class="form-input"
              placeholder="请输入用户名"
              @keypress="handleKeyPress"
            />
          </div>

          <div class="form-item">
            <label class="form-label">密码</label>
            <input
              v-model="form.password"
              type="password"
              class="form-input"
              placeholder="请输入密码"
              @keypress="handleKeyPress"
            />
          </div>

          <button
            class="login-button"
            :disabled="loading"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登录' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  width: 100%;
  height: 100vh;
  background: #1a1a1a;
}

/* 左侧：摄影作品背景 */
.login-left {
  position: relative;
  flex: 0 0 60%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-image: url('https://images.unsplash.com/photo-1542038784456-1ea8e935640e?w=1920&q=80');
  background-size: cover;
  background-position: center;
  overflow: hidden;
}

.background-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.8) 0%, rgba(118, 75, 162, 0.8) 100%);
}

.brand-info {
  position: absolute;
  bottom: 60px;
  left: 60px;
  z-index: 1;
  color: #fff;
}

.brand-title {
  font-size: 48px;
  font-weight: 700;
  margin: 0 0 12px 0;
  letter-spacing: -1px;
}

.brand-subtitle {
  font-size: 18px;
  font-weight: 300;
  margin: 0;
  opacity: 0.9;
}

/* 右侧：登录表单 */
.login-right {
  flex: 0 0 40%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1a1a1a;
  padding: 40px;
}

.login-form-wrapper {
  width: 100%;
  max-width: 400px;
}

.form-header {
  margin-bottom: 40px;
}

.form-title {
  font-size: 32px;
  font-weight: 600;
  color: #fff;
  margin: 0 0 8px 0;
}

.form-subtitle {
  font-size: 14px;
  color: #888;
  margin: 0;
}

.form-body {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.form-label {
  font-size: 14px;
  font-weight: 500;
  color: #ccc;
}

.form-input {
  width: 100%;
  height: 48px;
  padding: 0 16px;
  font-size: 15px;
  color: #fff;
  background: #2a2a2a;
  border: 1px solid #3a3a3a;
  border-radius: 8px;
  outline: none;
  transition: all 0.2s;
}

.form-input::placeholder {
  color: #666;
}

.form-input:focus {
  border-color: #667eea;
  background: #2d2d2d;
}

.login-button {
  width: 100%;
  height: 48px;
  margin-top: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s;
}

.login-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
}

.login-button:active:not(:disabled) {
  transform: translateY(0);
}

.login-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .login-left {
    flex: 0 0 50%;
  }
  .login-right {
    flex: 0 0 50%;
  }
}

@media (max-width: 768px) {
  .login-left {
    display: none;
  }
  .login-right {
    flex: 1;
  }
}
</style>
