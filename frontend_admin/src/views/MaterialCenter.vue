<template>
  <div class="material-center">
    <div class="page-header">
      <div>
        <h1 class="page-title">素材中心</h1>
        <p class="page-subtitle">按分类和标签查找场景、道具、饮品等素材图</p>
      </div>
      <div class="header-actions">
        <el-button @click="showBatchSorter = true">快速分类</el-button>
        <el-button type="primary" @click="showUpload = true">上传素材</el-button>
      </div>
    </div>

    <div class="filter-bar">
      <el-select v-model="filterPrimary" placeholder="一级分类" clearable style="width: 150px" @change="onPrimaryFilterChange">
        <el-option v-for="c in materialCategories" :key="c.name" :label="c.name" :value="c.name" />
      </el-select>
      <el-select v-model="filterSecondary" placeholder="二级分类" clearable style="width: 160px" @change="fetchMaterials">
        <el-option v-for="s in filterSecondaryOptions" :key="s" :label="s" :value="s" />
      </el-select>
      <el-input v-model="filterKeyword" placeholder="标签/名称" clearable style="width: 220px" @keyup.enter="fetchMaterials" />
      <el-button @click="fetchMaterials">筛选</el-button>
    </div>

    <div v-loading="loading" class="material-grid">
      <div v-for="(item, idx) in filteredMaterials" :key="item.id" class="material-card">
        <div class="material-img-wrap" @click="openPreview(idx)">
          <img :src="storageUrl(item.thumbnail_path || item.original_path)" class="material-img" loading="lazy" />
        </div>
        <div class="material-info">
          <div class="material-name">{{ item.name }}</div>
          <div class="material-category">{{ item.category }}</div>
          <div v-if="item.tags" class="material-tags">{{ item.tags }}</div>
        </div>
      </div>
    </div>
    <el-empty v-if="!loading && filteredMaterials.length === 0" description="暂无素材" />

    <el-dialog v-model="showBatchSorter" title="素材快速分类" width="92vw" top="4vh" destroy-on-close class="sorter-dialog">
      <div class="sorter-layout">
        <section class="sorter-panel">
          <div class="sorter-panel-head">
            <div>
              <strong>来源素材</strong>
              <span>当前筛选 {{ filteredMaterials.length }} 张</span>
            </div>
            <div class="sorter-head-actions">
              <el-button size="small" @click="selectCurrentFiltered">全选当前</el-button>
              <el-button size="small" @click="clearSelected">清空</el-button>
            </div>
          </div>
          <div class="sorter-grid source-grid">
            <button
              v-for="item in filteredMaterials"
              :key="item.id"
              type="button"
              class="sorter-card"
              :class="{ selected: selectedIds.has(item.id) }"
              @click="toggleSelect(item.id)"
            >
              <img :src="storageUrl(item.thumbnail_path || item.original_path)" class="sorter-thumb" loading="lazy" />
              <span class="sorter-badge">{{ item.category || '未分类' }}</span>
              <span class="sorter-name">{{ item.name }}</span>
            </button>
          </div>
        </section>

        <aside class="sorter-actions">
          <div class="sorter-step">
            <span class="step-label">已选素材</span>
            <strong>{{ selectedIds.size }} 张</strong>
          </div>
          <el-select v-model="batchPrimary" placeholder="一级分类" @change="batchSecondary = ''">
            <el-option v-for="c in materialCategories" :key="c.name" :label="c.name" :value="c.name" />
          </el-select>
          <el-select v-model="batchSecondary" placeholder="二级分类">
            <el-option v-for="s in batchSecondaryOptions" :key="s" :label="s" :value="s" />
          </el-select>
          <el-input v-model="batchTags" placeholder="附加标签，多个用逗号分隔" />
          <div class="target-summary">
            <span>目标分类</span>
            <strong>{{ targetCategory || '请选择分类' }}</strong>
            <small>现有 {{ targetMaterials.length }} 张素材</small>
          </div>
          <el-button
            type="primary"
            size="large"
            :disabled="selectedIds.size === 0 || !targetCategory"
            @click="applyBatchCategory"
          >
            移入目标分类
          </el-button>
          <el-button size="large" @click="clearSelected">取消选择</el-button>
        </aside>

        <section class="sorter-panel">
          <div class="sorter-panel-head">
            <div>
              <strong>目标分类预览</strong>
              <span>{{ targetCategory || '未选择分类' }}</span>
            </div>
          </div>
          <div v-if="targetMaterials.length" class="sorter-grid target-grid">
            <div v-for="item in targetMaterials" :key="item.id" class="target-card">
              <img :src="storageUrl(item.thumbnail_path || item.original_path)" class="sorter-thumb" loading="lazy" />
              <span class="sorter-name">{{ item.name }}</span>
            </div>
          </div>
          <el-empty v-else description="选择分类后查看已有素材" />
        </section>
      </div>
    </el-dialog>

    <div v-if="previewVisible" class="preview-mask" @click.self="previewVisible = false">
      <div class="preview-shell">
        <img :src="previewUrl" class="preview-img" />
        <div class="preview-caption">
          <div>{{ filteredMaterials[previewIndex]?.name }}</div>
          <div>{{ filteredMaterials[previewIndex]?.category }}</div>
        </div>
        <button class="side-btn download" @click="downloadCurrent">⬇</button>
        <button v-if="previewIndex > 0" class="nav-btn prev" @click="previewIndex--">‹</button>
        <button v-if="previewIndex < filteredMaterials.length - 1" class="nav-btn next" @click="previewIndex++">›</button>
        <button class="close-btn" @click="previewVisible = false">✕</button>
      </div>
    </div>

    <el-dialog v-model="showUpload" title="上传素材" width="680px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="素材名称">
          <el-input v-model="uploadName" placeholder="例如：海边柠檬水" />
        </el-form-item>
        <el-form-item label="一级分类">
          <el-select v-model="uploadPrimary" placeholder="选择一级分类" style="width: 100%" @change="uploadSecondary = ''">
            <el-option v-for="c in materialCategories" :key="c.name" :label="c.name" :value="c.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="二级分类">
          <el-select v-model="uploadSecondary" placeholder="选择二级分类" style="width: 100%">
            <el-option v-for="s in uploadSecondaryOptions" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="附加标签">
          <el-input v-model="uploadTags" placeholder="多个标签用逗号分隔" />
        </el-form-item>
        <el-form-item label="图片">
          <el-upload
            ref="uploadRef"
            drag
            multiple
            :auto-upload="false"
            accept=".jpg,.jpeg,.png,.webp,.tif,.tiff"
            :on-change="onFileChange"
            :on-remove="onFileRemove"
          >
            <el-button type="primary" plain>选择图片</el-button>
            <template #tip><div class="upload-tip">可批量选择，多张会使用同一分类与标签。</div></template>
          </el-upload>
        </el-form-item>
        <el-divider content-position="left">NAS 导入</el-divider>
        <el-form-item label="NAS路径">
          <div class="nas-row">
            <el-input v-model="nasPath" placeholder="点击右侧选择 NAS 目录" readonly />
            <el-button @click="showNasPicker = true">选择</el-button>
            <el-button type="success" :loading="scanningNas" :disabled="!nasPath || !uploadPrimary || !uploadSecondary" @click="scanNasMaterials">导入</el-button>
          </div>
        </el-form-item>
      </el-form>
      <NASPathPicker v-model="showNasPicker" @select="onNasSelected" />
      <template #footer>
        <el-button @click="showUpload = false">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="uploadFiles.length === 0 || !uploadPrimary || !uploadSecondary" @click="uploadMaterial">
          上传 {{ uploadFiles.length }} 张
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'
import NASPathPicker from '../components/NASPathPicker.vue'

