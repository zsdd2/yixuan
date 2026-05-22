<template>
  <div class="delivery-page">
    <div v-if="loading" class="loading-container">
      <el-icon class="is-loading" :size="40"><Loading /></el-icon>
      <div style="margin-top: 16px; color: #909399;">加载中...</div>
    </div>

    <div v-else-if="error" class="error-container">
      <el-result icon="error" :title="error" />
    </div>

    <div v-else-if="data" class="delivery-content">
      <div class="header">
        <h1 class="project-title">{{ data.project_name }}</h1>
        <div class="client-info">客户：{{ data.client_name }}</div>
        <div class="meta-info">
          <span>归档日期：{{ formatDate(data.archived_at) }}</span>
          <span style="margin-left: 24px;">照片数量：{{ data.photo_count }} 张</span>
        </div>
      </div>

      <div class="download-section">
        <el-button
          type="primary"
          size="large"
          :loading="downloading"
          @click="downloadZip"
          :disabled="data.zip_status !== 'completed'"
        >
          <el-icon style="margin-right: 8px;"><Download /></el-icon>
          {{ downloadButtonText }}
        </el-button>

        <div v-if="data.zip_status !== 'completed'" class="status-tip">
          <el-alert
            :type="data.zip_status === 'failed' ? 'error' : 'info'"
            :closable="false"
          >
            {{ zipStatusText }}
          </el-alert>
        </div>
      </div>

      <div class="preview-section">
        <h2 class="section-title">照片预览</h2>

        <div v-if="data.group_by === 'target'" class="target-groups">
          <div v-for="group in data.groups" :key="group.target_id" class="group-card">
            <div class="group-header">
              <h3>{{ group.target_name }}</h3>
              <span class="photo-count">{{ group.photos.length }} 张</span>
            </div>
            <div class="photo-grid">
              <div
                v-for="photo in group.photos"
                :key="photo.photo_id"
                class="photo-item"
                @click="previewPhoto(photo)"
              >
                <img :src="photo.thumbnail_url" :alt="photo.filename" />
              </div>
            </div>
          </div>
        </div>

        <div v-else class="category-groups">
          <div v-for="group in data.groups" :key="group.category_name" class="group-card">
            <div class="group-header">
              <h3>{{ group.category_name || '未分类' }}</h3>
              <span class="photo-count">{{ group.photos.length }} 张</span>
            </div>
            <div class="photo-grid">
              <div
                v-for="photo in group.photos"
                :key="photo.photo_id"
                class="photo-item"
                @click="previewPhoto(photo)"
              >
                <img :src="photo.thumbnail_url" :alt="photo.filename" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 大图预览 - 拍立得相框风格 -->
    <Teleport to="body">
      <div v-if="showViewer" class="preview-mask" @click.self="showViewer = false">
        <div class="polaroid-wrapper">
          <!-- 拍立得相框容器 -->
          <div class="polaroid-frame">
            <img
              :src="currentPreviewUrl"
              class="polaroid-img"
              ref="polaroidImgRef"
              @load="onImageLoad"
            />
            <!-- 底部白边信息区 -->
            <div class="polaroid-caption">
              <div class="caption-line">{{ currentPhotoData?.target_name || '未分配' }}</div>
              <div class="caption-line caption-filename">{{ currentPhotoData?.filename || '—' }}</div>
              <div class="caption-line caption-id">#{{ String(currentPhotoData?.display_id || '000').padStart(3, '0') }}</div>
              <div class="caption-line caption-project">{{ data?.project_name }}</div>
            </div>
          </div>
          <!-- 右侧按钮组（下载 + 放大镜） -->
          <button
            class="polaroid-side-btn polaroid-download-btn"
            @click="downloadPhoto(currentPhotoData)"
            title="下载原图"
          >
            <span class="download-icon">⬇</span>
          </button>
          <button
            v-if="currentPhotoData?.thumbnail_url"
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
          <!-- 导航按钮 -->
          <button v-if="previewIndex > 0" class="preview-nav-close prev" @click.stop="navPrev">‹</button>
          <button v-if="previewIndex < allPhotos.length - 1" class="preview-nav-close next" @click.stop="navNext">›</button>
        </div>
        <!-- 关闭按钮 -->
        <button class="preview-close" @click="showViewer = false">✕</button>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading, Download } from '@element-plus/icons-vue'
import request from '../api/request'

const route = useRoute()
const token = computed(() => route.params.token as string)

const loading = ref(true)
const error = ref('')
const data = ref<any>(null)
const downloading = ref(false)
const showViewer = ref(false)
const previewIndex = ref(0)
const allPhotos = ref<any[]>([])
const polaroidImgRef = ref<HTMLImageElement | null>(null)
const showOriginal = ref(false)
const loadingOriginal = ref(false)

const currentPhotoData = computed(() => allPhotos.value[previewIndex.value])

const currentPreviewUrl = computed(() => {
  if (!currentPhotoData.value) return ''

  if (showOriginal.value) {
    return currentPhotoData.value.preview_url || currentPhotoData.value.thumbnail_url
  }

  return currentPhotoData.value.thumbnail_url
})

const downloadButtonText = computed(() => {
  if (!data.value) return '下载照片'
  if (data.value.zip_status === 'completed') return '下载全部照片'
  if (data.value.zip_status === 'processing') return '正在生成压缩包...'
  if (data.value.zip_status === 'pending') return '等待生成压缩包...'
  if (data.value.zip_status === 'failed') return '压缩包生成失败'
  return '下载照片'
})

const zipStatusText = computed(() => {
  if (!data.value) return ''
  if (data.value.zip_status === 'processing') return '正在生成压缩包，请稍候刷新页面...'
  if (data.value.zip_status === 'pending') return '压缩包正在队列中，预计将在凌晨2点后生成'
  if (data.value.zip_status === 'failed') return '压缩包生成失败，请联系工作人员'
  return ''
})

