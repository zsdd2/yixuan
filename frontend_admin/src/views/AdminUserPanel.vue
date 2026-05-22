<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '@/api/request'
import type { UserRole } from '@/stores/userStore'

interface User {
  id: number
  username: string
  display_name: string
  role: UserRole
  is_active: boolean
  last_login_at: string | null
  created_at: string
}

interface UserListResponse {
  total: number
  items: User[]
  skip: number
  limit: number
}

const users = ref<User[]>([])
const total = ref(0)
const loading = ref(false)
const searchKeyword = ref('')
const roleFilter = ref('')

const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const dialogTitle = ref('创建用户')

const userForm = ref({
  id: 0,
  username: '',
  display_name: '',
  password: '',
  role: 'staff' as UserRole,
  is_active: true,
})

const roleOptions = [
  { label: '超级管理员', value: 'super_admin' },
  { label: '管理员', value: 'admin' },
  { label: '普通员工', value: 'staff' },
  { label: '客户', value: 'client' },
]

const roleTypeMap: Record<string, string> = {
  super_admin: 'danger',
  admin: 'warning',
  staff: 'success',
  client: 'info',
}

const roleLabelMap: Record<string, string> = {
  super_admin: '超级管理员',
  admin: '管理员',
  staff: '普通员工',
  client: '客户',
}

const fetchUsers = async () => {
  loading.value = true
  try {
    const params: any = {
      skip: 0,
      limit: 100,
    }
    if (searchKeyword.value) {
      params.search = searchKeyword.value
    }
    if (roleFilter.value) {
      params.role_filter = roleFilter.value
    }

    const data = await request.get<UserListResponse>('/api/v1/users', params)
    users.value = data.items
    total.value = data.total
  } catch (error: any) {
    ElMessage.error(error.message || '获取用户列表失败')
  } finally {
    loading.value = false
  }
}

const handleCreate = () => {
  dialogMode.value = 'create'
  dialogTitle.value = '创建用户'
  userForm.value = {
    id: 0,
    username: '',
    display_name: '',
    password: '',
    role: 'staff',
    is_active: true,
  }
  dialogVisible.value = true
}

const handleEdit = (user: User) => {
  dialogMode.value = 'edit'
  dialogTitle.value = '编辑用户'
  userForm.value = {
    id: user.id,
    username: user.username,
    display_name: user.display_name,
    password: '',
    role: user.role,
    is_active: user.is_active,
  }
  dialogVisible.value = true
}

const handleDelete = async (user: User) => {
  try {
    await ElMessageBox.confirm(`确定要删除用户「${user.display_name}」吗？`, '确认删除', {
      type: 'warning',
    })

    await request.delete(`/api/v1/users/${user.id}`)
    ElMessage.success('用户删除成功')
    fetchUsers()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.message || '删除失败')
    }
  }
}

const handleSubmit = async () => {
  if (!userForm.value.username || !userForm.value.display_name) {
    ElMessage.error('请填写完整信息')
    return
  }

  if (dialogMode.value === 'create' && !userForm.value.password) {
    ElMessage.error('请输入密码')
    return
  }

  if (dialogMode.value === 'create' && userForm.value.password.length < 6) {
    ElMessage.error('密码至少 6 位')
    return
  }

  try {
    if (dialogMode.value === 'create') {
      await request.post('/api/v1/users', {
        username: userForm.value.username,
        display_name: userForm.value.display_name,
        password: userForm.value.password,
        role: userForm.value.role,
        is_active: userForm.value.is_active,
      })
      ElMessage.success('用户创建成功')
    } else {
      await request.patch(`/api/v1/users/${userForm.value.id}`, {
        display_name: userForm.value.display_name,
        role: userForm.value.role,
        is_active: userForm.value.is_active,
      })
      ElMessage.success('用户更新成功')
    }

    dialogVisible.value = false
    fetchUsers()
  } catch (error: any) {
    ElMessage.error(error.message || '操作失败')
  }
}

const formatDate = (dateStr: string | null) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

onMounted(() => {
  fetchUsers()
})
</script>

