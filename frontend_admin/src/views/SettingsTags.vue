<template>
  <div class="settings-tags">
    <div class="page-header">
      <div>
        <h1 class="page-title">标签管理</h1>
        <p class="page-subtitle">通用标签用于作品中心等全局筛选；项目临时标签只在项目内使用。</p>
      </div>
    </div>

    <section class="tag-section">
      <div class="section-head">
        <div>
          <h2>通用标签</h2>
          <p>系统统一维护，跨项目可用。</p>
        </div>
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
            <span class="muted">{{ row.color }}</span>
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
    </section>

    <section class="tag-section">
      <div class="section-head">
        <div>
          <h2>项目临时标签排行</h2>
          <p>统计项目内同名标签的使用情况，可将高频标签转为通用标签。</p>
        </div>
        <el-button size="small" @click="fetchUsage">刷新</el-button>
      </div>

      <el-table :data="usageItems" v-loading="usageLoading" stripe style="width:100%">
        <el-table-column width="50" align="center">
          <template #default="{ row }">
            <span class="color-dot" :style="{ background: row.color }" />
          </template>
        </el-table-column>
        <el-table-column prop="name" label="项目标签名称" min-width="200" />
        <el-table-column prop="project_count" label="出现项目数" width="120" align="center" />
        <el-table-column prop="photo_count" label="关联图片数" width="120" align="center" />
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button type="primary" link :loading="promotingName === row.name" @click="promoteTag(row)">转为通用标签</el-button>
          </template>
        </el-table-column>
      </el-table>
    </section>

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

interface SystemTagItem {
  id: number
  name: string
  color: string
  sort_order: number
  created_at: string
}

interface ProjectTagUsageItem {
  name: string
  color: string
  project_count: number
  photo_count: number
}

const tags = ref<SystemTagItem[]>([])
const usageItems = ref<ProjectTagUsageItem[]>([])
const loading = ref(false)
const usageLoading = ref(false)
const promotingName = ref('')
const newName = ref('')
const newColor = ref('#409eff')

const showEdit = ref(false)
const editId = ref<number | null>(null)
const editName = ref('')
const editColor = ref('#409eff')

function fmtDate(iso: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

async function fetchTags() {
  loading.value = true
  try {
    const d = await request.get('/api/v1/settings/tags')
    tags.value = d.items
  } catch (e: any) {
    ElMessage.error(e.message || '获取通用标签失败')
  } finally {
    loading.value = false
  }
}

async function fetchUsage() {
  usageLoading.value = true
  try {
    const d = await request.get('/api/v1/projects/tags/usage/project-local')
    usageItems.value = d.items
  } catch (e: any) {
    ElMessage.error(e.message || '获取项目标签排行失败')
  } finally {
    usageLoading.value = false
  }
}

async function createTag() {
  const name = newName.value.trim()
  if (!name) return
  try {
    await request.post('/api/v1/settings/tags', {
      name,
      color: newColor.value,
    })
    ElMessage.success('标签已添加')
    newName.value = ''
    newColor.value = '#409eff'
    await fetchTags()
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

function startEdit(row: SystemTagItem) {
  editId.value = row.id
  editName.value = row.name
  editColor.value = row.color
  showEdit.value = true
}

async function submitEdit() {
  try {
    await request.patch(`/api/v1/settings/tags/${editId.value}`, {
      name: editName.value.trim(),
      color: editColor.value,
    })
    ElMessage.success('标签已更新')
    showEdit.value = false
    await fetchTags()
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function deleteTag(row: SystemTagItem) {
  try {
    await ElMessageBox.confirm(`删除通用标签「${row.name}」？`, '确认', { type: 'warning' })
  } catch {
    return
  }
  await request.delete(`/api/v1/settings/tags/${row.id}`)
  await fetchTags()
}

async function promoteTag(row: ProjectTagUsageItem) {
  try {
    await ElMessageBox.confirm(`将项目临时标签「${row.name}」转为通用标签？`, '确认', { type: 'warning' })
  } catch {
    return
  }
  promotingName.value = row.name
  try {
    await request.post('/api/v1/projects/tags/promote', {
      name: row.name,
      color: row.color,
    })
    ElMessage.success('已转为通用标签')
    await Promise.all([fetchTags(), fetchUsage()])
  } catch (e: any) {
    ElMessage.error(e.message || '转换失败')
  } finally {
    promotingName.value = ''
  }
}

onMounted(() => {
  Promise.all([fetchTags(), fetchUsage()])
})
</script>

<style scoped>
.settings-tags { padding: 20px 28px; min-height: 100%; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.page-title { font-size: 24px; font-weight: 700; color: #2c3e50; margin: 0; }
.page-subtitle { margin: 6px 0 0; font-size: 13px; color: #909399; }
.tag-section { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.section-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
.section-head h2 { margin: 0; font-size: 16px; color: #1f2937; }
.section-head p { margin: 4px 0 0; font-size: 12px; color: #909399; }
.add-row { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.color-dot { display: inline-block; width: 14px; height: 14px; border-radius: 50%; border: 1px solid rgba(0,0,0,.08); }
.muted { font-size: 12px; color: #909399; }
</style>
