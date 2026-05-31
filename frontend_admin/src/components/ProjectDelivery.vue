<template>
  <div class="delivery-view">
    <div class="delivery-header">
      <el-button @click="$emit('back')" :icon="ArrowLeft">返回看板</el-button>
      <h2 class="delivery-title">最终交付图</h2>
      <span class="delivery-count">{{ photos.length }} 张成片</span>
      <div class="header-actions">
        <el-button @click="showShareModal = true" :disabled="photos.length === 0">
          创建客户分享
        </el-button>
        <el-checkbox v-model="selectAll" @change="toggleSelectAll" :indeterminate="isIndeterminate">全选</el-checkbox>
        <el-button type="primary" :disabled="selectedIds.size === 0" @click="downloadSelected">
          下载选中 ({{ selectedIds.size }})
        </el-button>
      </div>
    </div>

    <!-- 场景图成片 -->
    <div v-if="scenePhotos.length > 0" class="delivery-section">
      <h3 class="section-title">场景图</h3>
      <div class="delivery-grid">
        <div v-for="item in scenePhotos" :key="item.id" class="delivery-card">
          <el-checkbox
            :model-value="selectedIds.has(item.id)"
            @change="toggleSelect(item.id)"
            class="card-checkbox"
            @click.stop
          />
          <div @click="openPreview(item)" class="card-content">
            <el-image :src="thumbUrl(item)" fit="cover" lazy class="delivery-img">
              <template #error><div class="delivery-placeholder">-</div></template>
            </el-image>
            <div class="delivery-info">
              <div class="info-line-1">{{ item.target_name }}</div>
              <div class="info-line-2">#{{ String(item.display_id).padStart(3,'0') }}</div>
              <div class="info-line-3">{{ item.original_filename || '—' }}</div>
              <div class="info-line-4">{{ projectName }}</div>
            </div>
          </div>
          <el-select
            v-model="item.portfolio_tag_ids"
            class="portfolio-tag-select"
            multiple
            collapse-tags
            collapse-tags-tooltip
            clearable
            size="small"
            placeholder="作品标签"
            @click.stop
            @change="updatePortfolioTags(item)"
          >
            <el-option v-for="tag in systemTags" :key="tag.id" :label="tag.name" :value="tag.id" />
          </el-select>
        </div>
      </div>
    </div>

    <!-- 白图成片 -->
    <div v-if="whitePhotos.length > 0" class="delivery-section">
      <h3 class="section-title">白图</h3>
      <div class="delivery-grid">
        <div v-for="item in whitePhotos" :key="item.id" class="delivery-card">
          <el-checkbox
            :model-value="selectedIds.has(item.id)"
            @change="toggleSelect(item.id)"
            class="card-checkbox"
            @click.stop
          />
          <div @click="openPreview(item)" class="card-content">
            <el-image :src="thumbUrl(item)" fit="cover" lazy class="delivery-img">
              <template #error><div class="delivery-placeholder">-</div></template>
            </el-image>
            <div class="delivery-info">
              <div class="info-line-1">{{ item.target_name }}</div>
              <div class="info-line-2">#{{ String(item.display_id).padStart(3,'0') }}</div>
              <div class="info-line-3">{{ item.original_filename || '—' }}</div>
              <div class="info-line-4">{{ projectName }}</div>
            </div>
          </div>
          <el-select
            v-model="item.portfolio_tag_ids"
            class="portfolio-tag-select"
            multiple
            collapse-tags
            collapse-tags-tooltip
            clearable
            size="small"
            placeholder="作品标签"
            @click.stop
            @change="updatePortfolioTags(item)"
          >
            <el-option v-for="tag in systemTags" :key="tag.id" :label="tag.name" :value="tag.id" />
          </el-select>
        </div>
      </div>
    </div>

    <el-empty v-if="photos.length === 0" description="暂无成片" />

    <!-- 分享模态框 -->
    <ShareDeliveryModal
      v-model:visible="showShareModal"
      :project-id="Number(props.projectId)"
    />

    <!-- 大图预览 - 拍立得相框风格（复用作品中心标准实现） -->
    <Teleport to="body">
      <div v-if="previewVisible" class="preview-mask" @click.self="previewVisible = false">
        <!-- 相框容器包装器（用于定位下载按钮） -->
        <div class="polaroid-wrapper">
          <!-- 拍立得相框容器 -->
          <div class="polaroid-frame" ref="polaroidFrameRef">
            <img
              :src="currentPreviewUrl"
              class="polaroid-img"
              ref="polaroidImgRef"
              @load="onImageLoad"
            />
            <!-- 底部白边信息区 -->
            <div class="polaroid-caption">
              <div class="caption-line">{{ previewItem?.target_name }}</div>
              <div class="caption-line caption-filename">{{ previewItem?.original_filename || '—' }}</div>
              <div class="caption-line caption-id">#{{ String(previewItem?.display_id || 0).padStart(3, '0') }}</div>
              <div class="caption-line caption-project">{{ projectName }}</div>
            </div>
          </div>
          <!-- 右侧按钮组（下载 + 放大镜） -->
          <button
            class="polaroid-side-btn polaroid-download-btn"
            @click="downloadOriginal(previewItem)"
            title="下载原图"
          >
            <span class="download-icon">⬇</span>
          </button>
          <button
            v-if="previewItem?.thumbnail_path"
            class="polaroid-side-btn polaroid-zoom-btn"
            :class="{ active: showOriginal }"
            :disabled="loadingOriginal"
            @click="toggleOriginal"
            :title="showOriginal ? '查看缩略图' : '查看原图'"
          >
            <svg v-if="!loadingOriginal" width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <circle cx="11" cy="11" r="8" stroke-width="2"/>
              <path d="M21 21l-4.35-4.35" stroke-width="2" stroke-linecap="round"/>
              <path v-if="!showOriginal" d="M11 8v6M8 11h6" stroke-width="2" stroke-linecap="round"/>
              <path v-else d="M8 11h6" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <svg v-else class="loading-spinner" width="20" height="20" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" fill="none" opacity="0.25"/>
              <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>
            </svg>
          </button>
          <!-- 导航按钮（贴近图片） -->
          <button v-if="currentIndex > 0" class="preview-nav-close prev" @click.stop="navPrev">‹</button>
          <button v-if="currentIndex < photos.length - 1" class="preview-nav-close next" @click.stop="navNext">›</button>
        </div>
        <!-- 关闭按钮 -->
        <button class="preview-close" @click="previewVisible = false">✕</button>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ArrowLeft } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import ShareDeliveryModal from './ShareDeliveryModal.vue'
