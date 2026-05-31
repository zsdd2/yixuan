<template>
  <div class="settings-images">
    <div class="page-header">
      <h1 class="page-title">系统图库</h1>
    </div>

    <div class="content-layout">
      <!-- 左侧分类 -->
      <div class="category-sidebar">
        <div
          v-for="cat in categories"
          :key="cat.value"
          class="category-item"
          :class="{ active: activeCategory === cat.value }"
          @click="activeCategory = cat.value; fetchImages()"
        >
          <span class="cat-icon">{{ cat.icon }}</span>
          <span class="cat-label">{{ cat.label }}</span>
          <span class="cat-count">{{ categoryCounts[cat.value] || 0 }}</span>
        </div>
      </div>

      <!-- 右侧内容 -->
      <div class="image-panel">
        <div class="panel-toolbar">
          <el-button type="primary" @click="showUploadDialog = true">上传图片</el-button>
          <el-button @click="showNasScan = true">NAS 扫描导入</el-button>
          <div class="search-wrap">
            <input
              v-model="searchQuery"
              class="search-input"
              placeholder="搜索名称 / 标签"
              @input="onSearchDebounced"
            />
          </div>
          <span class="img-count">共 {{ images.length }} 张</span>
        </div>

        <div class="img-grid" v-loading="loading">
          <div v-for="img in images" :key="img.id" class="img-card">
            <el-image :src="getStorageUrl(img.thumbnail_path || img.original_path)" fit="cover" lazy class="img-thumb">
              <template #error><div class="img-err">ERR</div></template>
            </el-image>
            <div class="img-info">
              <span class="img-name" :title="img.name">{{ img.name }}</span>
              <span v-if="img.tags" class="img-tags">{{ img.tags }}</span>
            </div>
            <el-button class="img-del" type="danger" size="small" text @click.stop="deleteImage(img.id)">删除</el-button>
          </div>
          <el-empty v-if="!loading && images.length === 0" description="暂无图片" :image-size="60" />
        </div>
      </div>
    </div>

    <!-- 上传弹窗（支持标签） -->
    <el-dialog v-model="showUploadDialog" title="上传图片" width="500px" destroy-on-close>
      <el-form label-width="80px">
        <el-form-item label="分类">
          <el-select v-model="uploadCategory" style="width:100%">
            <el-option v-for="cat in categories" :key="cat.value" :label="cat.label" :value="cat.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="uploadTagNames" multiple filterable allow-create default-first-option placeholder="选择或新建标签" style="width:100%">
            <el-option v-for="t in globalTags" :key="t.id" :label="t.name" :value="t.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="选择文件">
          <el-upload
            ref="uploadRef"
            :action="uploadUrl"
            name="file"
            :data="uploadFormData"
            :show-file-list="true"
            :on-success="onDialogUploaded"
            :on-error="onUploadError"
            :auto-upload="false"
            multiple
            accept=".jpg,.jpeg,.png,.webp"
          >
            <el-button>选择图片</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" @click="submitUpload">开始上传</el-button>
      </template>
    </el-dialog>

    <!-- NAS 扫描弹窗 -->
    <el-dialog v-model="showNasScan" title="NAS 扫描导入" width="560px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="导入分类">
          <el-select v-model="nasScanCategory" style="width:100%">
            <el-option v-for="cat in categories" :key="cat.value" :label="cat.label" :value="cat.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="NAS 文件夹">
          <el-input v-model="nasSelectedPath" placeholder="点击图标选择文件夹..." readonly size="default">
            <template #suffix>
              <el-icon class="nas-trigger" @click="showNasPicker = true"><FolderOpened /></el-icon>
            </template>
          </el-input>
        </el-form-item>
        <el-form-item label="标签">
          <el-select v-model="nasScanTagNames" multiple filterable allow-create default-first-option placeholder="选择或新建标签" style="width:100%">
            <el-option v-for="t in globalTags" :key="t.id" :label="t.name" :value="t.name" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showNasScan = false">取消</el-button>
        <el-button type="primary" :loading="scanning" :disabled="!nasSelectedPath" @click="doNasScan">开始扫描</el-button>
      </template>
    </el-dialog>

    <NASPathPicker v-model="showNasPicker" @select="onNasPathSelected" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { FolderOpened } from '@element-plus/icons-vue'
import NASPathPicker from '../components/NASPathPicker.vue'
import request from '../api/request'

const categories = [
  { value: 'cover', label: '封面图', icon: '🖼️' },
  { value: 'sample', label: '样图', icon: '📸' },
  { value: 'avatar', label: '头像', icon: '👤' },
  { value: 'other', label: '其他', icon: '📎' },
]

const activeCategory = ref('cover')
const images = ref<any[]>([])
const loading = ref(false)
const categoryCounts = ref<Record<string, number>>({})
const uploadUrl = '/api/v1/settings/images/upload'

// ── 搜索 ──
const searchQuery = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

function onSearchDebounced() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => fetchImages(), 300)
}

function getStorageUrl(path: string): string {
  return `/storage/${path}`
}

async function fetchImages() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (activeCategory.value) params.set('category', activeCategory.value)
    if (searchQuery.value.trim()) params.set('search', searchQuery.value.trim())
    const d = await request.get(`/api/v1/settings/images?${params}`)
    images.value = d.items
  } catch {} finally { loading.value = false }
}