interface MaterialCategory { name: string; children: string[] }
interface MaterialItem {
  id: number
  category: string
  name: string
  tags: string | null
  original_path: string
  thumbnail_path: string | null
}

const defaultCategories: MaterialCategory[] = [
  { name: '场景', children: ['庄园', '海边', '泳池', '庭院'] },
  { name: '饮料', children: ['红酒杯', '柠檬水'] },
]

const materialCategories = ref<MaterialCategory[]>(defaultCategories)
const materials = ref<MaterialItem[]>([])
const loading = ref(false)
const filterPrimary = ref('')
const filterSecondary = ref('')
const filterKeyword = ref('')

const showUpload = ref(false)
const uploadName = ref('')
const uploadPrimary = ref('')
const uploadSecondary = ref('')
const uploadTags = ref('')
const uploadFiles = ref<File[]>([])
const uploading = ref(false)
const uploadRef = ref()
const nasPath = ref('')
const showNasPicker = ref(false)
const scanningNas = ref(false)
const showBatchSorter = ref(false)
const selectedIds = ref(new Set<number>())
const batchPrimary = ref('')
const batchSecondary = ref('')
const batchTags = ref('')

const previewVisible = ref(false)
const previewIndex = ref(0)
const previewUrl = computed(() => {
  const item = filteredMaterials.value[previewIndex.value]
  return item ? storageUrl(item.original_path) : ''
})

