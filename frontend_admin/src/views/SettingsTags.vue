<template>
  <div class="settings-tags">
    <div class="page-header">
      <div>
        <h1 class="page-title">标签管理</h1>
        <p class="page-subtitle">通用标签用于全局筛选；作品标签独立分类，用于最终作品检索。</p>
      </div>
    </div>

    <section class="tag-section">
      <el-tabs v-model="activeType" @tab-change="fetchTags">
        <el-tab-pane label="通用标签" name="general" />
        <el-tab-pane label="作品标签" name="portfolio" />
      </el-tabs>

      <div class="section-head">
        <div>
          <h2>{{ activeType === 'portfolio' ? '作品标签' : '通用标签' }}</h2>
          <p v-if="activeType === 'portfolio'">按分类维护，如场景：海边、庭院；元素：水果、茶几、书本。</p>
          <p v-else>系统统一维护，跨项目可用。</p>
        </div>
      </div>

      <div class="add-row" :class="{ portfolio: activeType === 'portfolio' }">
        <el-select
          v-if="activeType === 'portfolio'"
          v-model="newCategory"
          filterable
          allow-create
          default-first-option
          placeholder="分类"
          style="width: 160px"
        >
          <el-option v-for="category in tagCategories" :key="category" :label="category" :value="category" />
        </el-select>
        <el-input v-model="newName" placeholder="标签名称" maxlength="64" clearable @keyup.enter="createTag" />
        <el-color-picker v-model="newColor" />
        <el-button type="primary" :disabled="!newName.trim()" @click="createTag">添加标签</el-button>
      </div>

      <el-table :data="tags" v-loading="loading" stripe style="width:100%">
        <el-table-column width="50" align="center">
          <template #default="{ row }">
            <span class="color-dot" :style="{ background: row.color }" />
          </template>
        </el-table-column>
        <el-table-column v-if="activeType === 'portfolio'" prop="category" label="分类" width="150">
          <template #default="{ row }">{{ row.category || '未分类' }}</template>
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
          <p>统计项目内同名标签使用情况，可将高频标签转为通用标签。</p>
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

    <el-dialog v-model="showEdit" title="编辑标签" width="420px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item v-if="activeType === 'portfolio'" label="分类">
          <el-select v-model="editCategory" filterable allow-create default-first-option style="width: 100%">
            <el-option v-for="category in tagCategories" :key="category" :label="category" :value="category" />
          </el-select>
        </el-form-item>
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
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'

interface SystemTagItem {
  id: number
  name: string
  tag_type: string
  category: string | null
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

const activeType = ref<'general' | 'portfolio'>('general')
const tags = ref<SystemTagItem[]>([])
const usageItems = ref<ProjectTagUsageItem[]>([])
const loading = ref(false)
const usageLoading = ref(false)
const promotingName = ref('')
const newName = ref('')
const newCategory = ref('场景')
const newColor = ref('#409eff')

const showEdit = ref(false)
const editId = ref<number | null>(null)
const editName = ref('')
const editCategory = ref('')
const editColor = ref('#409eff')

const tagCategories = computed(() => {
  const categories = tags.value.map(tag => tag.category).filter(Boolean) as string[]
  return Array.from(new Set(['场景', '元素', ...categories]))
})

function fmtDate(iso: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

async function fetchTags() {
  loading.value = true
  try {
    const d = await request.get('/api/v1/settings/tags', { tag_type: activeType.value })
    tags.value = d.items || []
  } catch (e: any) {
    ElMessage.error(e.message || '获取标签失败')
  } finally {
    loading.value = false
  }
}

async function fetchUsage() {
  usageLoading.value = true
  try {
    const d = await request.get('/api/v1/projects/tags/usage/project-local')
    usageItems.value = d.items || []
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
      tag_type: activeType.value,
      category: activeType.value === 'portfolio' ? (newCategory.value || null) : null,
      color: newColor.value,
      sort_order: tags.value.length,
    })
    ElMessage.success('标签已添加')
    newName.value = ''
    newColor.value = '#409eff'
    await fetchTags()
  } catch (e: any) {
    ElMessage.error(e.message || '添加标签失败')
  }
}

function startEdit(row: SystemTagItem) {
  editId.value = row.id
  editName.value = row.name
  editCategory.value = row.category || '场景'
  editColor.value = row.color
  showEdit.value = true
}

async function submitEdit() {
  try {
    await request.patch(`/api/v1/settings/tags/${editId.value}`, {
      name: editName.value.trim(),
      tag_type: activeType.value,
      category: activeType.value === 'portfolio' ? (editCategory.value || null) : null,
      color: editColor.value,
    })
    ElMessage.success('标签已更新')
    showEdit.value = false
    await fetchTags()
  } catch (e: any) {
    ElMessage.error(e.message || '更新标签失败')
  }
}

async function deleteTag(row: SystemTagItem) {
  try {
    await ElMessageBox.confirm(`删除标签「${row.name}」？`, '确认', { type: 'warning' })
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
.add-row { display: grid; grid-template-columns: minmax(0, 240px) auto auto; align-items: center; gap: 10px; margin-bottom: 16px; }
.add-row.portfolio { grid-template-columns: 160px minmax(0, 240px) auto auto; }
.color-dot { display: inline-block; width: 14px; height: 14px; border-radius: 50%; border: 1px solid rgba(0,0,0,.08); }
.muted { font-size: 12px; color: #909399; }
</style>