import request from '../api/request'
import { downloadStorageFile } from '../composables/usePhotoDownload'

interface DeliveryPhoto {
  id: number
  display_id: number
  target_name: string
  category_type: string
  original_path: string
  original_filename: string | null
  thumbnail_path: string | null
  portfolio_tag_ids: number[]
}

interface SystemTagItem {
  id: number
  name: string
  color: string
}

const props = defineProps<{ projectId: string | number }>()
defineEmits<{ back: [] }>()

const photos = ref<DeliveryPhoto[]>([])
const projectName = ref<string>('')
const previewVisible = ref(false)
const previewItem = ref<DeliveryPhoto | null>(null)
const currentIndex = ref(0)
const selectedIds = ref<Set<number>>(new Set())
const selectAll = ref(false)
const showShareModal = ref(false)
const systemTags = ref<SystemTagItem[]>([])
const polaroidImgRef = ref<HTMLImageElement | null>(null)
const showOriginal = ref(false) // 默认显示缩略图（内部工作台也改为缩略图优先）

const whitePhotos = computed(() => photos.value.filter(p => p.category_type === 'white'))
const scenePhotos = computed(() => photos.value.filter(p => p.category_type === 'scene'))

const isIndeterminate = computed(() => {
  const size = selectedIds.value.size
  return size > 0 && size < photos.value.length
})