<template>
  <div class="admin-user-panel">
    <div class="page-header">
      <h1 class="page-title">用户管理</h1>
      <button class="create-button" @click="handleCreate">创建用户</button>
    </div>

    <div class="filter-bar">
      <input
        v-model="searchKeyword"
        type="text"
        class="search-input"
        placeholder="搜索用户名或显示名称"
        @keyup.enter="fetchUsers"
      />
      <select v-model="roleFilter" class="role-select" @change="fetchUsers">
        <option value="">全部角色</option>
        <option v-for="opt in roleOptions" :key="opt.value" :value="opt.value">
          {{ opt.label }}
        </option>
      </select>
      <button class="search-button" @click="fetchUsers">搜索</button>
    </div>

    <div class="table-container">
      <el-table :data="users" v-loading="loading" style="width: 100%">
        <el-table-column prop="id" label="ID" width="80" />
        <el-table-column prop="username" label="用户名" width="150" />
        <el-table-column prop="display_name" label="显示名称" width="150" />
        <el-table-column label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="roleTypeMap[row.role]" size="small">
              {{ roleLabelMap[row.role] }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '正常' : '已禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="最后登录" width="180">
          <template #default="{ row }">
            {{ formatDate(row.last_login_at) }}
          </template>
        </el-table-column>
        <el-table-column label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <button class="action-button edit" @click="handleEdit(row)">编辑</button>
            <button class="action-button delete" @click="handleDelete(row)">删除</button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 创建/编辑用户对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="500px"
    >
      <div class="dialog-form">
        <div class="form-item">
          <label class="form-label">用户名</label>
          <input
            v-model="userForm.username"
            type="text"
            class="form-input"
            placeholder="请输入用户名"
            :disabled="dialogMode === 'edit'"
          />
        </div>

        <div class="form-item">
          <label class="form-label">显示名称</label>
          <input
            v-model="userForm.display_name"
            type="text"
            class="form-input"
            placeholder="请输入显示名称"
          />
        </div>

        <div v-if="dialogMode === 'create'" class="form-item">
          <label class="form-label">密码</label>
          <input
            v-model="userForm.password"
            type="password"
            class="form-input"
            placeholder="请输入密码（至少 6 位）"
          />
        </div>

        <div class="form-item">
          <label class="form-label">角色</label>
          <select v-model="userForm.role" class="form-select">
            <option v-for="opt in roleOptions" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </option>
          </select>
        </div>

        <div class="form-item">
          <label class="form-label">
            <input v-model="userForm.is_active" type="checkbox" class="form-checkbox" />
            启用账号
          </label>
        </div>
      </div>

      <template #footer>
        <button class="dialog-button cancel" @click="dialogVisible = false">取消</button>
        <button class="dialog-button confirm" @click="handleSubmit">确定</button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.admin-user-panel {
  padding: 32px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}

.page-title {
  font-size: 28px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.create-button {
  height: 40px;
  padding: 0 20px;
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  background: #409eff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.create-button:hover {
  background: #66b1ff;
}

.filter-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.search-input {
  flex: 1;
  height: 40px;
  padding: 0 12px;
  font-size: 14px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  outline: none;
}

.search-input:focus {
  border-color: #409eff;
}

.role-select {
  width: 150px;
  height: 40px;
  padding: 0 12px;
  font-size: 14px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  outline: none;
}

.search-button {
  height: 40px;
  padding: 0 20px;
  font-size: 14px;
  font-weight: 500;
  color: #fff;
  background: #409eff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.search-button:hover {
  background: #66b1ff;
}

.table-container {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.action-button {
  height: 28px;
  padding: 0 12px;
  font-size: 13px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  margin-right: 8px;
  transition: all 0.2s;
}

.action-button.edit {
  color: #409eff;
  background: #ecf5ff;
}

.action-button.edit:hover {
  background: #d9ecff;
}

.action-button.delete {
  color: #f56c6c;
  background: #fef0f0;
}

.action-button.delete:hover {
  background: #fde2e2;
}

.dialog-form {
  padding: 20px 0;
}

.form-item {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 8px;
}

.form-input,
.form-select {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  font-size: 14px;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  outline: none;
}

.form-input:focus,
.form-select:focus {
  border-color: #409eff;
}

.form-checkbox {
  margin-right: 8px;
}

.dialog-button {
  height: 36px;
  padding: 0 20px;
  font-size: 14px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  margin-left: 12px;
}

.dialog-button.cancel {
  color: #606266;
  background: #f5f7fa;
}

.dialog-button.cancel:hover {
  background: #e9ecef;
}

.dialog-button.confirm {
  color: #fff;
  background: #409eff;
}

.dialog-button.confirm:hover {
  background: #66b1ff;
}
</style>
