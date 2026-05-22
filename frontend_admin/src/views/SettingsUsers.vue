<template>
  <div class="settings-users">
    <div class="page-header">
      <h1 class="page-title">用户管理</h1>
    </div>

    <div class="action-bar">
      <el-button type="primary" @click="openCreate">+ 新建用户</el-button>
    </div>

    <el-table :data="users" v-loading="loading" stripe style="width:100%">
      <el-table-column type="index" label="#" width="50" />
      <el-table-column prop="username" label="用户名" width="140" />
      <el-table-column prop="display_name" label="显示名" width="140">
        <template #default="{ row }">{{ row.display_name || '—' }}</template>
      </el-table-column>
      <el-table-column prop="role" label="角色" width="100">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">{{ roleLabel[row.role] || row.role }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="is_active" label="状态" width="80" align="center">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="200" align="center">
        <template #default="{ row }">
          <el-button type="primary" link @click="editUser(row)">编辑</el-button>
          <el-button link @click="editAccess(row)">权限</el-button>
          <el-button type="danger" link @click="deleteUser(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 用户编辑弹窗 -->
    <el-dialog v-model="showUserDialog" :title="isEdit ? '编辑用户' : '新建用户'" width="450px" destroy-on-close>
      <el-form :model="userForm" label-width="90px">
        <el-form-item label="用户名"><el-input v-model="userForm.username" :disabled="isEdit" maxlength="64" /></el-form-item>
        <el-form-item label="显示名"><el-input v-model="userForm.display_name" placeholder="选填" maxlength="64" /></el-form-item>
        <el-form-item label="密码">
          <el-input v-model="userForm.password" type="password" placeholder="暂未启用认证" />
          <div style="font-size:11px;color:#909399;margin-top:2px;">密码功能暂未启用，仅存储</div>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userForm.role" style="width:100%">
            <el-option label="员工" value="staff" /><el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUserDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitUser">保存</el-button>
      </template>
    </el-dialog>

    <!-- 权限弹窗 -->
    <el-dialog v-model="showAccessDialog" title="项目权限设置" width="600px" destroy-on-close>
      <p style="font-size:13px;color:#606266;margin-bottom:12px;">
        为用户 <b>{{ accessUser?.username }}</b> 设置可见项目。空 = 可看所有项目。
      </p>
      <div style="margin-bottom:8px;">
        <span style="font-size:12px;color:#909399;">按客户筛选：</span>
        <el-select v-model="accessClientFilter" size="small" clearable placeholder="全部客户" style="width:200px">
          <el-option v-for="c in accessClients" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </div>
      <el-checkbox-group v-model="accessProjectIds">
        <div v-for="p in filteredAccessProjects" :key="p.id" style="padding:4px 0;">
          <el-checkbox :value="p.id">{{ p.name }} ({{ p.display_id }})</el-checkbox>
        </div>
      </el-checkbox-group>
      <el-empty v-if="filteredAccessProjects.length === 0" description="无项目" :image-size="40" />
      <template #footer>
        <el-button @click="showAccessDialog = false">取消</el-button>
        <el-button @click="accessProjectIds = []">清空（可看全部）</el-button>
        <el-button type="primary" :loading="savingAccess" @click="submitAccess">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'

const roleLabel: Record<string, string> = { staff: '员工', admin: '管理员', client: '客户' }

function fmtDate(iso: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

const users = ref<any[]>([])
const loading = ref(false)
const showUserDialog = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)
const saving = ref(false)
const userForm = reactive({ username: '', display_name: '', password: '', role: 'staff' })

async function fetchUsers() {
  loading.value = true
  try {
    const d = await request.get('/api/v1/settings/users')
    users.value = d.items
  } catch {} finally { loading.value = false }
}

function openCreate() {
  isEdit.value = false; editId.value = null
  Object.assign(userForm, { username: '', display_name: '', password: '', role: 'staff' })
  showUserDialog.value = true
}

function editUser(row: any) {
  isEdit.value = true; editId.value = row.id
  Object.assign(userForm, { username: row.username, display_name: row.display_name || '', password: '', role: row.role })
  showUserDialog.value = true
}

async function submitUser() {
  if (!userForm.username.trim()) { ElMessage.warning('请输入用户名'); return }
  saving.value = true
  try {
    if (isEdit.value) {
      const body: any = { display_name: userForm.display_name || null, role: userForm.role }
      if (userForm.password) body.password = userForm.password
      await request.patch(`/api/v1/settings/users/${editId.value}`, body)
      ElMessage.success('用户已更新')
    } else {
      await request.post('/api/v1/settings/users', {
        username: userForm.username,
        display_name: userForm.display_name || null,
        password: userForm.password || null,
        role: userForm.role
      })
      ElMessage.success('用户已创建')
    }
    showUserDialog.value = false; await fetchUsers()
  } catch (e: any) { ElMessage.error(e.message) }
  finally { saving.value = false }
}

async function deleteUser(row: any) {
  try { await ElMessageBox.confirm(`删除用户「${row.username}」？`, '确认', { type: 'warning' }) } catch { return }
  await request.delete(`/api/v1/settings/users/${row.id}`); fetchUsers()
}

// ═══ 权限 ═══
const showAccessDialog = ref(false)
const accessUser = ref<any>(null)
const accessProjectIds = ref<number[]>([])
const savingAccess = ref(false)
const accessClients = ref<any[]>([])
const allAccessProjects = ref<any[]>([])
const accessClientFilter = ref<number | null>(null)

const filteredAccessProjects = computed(() => {
  if (!accessClientFilter.value) return allAccessProjects.value
  return allAccessProjects.value.filter((p: any) => p.client_id === accessClientFilter.value)
})

async function editAccess(row: any) {
  accessUser.value = row
  const [aRes, pRes, cRes] = await Promise.all([
    request.get(`/api/v1/settings/users/${row.id}/access`),
    request.get('/api/v1/projects?limit=100&include_completed=true'),
    request.get('/api/v1/clients'),
  ])
  accessProjectIds.value = aRes.project_ids
  allAccessProjects.value = pRes.items
  accessClients.value = cRes.items
  accessClientFilter.value = null
  showAccessDialog.value = true
}

async function submitAccess() {
  savingAccess.value = true
  try {
    await request.put(`/api/v1/settings/users/${accessUser.value.id}/access`, {
      project_ids: accessProjectIds.value
    })
    ElMessage.success('权限已保存')
    showAccessDialog.value = false
  } catch { ElMessage.error('保存失败') }
  finally { savingAccess.value = false }
}

onMounted(fetchUsers)
</script>

<style scoped>
.settings-users { padding: 20px 28px; min-height: 100%; }
.page-header { margin-bottom: 16px; }
.page-title { font-size: 24px; font-weight: 700; color: #2c3e50; }
.action-bar { margin-bottom: 14px; }
</style>