const currentPreviewUrl = computed(() => {
  if (!previewItem.value) return ''

  if (showOriginal.value) {
    return `/storage/${previewItem.value.original_path}`
  }

  const thumbPath = previewItem.value.thumbnail_path || previewItem.value.original_path
  return `/storage/${thumbPath}`
})

const loadingOriginal = ref(false)

function toggleSelect(id: number) {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
  updateSelectAllState()
}

function toggleSelectAll(checked: boolean) {
  if (checked) {
    photos.value.forEach(p => selectedIds.value.add(p.id))
  } else {
    selectedIds.value.clear()
  }
}

function updateSelectAllState() {
  selectAll.value = selectedIds.value.size === photos.value.length && photos.value.length > 0
}

async function downloadSelected() {
  if (selectedIds.value.size === 0) return

  const loadingMsg = ElMessage({
    message: '正在打包中，请稍候...',
    type: 'info',
    duration: 0,
    icon: 'Loading',
  })

  try {
    const token = localStorage.getItem('token')
    const ids = Array.from(selectedIds.value).join(',')
    const res = await fetch(`/api/v1/projects/${props.projectId}/photos/download?photo_ids=${ids}`, {
      headers: { 'Authorization': `Bearer ${token}` }
    })

    if (!res.ok) {
      const errorText = await res.text()
      console.error('下载失败 HTTP', res.status, errorText)
      throw new Error(`HTTP ${res.status}`)
    }

    const blob = await res.blob()
    if (blob.size === 0) {
      throw new Error('下载的文件为空')
    }

    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `交付图_${new Date().getTime()}.zip`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)

    loadingMsg.close()
    ElMessage.success('下载成功')
  } catch (e: any) {
    loadingMsg.close()
    console.error('下载失败:', e)
    ElMessage.error(`下载失败: ${e.message || '网络错误'}`)
  }
}

function thumbUrl(photo: DeliveryPhoto): string {
  const path = photo.thumbnail_path || photo.original_path
  return `/storage/${path}`
}

function openPreview(photo: DeliveryPhoto) {
  previewItem.value = photo
  currentIndex.value = photos.value.indexOf(photo)
  showOriginal.value = false // 每次打开预览都重置为缩略图
  loadingOriginal.value = false
  previewVisible.value = true
}

function navPrev() {
  if (currentIndex.value > 0) {
    currentIndex.value--
    previewItem.value = photos.value[currentIndex.value]
    showOriginal.value = false // 切换图片时重置为缩略图
    loadingOriginal.value = false
  }
}

function navNext() {
  if (currentIndex.value < photos.value.length - 1) {
    currentIndex.value++
    previewItem.value = photos.value[currentIndex.value]
    showOriginal.value = false // 切换图片时重置为缩略图
    loadingOriginal.value = false
  }
}

function onKeydown(e: KeyboardEvent) {
  if (!previewVisible.value) return
  if (e.key === 'Escape') previewVisible.value = false
  else if (e.key === 'ArrowLeft') navPrev()
  else if (e.key === 'ArrowRight') navNext()
}

function onImageLoad() {
  // 图片加载完成回调（作品中心标准实现不需要动态按钮尺寸）
}

function toggleOriginal() {
  if (!previewItem.value?.thumbnail_path) return

  if (showOriginal.value) {
    // 切换回缩略图
    showOriginal.value = false
    loadingOriginal.value = false
  } else {
    // 加载原图
    loadingOriginal.value = true
    showOriginal.value = true

    // 预加载原图
    const photo = previewItem.value
    const img = new Image()
    img.onload = () => {
      loadingOriginal.value = false
    }
    img.onerror = () => {
      loadingOriginal.value = false
      ElMessage.error('原图加载失败')
      showOriginal.value = false
    }
    img.src = `/storage/${photo.original_path}`
  }
}

function downloadOriginal(photo: DeliveryPhoto | null) {
  if (!photo) return
  downloadStorageFile(photo.original_path, photo.original_filename || `photo_${photo.display_id}`)
}

async function fetchSystemTags() {
  try {
    const data = await request.get('/api/v1/settings/tags')
    systemTags.value = data.items || []
  } catch {
    systemTags.value = []
  }
}

