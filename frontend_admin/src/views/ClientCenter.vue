<template>
  <div class="client-center">
    <!-- 顶部搜索栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <span class="toolbar-label">客户名称</span>
        <el-input v-model="searchText" placeholder="请输入客户名称" size="default" clearable style="width:220px" @keyup.enter="fetchClients" />
        <el-button type="primary" @click="fetchClients">
          <el-icon><Search /></el-icon> 查询
        </el-button>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="action-bar">
      <el-button type="primary" @click="openCreate">+ 新建客户</el-button>
    </div>

    <!-- 表格 -->
    <el-table
      :data="clients"
      v-loading="loading"
      stripe
      border
      style="width: 100%"
      empty-text="暂无客户数据"
    >
      <el-table-column type="index" label="#" width="50" align="center" />
      <el-table-column label="头像" width="70" align="center">
        <template #default="{ row }">
          <div class="avatar-cell">
            <img v-if="row.avatar" :src="getAvatarUrl(row.avatar)" class="avatar-img" />
            <span v-else>{{ row.name.charAt(0) }}</span>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="prefix" label="客户前缀" width="110" sortable>
        <template #default="{ row }">
          <span class="prefix-tag">{{ row.prefix }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="客户姓名" min-width="120" sortable show-overflow-tooltip />
      <el-table-column prop="company" label="公司名称" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.company || '—' }}
        </template>
      </el-table-column>
      <el-table-column prop="phone" label="联系电话" width="140">
        <template #default="{ row }">
          {{ row.phone || '—' }}
        </template>
      </el-table-column>
      <el-table-column prop="project_total" label="项目合计" width="100" align="center" sortable />
      <el-table-column prop="active_projects" label="进行中" width="90" align="center">
        <template #default="{ row }">
          <span :class="{ 'text-blue': row.active_projects > 0 }">{{ row.active_projects }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="completed_projects" label="已完成" width="90" align="center">
        <template #default="{ row }">
          <span :class="{ 'text-green': row.completed_projects > 0 }">{{ row.completed_projects }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="total_amount" label="消费金额" width="110" align="right" sortable>
        <template #default="{ row }">
          ¥{{ row.total_amount.toFixed(0) }}
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170" sortable>
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="100" fixed="right" align="center">
        <template #default="{ row }">
          <el-dropdown trigger="click" @command="(cmd: string) => onCommand(cmd, row)">
            <el-button type="primary" link>操作</el-button>
            <template #dropdown>
              <el-dropdown-menu class="ctx-menu">
                <el-dropdown-item command="edit"><span class="mi">✏️ 编辑</span></el-dropdown-item>
                <el-dropdown-item command="delete" divided><span class="mi mi-danger">🗑️ 删除</span></el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建/编辑弹窗 -->
    <el-dialog v-model="showForm" :title="isEdit ? '编辑客户' : '新建客户'" width="500px" destroy-on-close>
      <el-form :model="form" :rules="formRules" ref="formRef" label-width="100px">
        <el-form-item label="客户头像">
          <div class="avatar-picker">
            <div v-if="form.avatar" class="avatar-preview-wrap">
              <img :src="getAvatarUrl(form.avatar)" class="avatar-preview-img" />
              <el-button size="small" text type="danger" @click="form.avatar = ''">移除</el-button>
            </div>
            <el-button size="small" @click="showImagePicker = true">选择图片</el-button>
          </div>
        </el-form-item>
        <el-form-item label="客户前缀" prop="prefix">
          <el-input v-model="form.prefix" :disabled="isEdit" placeholder="如: XD（仅英文）" maxlength="10" />
        </el-form-item>
        <el-form-item label="客户姓名" prop="name">
          <el-input v-model="form.name" placeholder="客户姓名" maxlength="64" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="form.phone" placeholder="选填" maxlength="32" />
        </el-form-item>
        <el-form-item label="公司名称">
          <el-input v-model="form.company" placeholder="选填" maxlength="128" />
        </el-form-item>
        <el-form-item label="收货地址">
          <el-input v-model="form.address" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
        <el-form-item label="营业执照号">
          <el-input v-model="form.license_no" placeholder="选填" maxlength="64" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showForm = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">{{ isEdit ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>

    <!-- 图片选择器 -->
    <ImagePicker v-model:visible="showImagePicker" category="avatar" @confirm="onAvatarPicked" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import ImagePicker from '../components/ImagePicker.vue'
import request from '../api/request'

interface ClientItem {
  id: number; name: string; prefix: string; phone: string | null
  company: string | null; avatar: string | null
  project_total: number; active_projects: number; completed_projects: number
  total_amount: number; created_at: string
}

const clients = ref<ClientItem[]>([])
const loading = ref(false)
const searchText = ref('')
const showForm = ref(false)
const isEdit = ref(false)
const saving = ref(false)
const editId = ref<number | null>(null)
const formRef = ref<FormInstance>()
const form = reactive({
  name: '', prefix: '', phone: '', company: '', address: '', license_no: '', avatar: '',
})

const showImagePicker = ref(false)

function getAvatarUrl(path: string): string {
  return `/storage/${path}`
}

function onAvatarPicked(image: { url: string; id?: number; source: 'system' | 'project' }) {
  form.avatar = image.url
}

const formRules: FormRules = {
  prefix: [
    { required: true, message: '请输入客户前缀', trigger: 'blur' },
    { pattern: /^[A-Za-z]+$/, message: '仅允许英文字母', trigger: 'blur' },
  ],
  name: [{ required: true, message: '请输入客户姓名', trigger: 'blur' }],
}

function formatDate(iso: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function fetchClients() {
  loading.value = true
  try {
    const params = searchText.value ? `?search=${encodeURIComponent(searchText.value)}` : ''
    const data = await request.get(`/api/v1/clients${params}`)
    clients.value = data.items
  } catch { ElMessage.error('获取客户列表失败') }
  finally { loading.value = false }
}

function openCreate() {
  isEdit.value = false; editId.value = null
  Object.assign(form, { name: '', prefix: '', phone: '', company: '', address: '', license_no: '', avatar: '' })
  showForm.value = true
}

function onCommand(cmd: string, c: ClientItem) {
  if (cmd === 'edit') {
    isEdit.value = true; editId.value = c.id
    Object.assign(form, { name: c.name, prefix: c.prefix, phone: c.phone || '', company: c.company || '', address: '', license_no: '', avatar: c.avatar || '' })
    request.get(`/api/v1/clients/${c.id}`).then(d => {
      form.address = d.address || ''; form.license_no = d.license_no || ''; form.avatar = d.avatar || ''
    })
    showForm.value = true
  } else if (cmd === 'delete') {
    confirmDelete(c)
  }
}

async function submitForm() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  saving.value = true
  try {
    if (isEdit.value) {
      await request.patch(`/api/v1/clients/${editId.value}`, {
        name: form.name,
        phone: form.phone || null,
        company: form.company || null,
        address: form.address || null,
        license_no: form.license_no || null,
        avatar: form.avatar || null
      })
      ElMessage.success('客户已更新')
    } else {
      await request.post('/api/v1/clients', {
        name: form.name,
        prefix: form.prefix.toUpperCase(),
        phone: form.phone || null,
        company: form.company || null,
        address: form.address || null,
        license_no: form.license_no || null,
        avatar: form.avatar || null
      })
      ElMessage.success('客户已创建')
    }
    showForm.value = false
    await fetchClients()
  } catch (e: any) { ElMessage.error(e.message) }
  finally { saving.value = false }
}

async function confirmDelete(c: ClientItem) {
  try { await ElMessageBox.confirm(`确定删除客户「${c.name}」？`, '删除确认', { type: 'warning' }) } catch { return }
  try {
    await request.delete(`/api/v1/clients/${c.id}`)
    ElMessage.success('客户已删除')
    await fetchClients()
  } catch (e: any) { ElMessage.error(e.message) }
}

onMounted(fetchClients)
</script>

<style scoped>
.client-center {
  padding: 20px 28px;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: white;
  padding: 14px 16px;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.toolbar-label {
  font-size: 14px;
  color: #606266;
  white-space: nowrap;
}

.action-bar {
  display: flex;
  gap: 10px;
}

.avatar-cell {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;
  font-weight: 700;
  margin: 0 auto;
  overflow: hidden;
}

.avatar-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-picker { display: flex; align-items: center; gap: 10px; }
.avatar-preview-wrap { display: flex; align-items: center; gap: 8px; }
.avatar-preview-img { width: 48px; height: 48px; border-radius: 50%; object-fit: cover; }

.prefix-tag {
  display: inline-block;
  background: #ecf5ff;
  color: #409eff;
  font-size: 12px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 4px;
}

.text-blue { color: #409eff; font-weight: 600; }
.text-green { color: #67c23a; font-weight: 600; }

.ctx-menu { min-width: 140px; padding: 4px 0; }
.mi { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.mi-danger { color: #f56c6c; }
</style>