async function fetchCounts() {
  for (const cat of categories) {
    try {
      const d = await request.get(`/api/v1/settings/images?category=${cat.value}`)
      categoryCounts.value[cat.value] = d.total
    } catch {}
  }
}

// ── 全局标签 ──
const globalTags = ref<any[]>([])

async function fetchGlobalTags() {
  try {
    const d = await request.get('/api/v1/settings/tags', { tag_type: 'general' })
    globalTags.value = d.items
  } catch {}
}

// ── 上传弹窗 ──
const showUploadDialog = ref(false)
const uploadCategory = ref('cover')
const uploadTagNames = ref<string[]>([])
const uploadRef = ref<any>()

const uploadFormData = computed(() => ({
  category: uploadCategory.value,
  tags: uploadTagNames.value.length ? uploadTagNames.value.join(',') : undefined,
}))

function submitUpload() {
  uploadRef.value?.submit()
}

function onDialogUploaded() {
  ElMessage.success('图片已上传')
  showUploadDialog.value = false
  uploadTagNames.value = []
  fetchImages(); fetchCounts()
}

function onUploadError() { ElMessage.error('上传失败') }

watch(showUploadDialog, (v) => {
  if (v) uploadCategory.value = activeCategory.value
})

async function deleteImage(id: number) {
  try { await ElMessageBox.confirm('删除此图片？', '确认', { type: 'warning' }) } catch { return }
  await request.delete(`/api/v1/settings/images/${id}`)
  fetchImages(); fetchCounts()
}

// ═══ NAS 扫描 ═══
const showNasScan = ref(false)
const showNasPicker = ref(false)
const nasScanCategory = ref('sample')
const nasSelectedPath = ref('')
const nasScanTagNames = ref<string[]>([])
const scanning = ref(false)

function onNasPathSelected(path: string) {
  nasSelectedPath.value = path === '.' ? '/' : '/' + path
}

watch(showNasScan, (v) => {
  if (v) { nasScanCategory.value = activeCategory.value; nasSelectedPath.value = ''; nasScanTagNames.value = [] }
})

async function doNasScan() {
  scanning.value = true
  try {
    const d = await request.post('/api/v1/settings/images/scan-nas', {
      path: nasSelectedPath.value.replace(/^\//, '') || '.',
      category: nasScanCategory.value,
      tags: nasScanTagNames.value.length ? nasScanTagNames.value.join(',') : null,
    })
    ElMessage.success(d.msg || '扫描完成')
    showNasScan.value = false
    fetchImages(); fetchCounts()
  } catch (e: any) { ElMessage.error(e.message) }
  finally { scanning.value = false }
}

onMounted(() => { fetchImages(); fetchCounts(); fetchGlobalTags() })
</script>

<style scoped>
.settings-images { padding: 20px 28px; min-height: 100%; }
.page-header { margin-bottom: 16px; }
.page-title { font-size: 24px; font-weight: 700; color: #2c3e50; }

.content-layout { display: flex; gap: 16px; min-height: 600px; }

.category-sidebar {
  width: 180px; min-width: 180px;
  background: white; border-radius: 8px; padding: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  display: flex; flex-direction: column; gap: 2px;
}
.category-item {
  display: flex; align-items: center; gap: 8px;
  padding: 12px 14px; border-radius: 6px; cursor: pointer;
  font-size: 14px; color: #4B5563; transition: all 0.15s;
}
.category-item:hover { background: #F9FAFB; }
.category-item.active { background: #EFF6FF; color: #2563EB; font-weight: 600; }
.cat-icon { font-size: 16px; width: 20px; text-align: center; }
.cat-label { flex: 1; }
.cat-count { font-size: 12px; color: #909399; background: #f0f0f0; padding: 1px 6px; border-radius: 8px; }

.image-panel {
  flex: 1; background: white; border-radius: 8px; padding: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.panel-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.img-count { font-size: 13px; color: #909399; }

.nas-trigger { cursor: pointer; font-size: 18px; color: #409eff; }

.img-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
.img-card { position: relative; border-radius: 8px; overflow: hidden; border: 1px solid #ebeef5; background: white; }
.img-thumb { width: 100%; aspect-ratio: 1; display: block; }
.img-thumb :deep(img) { width: 100%; height: 100%; object-fit: cover; }
.img-err { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #f5f7fa; color: #c0c4cc; font-size: 12px; }
.img-info { padding: 6px 8px; }
.img-name { font-size: 12px; color: #2c3e50; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.img-tags { font-size: 11px; color: #909399; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; margin-top: 2px; }
.img-del { position: absolute; top: 4px; right: 4px; background: rgba(255,255,255,0.9); border-radius: 4px; }

.search-wrap { margin-left: auto; }
.search-input {
  width: 200px; padding: 6px 10px; border: 1px solid #dcdfe6; border-radius: 6px;
  font-size: 13px; outline: none; background: #fff; transition: border-color .15s;
}
.search-input:focus { border-color: #409eff; }
.search-input::placeholder { color: #c0c4cc; }

.tag-input {
  width: 100%; padding: 6px 10px; border: 1px solid #dcdfe6; border-radius: 4px;
  font-size: 13px; outline: none;
}
.tag-input:focus { border-color: #409eff; }
</style>