async function updatePortfolioTags(photo: DeliveryPhoto) {
  try {
    const data = await request.patch(`/api/v1/photos/${photo.id}/portfolio-tags`, {
      tag_ids: photo.portfolio_tag_ids || [],
    })
    photo.portfolio_tag_ids = data.portfolio_tag_ids || []
    ElMessage.success('作品标签已更新')
  } catch (e: any) {
    ElMessage.error(e.message || '作品标签更新失败')
  }
}

async function fetchDeliveryPhotos() {
  try {
    const [photosData, targetsData, projectData] = await Promise.all([
      request.get(`/api/v1/projects/${props.projectId}/photos`, { skip: '0', limit: '500', process_state: 'final', assigned_only: 'true' }),
      request.get(`/api/v1/projects/${props.projectId}/targets`),
      request.get(`/api/v1/projects/${props.projectId}`),
    ])

    projectName.value = projectData.name || ''

    const targetMap = new Map<number, { name: string; category_type: string }>()
    for (const t of targetsData.items) {
      targetMap.set(t.id, { name: t.name, category_type: t.category_type })
    }

    photos.value = photosData.items
      .filter((p: any) => p.status !== 'deleted' && targetMap.has(p.target_id))
      .map((p: any) => {
        const target = targetMap.get(p.target_id) || { name: '未分配', category_type: 'white' }
        return {
          id: p.id,
          display_id: p.display_id,
          target_name: target.name,
          category_type: target.category_type,
          original_path: p.original_path,
          original_filename: p.original_filename || null,
          thumbnail_path: p.thumbnail_path,
          portfolio_tag_ids: p.portfolio_tag_ids || [],
        }
      })
  } catch {}
}