onMounted(() => {
  loadDeliveryData()
})

async function loadDeliveryData() {
  loading.value = true
  error.value = ''

  try {
    const result = await request.get(`/api/v1/deliveries/${token.value}`)

    if (result.code === 200) {
      data.value = result.data
    } else if (result.code === 404) {
      error.value = '分享链接不存在或已失效'
    } else if (result.code === 410) {
      error.value = '分享链接已过期'
    } else {
      error.value = result.msg || '加载失败'
    }
  } catch (e) {
    console.error('加载交付数据失败:', e)
    error.value = '网络错误，请稍后重试'
  } finally {
    loading.value = false
  }
}

async function downloadZip() {
  if (data.value.zip_status !== 'completed') return

  downloading.value = true
  try {
    const res = await fetch(`/api/v1/deliveries/${token.value}/download`)

    if (!res.ok) {
      const result = await res.json()
      ElMessage.error(result.msg || '下载失败')
      return
    }

    const blob = await res.blob()
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${data.value.project_name}_${formatDate(data.value.archived_at)}.zip`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    window.URL.revokeObjectURL(url)

    ElMessage.success('下载成功')
  } catch (e) {
    console.error('下载失败:', e)
    ElMessage.error('下载失败')
  } finally {
    downloading.value = false
  }
}

function previewPhoto(photo: any) {
  allPhotos.value = data.value.groups.flatMap((g: any) => g.photos)
  previewIndex.value = allPhotos.value.findIndex((p: any) => p.photo_id === photo.photo_id)
  showOriginal.value = false
  loadingOriginal.value = false
  showViewer.value = true
}

function navPrev() {
  if (previewIndex.value > 0) {
    previewIndex.value--
    showOriginal.value = false
    loadingOriginal.value = false
  }
}

function navNext() {
  if (previewIndex.value < allPhotos.value.length - 1) {
    previewIndex.value++
    showOriginal.value = false
    loadingOriginal.value = false
  }
}

function toggleOriginal() {
  if (!currentPhotoData.value?.thumbnail_url) return

  if (showOriginal.value) {
    showOriginal.value = false
    loadingOriginal.value = false
  } else {
    loadingOriginal.value = true
    showOriginal.value = true

    const photo = currentPhotoData.value
    const img = new Image()
    img.onload = () => {
      loadingOriginal.value = false
    }
    img.onerror = () => {
      loadingOriginal.value = false
      showOriginal.value = false
    }
    img.src = photo.preview_url || photo.thumbnail_url
  }
}

function onImageLoad() {
  // 图片加载完成回调
}

function downloadPhoto(photo: any) {
  if (!photo) return
  const url = photo.preview_url || photo.thumbnail_url
  const a = document.createElement('a')
  a.href = url
  a.download = photo.filename || `photo_${photo.photo_id}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
}

function formatDate(dateStr: string) {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('zh-CN')
}
</script>

<style scoped>
/* 独立样式重置 - 避免受管理后台样式污染 */
.delivery-page,
.delivery-page *,
.delivery-page *::before,
.delivery-page *::after {
  box-sizing: border-box;
}

.delivery-page {
  min-height: 100vh;
  background: #f5f7fa;
}

.loading-container,
.error-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
}

.delivery-content {
  max-width: 1400px;
  margin: 0 auto;
  padding: 40px 20px;
}

.header {
  text-align: center;
  margin-bottom: 48px;
}

.project-title {
  font-size: 32px;
  font-weight: 700;
  color: #2c3e50;
  margin-bottom: 12px;
}

.client-info {
  font-size: 18px;
  color: #606266;
  margin-bottom: 8px;
}

.meta-info {
  font-size: 14px;
  color: #909399;
}

.download-section {
  text-align: center;
  margin-bottom: 48px;
}

.status-tip {
  max-width: 600px;
  margin: 16px auto 0;
}

.preview-section {
  margin-top: 48px;
}

.section-title {
  font-size: 24px;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 24px;
  text-align: center;
}

.group-card {
  background: white;
  border-radius: 8px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 2px solid #e4e7ed;
}

.group-header h3 {
  font-size: 18px;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.photo-count {
  font-size: 14px;
  color: #909399;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.photo-item {
  aspect-ratio: 1;
  border-radius: 4px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s;
}

.photo-item:hover {
  transform: scale(1.05);
}

.photo-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 大图预览 - 拍立得相框风格 */
.preview-mask {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: rgba(0, 0, 0, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.polaroid-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.polaroid-frame {
  position: relative;
  background: white;
  padding: 16px 16px 0 16px;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.05);
  max-width: 85vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}

.polaroid-img {
  width: 100%;
  max-height: calc(85vh - 140px);
  object-fit: contain;
  display: block;
}

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

.polaroid-download-btn {
  top: 16px;
  font-size: 24px;
}

.download-icon {
  display: block;
  line-height: 1;
}

.polaroid-zoom-btn {
  top: calc(16px + 58px + 12px);
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

.preview-close {
  position: absolute;
  top: 20px;
  right: 24px;
  background: none;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: #fff;
  font-size: 32px;
  cursor: pointer;
  opacity: 0.8;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.15);
  backdrop-filter: blur(8px);
  transition: all 0.2s;
}

.preview-close:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.25);
  transform: scale(1.05);
}

.preview-nav-close {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 52px;
  height: 52px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.15);
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
  background: rgba(255, 255, 255, 0.25);
  opacity: 1;
  transform: translateY(-50%) scale(1.08);
}

.preview-nav-close.prev {
  left: -70px;
}

.preview-nav-close.next {
  right: -70px;
}

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