const filterSecondaryOptions = computed(() =>
  materialCategories.value.find(c => c.name === filterPrimary.value)?.children || []
)
const uploadSecondaryOptions = computed(() =>
  materialCategories.value.find(c => c.name === uploadPrimary.value)?.children || []
)
const batchSecondaryOptions = computed(() =>
  materialCategories.value.find(c => c.name === batchPrimary.value)?.children || []
)
const targetCategory = computed(() =>
  batchPrimary.value && batchSecondary.value ? `${batchPrimary.value}/${batchSecondary.value}` : ''
)
const targetMaterials = computed(() =>
  targetCategory.value ? materials.value.filter(item => item.category === targetCategory.value) : []
)

const filteredMaterials = computed(() => {
  let list = materials.value
  if (filterPrimary.value) list = list.filter(item => item.category.startsWith(`${filterPrimary.value}/`))
  if (filterSecondary.value) list = list.filter(item => item.category === `${filterPrimary.value}/${filterSecondary.value}`)
  const keyword = filterKeyword.value.trim().toLowerCase()
  if (keyword) {
    list = list.filter(item =>
      item.name.toLowerCase().includes(keyword) ||
      (item.tags || '').toLowerCase().includes(keyword) ||
      item.category.toLowerCase().includes(keyword)
    )
  }
  return list
})

onMounted(async () => {
  await loadCategories()
  await fetchMaterials()
})

function storageUrl(path: string) {
  return `/storage/${path}`
}

async function loadCategories() {
  try {
    const result = await request.get('/api/v1/system/configs/material_categories')
    if (result.code === 200 && result.data?.config_value) {
      materialCategories.value = JSON.parse(result.data.config_value)
    }
  } catch {}
}

async function fetchMaterials() {
  loading.value = true
  try {
    const data = await request.get('/api/v1/settings/images', { limit: 500 })
    materials.value = (data.items || []).filter((item: MaterialItem) => item.category.includes('/'))
  } catch (e: any) {
    ElMessage.error(e.message || '获取素材失败')
  } finally {
    loading.value = false
  }
}

function onPrimaryFilterChange() {
  filterSecondary.value = ''
  fetchMaterials()
}

function onFileChange(_file: any, files: any[]) {
  uploadFiles.value = files.map(file => file.raw).filter(Boolean)
}

function onFileRemove(_file: any, files: any[]) {
  uploadFiles.value = files.map(file => file.raw).filter(Boolean)
}