onMounted(() => {
  fetchSystemTags()
  fetchDeliveryPhotos()
  document.addEventListener('keydown', onKeydown)
})
onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.delivery-view { padding: 24px 32px; min-height: 100%; }
.delivery-header { display: flex; align-items: center; gap: 16px; margin-bottom: 24px; }
.delivery-title { font-size: 20px; font-weight: 700; color: #2c3e50; margin: 0; }
.delivery-count { font-size: 13px; color: #909399; }
.header-actions { margin-left: auto; display: flex; align-items: center; gap: 12px; }

.delivery-section { margin-bottom: 32px; }
.section-title { font-size: 16px; font-weight: 600; color: #2c3e50; margin: 0 0 16px; }

.delivery-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px;
}

.delivery-card {
  border-radius: 16px; overflow: hidden; position: relative;
  background: white; box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  transition: transform 0.3s, box-shadow 0.3s;
}
.delivery-card:hover { transform: translateY(-4px); box-shadow: 0 8px 28px rgba(0,0,0,0.15); }

.card-checkbox {
  position: absolute; top: 10px; left: 10px; z-index: 10;
  background: rgba(255,255,255,0.95); border-radius: 6px; padding: 4px;
}

.card-content { cursor: pointer; }

.portfolio-tag-select {
  width: calc(100% - 24px);
  margin: 0 12px 14px;
}

.delivery-img { width: 100%; aspect-ratio: 4/3; }
.delivery-img :deep(img) { width: 100%; height: 100%; object-fit: cover; }
.delivery-placeholder { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #f5f7fa; color: #c0c4cc; }

/* 拍立得卡片信息区 - 四行居中布局 */
.delivery-info {
  padding: 16px 12px 14px;
  text-align: center;
  background: white;
}
.info-line-1 {
  font-size: 18px;
  font-weight: 800;
  color: #000;
  margin-bottom: 4px;
  letter-spacing: -0.3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.info-line-2 {
  font-size: 14px;
  color: #6b7280;
  margin-bottom: 6px;
  font-family: 'Courier New', monospace;
}
.info-line-3 {
  font-size: 12px;
  color: #374151;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.info-line-4 {
  font-size: 11px;
  color: #9ca3af;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 0;
}

/* 大图预览 - 拍立得相框风格 */
.preview-mask {
  position: fixed; inset: 0; z-index: 2000;
  background: rgba(0,0,0,0.92);
  display: flex; align-items: center; justify-content: center;
  padding: 40px;
}

/* 相框包装器（用于定位外置按钮） */
.polaroid-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 拍立得相框容器 */
.polaroid-frame {
  position: relative;
  background: white;
  padding: 16px 16px 0 16px;
  border-radius: 8px;
  border: 1px solid rgba(0,0,0,0.05);
  max-width: 85vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}

.polaroid-img {
  width: 100%;
  max-height: calc(85vh - 160px);
  object-fit: contain;
  display: block;
}

/* 右侧按钮组 - 统一样式，垂直排列（复用作品中心标准） */
.polaroid-side-btn {
  position: absolute;
  left: calc(100% + 12px);
  width: 58px;
  height: 58px;
  background: #ffffff;
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #6b7280;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.polaroid-side-btn:hover:not(:disabled) {
  background: #f9fafb;
  transform: translateY(1px);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
}

.polaroid-side-btn:active:not(:disabled) {
  transform: translateY(2px);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
}

/* 下载按钮 */
.polaroid-download-btn {
  top: 16px;
  font-size: 24px;
}

.download-icon {
  display: block;
  line-height: 1;
}

/* 放大镜按钮 */
.polaroid-zoom-btn {
  top: calc(16px + 58px + 12px); /* 下载按钮下方，间距 12px */
}

.polaroid-zoom-btn.active {
  background: #3b82f6;
  color: white;
  border-color: #3b82f6;
}

.polaroid-zoom-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.loading-spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* 底部白边信息区 */
.polaroid-caption {
  padding: 20px 16px 24px;
  text-align: center;
  background: white;
  border-radius: 0 0 8px 8px;
}
.caption-line {
  font-size: 15px;
  color: #1f2937;
  font-weight: 600;
  margin-bottom: 4px;
}
.caption-filename {
  font-size: 13px;
  color: #4b5563;
  font-weight: 400;
  margin-bottom: 6px;
}
.caption-id {
  font-size: 12px;
  color: #9ca3af;
  font-weight: 500;
  font-family: 'Courier New', monospace;
  margin-bottom: 4px;
}
.caption-project {
  font-size: 11px;
  color: #9ca3af;
  font-weight: 400;
  margin-bottom: 0;
}

.preview-close {
  position: absolute; top: 20px; right: 24px;
  background: none; border: 1px solid rgba(255,255,255,0.1); color: #fff; font-size: 32px; cursor: pointer; opacity: 0.8;
  width: 44px; height: 44px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 50%;
  background: rgba(255,255,255,0.15);
  backdrop-filter: blur(8px);
  transition: all 0.2s;
}
.preview-close:hover { opacity: 1; background: rgba(255,255,255,0.25); transform: scale(1.05); }

/* 导航按钮 - 贴近图片护航式布局 */
.preview-nav-close {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: 1px solid rgba(255,255,255,0.1);
  background: rgba(255,255,255,0.15);
  backdrop-filter: blur(8px);
  color: white;
  font-size: 32px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  opacity: 0.7;
}
.preview-nav-close:hover {
  background: rgba(255,255,255,0.25);
  opacity: 1;
  transform: translateY(-50%) scale(1.08);
}
.preview-nav-close.prev {
  left: -70px;
}
.preview-nav-close.next {
  right: -70px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .polaroid-frame {
    padding: 12px 12px 0 12px;
    max-width: 95vw;
    max-height: 90vh;
  }

  .polaroid-img {
    max-height: calc(90vh - 140px);
  }
  .polaroid-caption {
    padding: 16px 12px 20px;
  }
  .polaroid-side-btn {
    width: 48px;
    height: 48px;
    font-size: 20px;
  }
  .polaroid-download-btn {
    top: 12px;
  }
  .polaroid-zoom-btn {
    top: calc(12px + 48px + 12px);
  }
  .preview-nav-close.prev {
    left: -60px;
  }
  .preview-nav-close.next {
    right: -60px;
  }
}
</style>
