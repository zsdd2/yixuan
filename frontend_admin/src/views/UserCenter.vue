<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/userStore'

const userStore = useUserStore()

const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: '',
})

const loading = ref(false)

const roleLabel = computed(() => {
  const roleMap: Record<string, string> = {
    super_admin: '超级管理员',
    admin: '管理员',
    staff: '普通员工',
    client: '客户',
  }
  return roleMap[userStore.userInfo?.role || ''] || '未知'
})

const roleType = computed(() => {
  const typeMap: Record<string, string> = {
    super_admin: 'danger',
    admin: 'warning',
    staff: 'success',
    client: 'info',
  }
  return typeMap[userStore.userInfo?.role || ''] || ''
})

const handleChangePassword = async () => {
  if (!passwordForm.value.oldPassword) {
    ElMessage.error('请输入旧密码')
    return
  }

  if (!passwordForm.value.newPassword) {
    ElMessage.error('请输入新密码')
    return
  }

  if (passwordForm.value.newPassword.length < 6) {
    ElMessage.error('新密码至少 6 位')
    return
  }

  if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
    ElMessage.error('两次输入的新密码不一致')
    return
  }

  loading.value = true
  try {
    await userStore.updatePassword(passwordForm.value.oldPassword, passwordForm.value.newPassword)
    ElMessage.success('密码修改成功')
    passwordForm.value.oldPassword = ''
    passwordForm.value.newPassword = ''
    passwordForm.value.confirmPassword = ''
  } catch (error: any) {
    ElMessage.error(error.message || '密码修改失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="user-center-container">
    <div class="page-header">
      <h1 class="page-title">个人中心</h1>
      <p class="page-subtitle">管理您的个人信息和账号安全</p>
    </div>

    <div class="content-wrapper">
      <!-- 个人资料卡片 -->
      <div class="info-card">
        <div class="card-header">
          <h2 class="card-title">个人资料</h2>
        </div>
        <div class="card-body">
          <div class="info-item">
            <span class="info-label">用户名</span>
            <span class="info-value">{{ userStore.userInfo?.username }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">显示名称</span>
            <span class="info-value">{{ userStore.userInfo?.display_name }}</span>
          </div>
          <div class="info-item">
            <span class="info-label">角色</span>
            <el-tag :type="roleType" size="small">{{ roleLabel }}</el-tag>
          </div>
          <div class="info-item">
            <span class="info-label">账号状态</span>
            <el-tag :type="userStore.userInfo?.is_active ? 'success' : 'danger'" size="small">
              {{ userStore.userInfo?.is_active ? '正常' : '已禁用' }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 修改密码卡片 -->
      <div class="password-card">
        <div class="card-header">
          <h2 class="card-title">修改密码</h2>
        </div>
        <div class="card-body">
          <div class="form-item">
            <label class="form-label">旧密码</label>
            <input
              v-model="passwordForm.oldPassword"
              type="password"
              class="form-input"
              placeholder="请输入旧密码"
            />
          </div>

          <div class="form-item">
            <label class="form-label">新密码</label>
            <input
              v-model="passwordForm.newPassword"
              type="password"
              class="form-input"
              placeholder="请输入新密码（至少 6 位）"
            />
          </div>

          <div class="form-item">
            <label class="form-label">确认新密码</label>
            <input
              v-model="passwordForm.confirmPassword"
              type="password"
              class="form-input"
              placeholder="请再次输入新密码"
            />
          </div>

          <button
            class="submit-button"
            :disabled="loading"
            @click="handleChangePassword"
          >
            {{ loading ? '提交中...' : '修改密码' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.user-center-container {
  padding: 32px;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 32px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.content-wrapper {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
}

.info-card,
.password-card {
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.card-header {
  padding: 20px 24px;
  border-bottom: 1px solid #f0f0f0;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.card-body {
  padding: 24px;
}

.info-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 0;
  border-bottom: 1px solid #f5f5f5;
}

.info-item:last-child {
  border-bottom: none;
}

.info-label {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.info-value {
  font-size: 14px;
  color: #1a1a1a;
  font-weight: 500;
}

.form-item {
  margin-bottom: 20px;
}

.form-item:last-of-type {
  margin-bottom: 24px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.form-input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  font-size: 14px;
  color: #1a1a1a;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  outline: none;
  transition: all 0.2s;
}

.form-input::placeholder {
  color: #c0c4cc;
}

.form-input:focus {
  border-color: #409eff;
}

.submit-button {
  width: 100%;
  height: 40px;
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  background: #409eff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.submit-button:hover:not(:disabled) {
  background: #66b1ff;
}

.submit-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .content-wrapper {
    grid-template-columns: 1fr;
  }
}
</style>