async function uploadMaterial() {
  if (uploadFiles.value.length === 0 || !uploadPrimary.value || !uploadSecondary.value) return
  uploading.value = true
  try {
    for (const file of uploadFiles.value) {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('category', `${uploadPrimary.value}/${uploadSecondary.value}`)
      fd.append('name', uploadName.value || file.name)
      fd.append('tags', uploadTags.value)
      await request.upload('/api/v1/settings/images/upload', fd)
    }
    ElMessage.success(`已上传 ${uploadFiles.value.length} 张素材`)
    showUpload.value = false
    uploadName.value = ''
    uploadTags.value = ''
    uploadFiles.value = []
    uploadRef.value?.clearFiles?.()
    await fetchMaterials()
  } catch (e: any) {
    ElMessage.error(e.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

function onNasSelected(path: string) {
  nasPath.value = path === '.' ? '' : path
}

async function scanNasMaterials() {
  if (!nasPath.value || !uploadPrimary.value || !uploadSecondary.value) return
  scanningNas.value = true
  try {
    const result = await request.post('/api/v1/settings/images/scan-nas', {
      path: nasPath.value,
      category: `${uploadPrimary.value}/${uploadSecondary.value}`,
      tags: uploadTags.value || null,
    })
    ElMessage.success(result.msg || 'NAS 导入完成')
    await fetchMaterials()
  } catch (e: any) {
    ElMessage.error(e.message || 'NAS 导入失败')
  } finally {
    scanningNas.value = false
  }
}

function toggleSelect(id: number) {
  const next = new Set(selectedIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedIds.value = next
}

function selectCurrentFiltered() {
  selectedIds.value = new Set(filteredMaterials.value.map(item => item.id))
}

function clearSelected() {
  selectedIds.value = new Set()
}

async function applyBatchCategory() {
  if (!targetCategory.value || selectedIds.value.size === 0) return
  const category = targetCategory.value
  const ids = Array.from(selectedIds.value)
  try {
    await request.patch('/api/v1/settings/images/bulk-update', {
      image_ids: ids,
      category,
      tags: batchTags.value || null,
    })
    for (const id of ids) {
      const item = materials.value.find(m => m.id === id)
      if (item) {
        item.category = category
        item.tags = batchTags.value || item.tags
      }
    }
    selectedIds.value = new Set()
    ElMessage.success(`已批量分类 ${ids.length} 张素材`)
  } catch (e: any) {
    ElMessage.error(e.message || '批量分类失败')
  }
}

function openPreview(idx: number) {
  previewIndex.value = idx
  previewVisible.value = true
}

function downloadCurrent() {
  const item = filteredMaterials.value[previewIndex.value]
  if (!item) return
  const a = document.createElement('a')
  a.href = storageUrl(item.original_path)
  a.download = item.name
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}
</script>

<style scoped>
.material-center { padding: 24px 32px; min-height: 100%; background: #f9fafb; }
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 18px; }
.header-actions { display: flex; gap: 8px; }
.page-title { margin: 0; font-size: 24px; font-weight: 700; color: #1f2937; }
.page-subtitle { margin: 6px 0 0; color: #6b7280; font-size: 13px; }
.filter-bar { display: flex; gap: 10px; align-items: center; margin-bottom: 18px; flex-wrap: wrap; }
.material-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 14px; }
.material-card { background: #fff; border-radius: 8px; overflow: hidden; border: 1px solid #ebeef5; }
.material-img-wrap { position: relative; aspect-ratio: 4 / 3; cursor: zoom-in; background: #f5f7fa; }
.material-img { width: 100%; height: 100%; object-fit: cover; display: block; }
.material-info { padding: 10px 12px; }
.material-name { font-size: 14px; font-weight: 700; color: #1f2937; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.material-category { font-size: 12px; color: #409eff; margin-top: 4px; }
.material-tags { font-size: 12px; color: #909399; margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sorter-dialog :deep(.el-dialog__body) { padding-top: 8px; }
.sorter-layout { display: grid; grid-template-columns: minmax(360px, 1fr) 220px minmax(320px, 420px); gap: 14px; height: 72vh; min-height: 560px; }
.sorter-panel { min-height: 0; background: #fff; border: 1px solid #ebeef5; border-radius: 8px; display: flex; flex-direction: column; overflow: hidden; }
.sorter-panel-head { min-height: 52px; padding: 10px 12px; border-bottom: 1px solid #ebeef5; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.sorter-panel-head strong { display: block; color: #1f2937; font-size: 14px; }
.sorter-panel-head span { display: block; color: #909399; font-size: 12px; margin-top: 3px; }
.sorter-head-actions { display: flex; gap: 6px; flex-shrink: 0; }
.sorter-grid { padding: 12px; display: grid; grid-template-columns: repeat(auto-fill, minmax(118px, 1fr)); gap: 10px; overflow-y: auto; align-content: start; }
.sorter-card, .target-card { position: relative; border: 1px solid #ebeef5; border-radius: 8px; background: #fff; padding: 0; overflow: hidden; text-align: left; }
.sorter-card { cursor: pointer; }
.sorter-card.selected { border-color: #409eff; box-shadow: 0 0 0 2px rgba(64,158,255,0.2); }
.sorter-card.selected::after { content: '✓'; position: absolute; top: 8px; right: 8px; width: 24px; height: 24px; border-radius: 50%; background: #409eff; color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; }
.sorter-thumb { width: 100%; aspect-ratio: 4 / 3; object-fit: cover; display: block; background: #f5f7fa; }
.sorter-badge { position: absolute; left: 6px; top: 6px; max-width: calc(100% - 40px); padding: 2px 6px; border-radius: 4px; background: rgba(31,41,55,0.72); color: #fff; font-size: 11px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sorter-name { display: block; padding: 7px 8px; color: #303133; font-size: 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sorter-actions { border: 1px solid #ebeef5; border-radius: 8px; background: #f8fafc; padding: 18px 14px; display: flex; flex-direction: column; justify-content: center; gap: 12px; }
.sorter-step { padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #fff; text-align: center; }
.sorter-step strong { display: block; color: #1f2937; font-size: 24px; margin-top: 4px; }
.step-label, .target-summary span, .target-summary small { color: #909399; font-size: 12px; }
.target-summary { padding: 12px; border-radius: 8px; background: #fff; border: 1px solid #e5e7eb; }
.target-summary strong { display: block; margin: 5px 0; color: #409eff; min-height: 18px; }
.target-grid { grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); }
.nas-row { display: flex; gap: 8px; width: 100%; }
.nas-row .el-input { flex: 1; }
.upload-tip { font-size: 12px; color: #909399; margin-top: 6px; }
.preview-mask { position: fixed; inset: 0; z-index: 9999; background: rgba(0,0,0,0.9); display: flex; align-items: center; justify-content: center; }
.preview-shell { position: relative; max-width: 88vw; max-height: 88vh; }
.preview-img { max-width: 88vw; max-height: 78vh; object-fit: contain; background: #fff; border-radius: 8px; }
.preview-caption { color: #fff; text-align: center; margin-top: 10px; font-size: 13px; }
.side-btn, .nav-btn, .close-btn { position: absolute; border: none; background: rgba(255,255,255,0.18); color: white; cursor: pointer; }
.side-btn { right: -58px; top: 0; width: 44px; height: 44px; border-radius: 8px; }
.close-btn { right: -58px; top: 54px; width: 44px; height: 44px; border-radius: 50%; }
.nav-btn { top: 50%; width: 48px; height: 64px; margin-top: -32px; border-radius: 8px; font-size: 40px; }
.nav-btn.prev { left: -64px; }
.nav-btn.next { right: -64px; }
@media (max-width: 1100px) {
  .sorter-layout { grid-template-columns: 1fr; height: auto; min-height: 0; }
  .sorter-panel { min-height: 360px; }
  .sorter-actions { justify-content: flex-start; }
}
</style>
