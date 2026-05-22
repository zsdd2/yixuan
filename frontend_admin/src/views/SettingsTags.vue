<template>
  <div class="settings-tags">
    <div class="page-header">
      <h1 class="page-title">标签管理</h1>
    </div>

    <div class="add-row">
      <el-input v-model="newName" placeholder="新标签名称" maxlength="64" style="width:220px" @keyup.enter="createTag" />
      <el-color-picker v-model="newColor" size="default" />
      <el-button type="primary" :disabled="!newName.trim()" @click="createTag">添加标签</el-button>
    </div>

    <el-table :data="tags" v-loading="loading" stripe style="width:100%">
      <el-table-column width="50" align="center">
        <template #default="{ row }">
          <span class="color-dot" :style="{ background: row.color }" />
        </template>
      </el-table-column>
      <el-table-column prop="name" label="标签名称" min-width="200" />
      <el-table-column prop="color" label="颜色" width="120">
        <template #default="{ row }">
          <span style="font-size:12px;color:#909399;">{{ row.color }}</span>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="center">
        <template #default="{ row }">
          <el-button type="primary" link @click="startEdit(row)">编辑</el-button>
          <el-button type="danger" link @click="deleteTag(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="showEdit" title="编辑标签" width="400px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="名称"><el-input v-model="editName" maxlength="64" /></el-form-item>
        <el-form-item label="颜色"><el-color-picker v-model="editColor" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEdit = false">取消</el-button>
        <el-button type="primary" @click="submitEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'

const tags = ref<any[]>([])
const loading = ref(false)
const newName = ref('')
const newColor = ref('#409eff')

const showEdit = ref(false)
const editId = ref<number | null>(null)
const editName = ref('')
const editColor = ref('#409eff')

function fmtDate(iso: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

async function fetchTags() {
  loading.value = true
  try {
    const d = await request.get('/api/v1/settings/tags')
    tags.value = d.items
  } catch {} finally { loading.value = false }
}

async function createTag() {
  const name = newName.value.trim()
  if (!name) return
  try {
    await request.post('/api/v1/settings/tags', {
      name,
      color: newColor.value
    })
    ElMessage.success('标签已添加')
    newName.value = ''; newColor.value = '#409eff'
    await fetchTags()
  } catch (e: any) { ElMessage.error(e.message) }
}

function startEdit(row: any) {
  editId.value = row.id; editName.value = row.name; editColor.value = row.color
  showEdit.value = true
}

async function submitEdit() {
  try {
    await request.patch(`/api/v1/settings/tags/${editId.value}`, {
      name: editName.value.trim(),
      color: editColor.value
    })
    ElMessage.success('标签已更新')
    showEdit.value = false
    await fetchTags()
  } catch (e: any) { ElMessage.error(e.message) }
}

async function deleteTag(row: any) {
  try { await ElMessageBox.confirm(`删除标签「${row.name}」？`, '确认', { type: 'warning' }) } catch { return }
  await request.delete(`/api/v1/settings/tags/${row.id}`)
  await fetchTags()
}

onMounted(fetchTags)
</script>

<style scoped>
.settings-tags { padding: 20px 28px; min-height: 100%; }
.page-header { margin-bottom: 16px; }
.page-title { font-size: 24px; font-weight: 700; color: #2c3e50; }
.add-row { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.color-dot { display: inline-block; width: 14px; height: 14px; border-radius: 50%; }
</style>
