<template>
  <div class="review-page">
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="8" animated />
    </div>

    <div v-else-if="error" class="error-state">
      <el-result icon="error" :title="error" />
    </div>

    <div v-else class="review-container">
      <!-- Header -->
      <div class="header">
        <div class="project-info">
          <el-image
            v-if="data.cover_image"
            :src="`/storage/${data.cover_image}`"
            class="cover"
            fit="cover"
          />
          <div class="info">
            <h1>{{ data.project_name }}</h1>
            <p>{{ data.client_name }} · {{ data.project_display_id }}</p>
          </div>
        </div>
        <div v-if="data.is_expired" class="expired-badge">链接已过期</div>
      </div>

      <!-- Main Content: Sidebar + Content -->
      <div class="main-content">
        <!-- Left Sidebar: Accordion Navigation -->
        <div class="sidebar" :class="{ collapsed: sidebarCollapsed }">
          <div class="sidebar-header">
            <span v-if="!sidebarCollapsed">子项目导航</span>
            <el-button
              text
              :icon="sidebarCollapsed ? 'ArrowRight' : 'ArrowLeft'"
              @click="sidebarCollapsed = !sidebarCollapsed"
            />
          </div>

          <el-collapse v-if="!sidebarCollapsed" v-model="activeCategories" class="nav-collapse">
            <el-collapse-item
              v-for="cat in data.categories"
              :key="cat.category_type"
              :name="cat.category_type"
            >
              <template #title>
                <div class="category-header">
                  <span class="category-label">{{ cat.category_label }}</span>
                  <span class="category-count">{{ getCategoryTotalCount(cat) }}</span>
                </div>
              </template>

              <div class="target-list">
                <div
                  v-for="target in cat.targets"
                  :key="target.target_name"
                  class="target-item"
                  :class="{ active: activeTarget === getTargetKey(cat.category_type, target.target_name) }"
                  @click="scrollToTarget(cat.category_type, target.target_name)"
                >
                  <div class="target-name">{{ target.target_name }}</div>
                  <div class="target-stats">
                    <span class="confirmed">{{ target.confirmed_count }}</span>
                    <span class="separator">/</span>
                    <span class="total">{{ target.total_count }}</span>
                    <span class="label">已确认</span>
                  </div>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>

        <!-- Right Content Area -->
        <div class="content-area" @scroll="handleScroll">
          <div
            v-for="cat in data.categories"
            :key="cat.category_type"
            class="category-section"
          >
            <h2 class="category-title">{{ cat.category_label }}</h2>

            <div
              v-for="target in cat.targets"
              :key="target.target_name"
              :ref="el => setTargetRef(cat.category_type, target.target_name, el)"
              class="target-group"
            >
              <div class="target-header">
                <h3 class="target-title">{{ target.target_name }}</h3>
                <div class="target-progress">
                  {{ target.confirmed_count }} / {{ target.total_count }} 已确认
                </div>
              </div>

              <div class="photo-grid">
                <div v-for="(photo, photoIndex) in target.photos" :key="photo.id" class="photo-item" :class="{ discarded: isDiscarded(photo) }">
                  <div class="photo-img-wrapper" @click="openLightbox(photo, target.photos, Number(photoIndex))">
                    <el-image
                      :src="`/storage/${photo.thumbnail_path}`"
                      fit="cover"
                      class="photo-img"
                    />
                    <!-- Process State Badge -->
                    <div class="process-state-badge">
                      {{ getProcessStateLabel(photo.process_state) }}
                    </div>
                  </div>
                  <div class="photo-info">
                    <div class="filename">{{ photo.original_filename || `#${photo.display_id}` }}</div>
                    <div v-if="photo.version && photo.version > 1" class="version-badge">
                      v{{ photo.version }}
                    </div>
                  </div>
                  <div class="photo-actions">
                    <el-button
                      :type="photo.feedback?.is_confirmed ? 'success' : 'default'"
                      size="small"
                      :disabled="data.is_expired"
                      @click.stop="quickConfirm(photo)"
                    >
                      {{ photo.feedback?.is_confirmed ? '确认无需修改' : '无需修改' }}
                    </el-button>
                    <el-button
                      type="warning"
                      size="small"
                      :disabled="data.is_expired"
                      @click.stop="quickComment(photo)"
                    >
                      继续修改
                    </el-button>
                    <el-button
                      type="info"
                      size="small"
                      :disabled="data.is_expired"
                      @click.stop="discardPhoto(photo)"
                    >
                      弃用
                    </el-button>
                  </div>
                  <div v-if="photo.feedback?.comment" class="comment-preview">
                    {{ photo.feedback.comment }}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Comment Dialog -->
    <el-dialog v-model="showComment" title="修改意见" width="500px">
      <el-input
        v-model="commentText"
        type="textarea"
        :rows="4"
        placeholder="请输入您的修改意见..."
      />
      <template #footer>
        <el-button @click="showComment = false">取消</el-button>
        <el-button type="primary" @click="submitComment">提交</el-button>
      </template>
    </el-dialog>

    <!-- Polaroid Lightbox -->
    <Transition name="lightbox-fade">
      <div v-if="lightboxVisible" class="lightbox-overlay" @click.self="closeLightbox">
        <div class="polaroid-wrapper">
          <!-- Navigation Buttons -->
          <button
            v-if="currentPhotoIndex > 0"
            class="preview-nav-close prev"
            @click="prevPhoto"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="15 18 9 12 15 6"></polyline>
            </svg>
          </button>

          <!-- Polaroid Frame -->
          <div class="polaroid-frame">
            <div class="annotation-stage">
              <img
                ref="polaroidImgRef"
                :src="currentPhotoUrl"
                :alt="currentPhotoData?.original_filename || `#${currentPhotoData?.display_id}`"
                class="polaroid-img"
                @load="onImageLoad"
              />
              <canvas
                ref="annotationCanvasRef"
                class="annotation-canvas"
                :class="{ active: annotationMode !== 'none' }"
                @pointerdown="startAnnotation"
                @pointermove="drawAnnotation"
                @pointerup="endAnnotation"
                @pointerleave="endAnnotation"
              />
            </div>
            <!-- Process State Label in Lightbox -->
            <div class="lightbox-process-label">
              {{ getProcessStateLabel(currentPhotoData?.process_state) }}
            </div>
            <div class="polaroid-caption">
              <div class="caption-line caption-filename">
                {{ currentPhotoData?.original_filename || `照片 #${currentPhotoData?.display_id}` }}
              </div>
              <div class="caption-line caption-id">
                #{{ String(currentPhotoData?.display_id).padStart(3, '0') }}
              </div>
              <div v-if="currentPhotoData?.version && currentPhotoData.version > 1" class="caption-line caption-version">
                版本 v{{ currentPhotoData.version }}
              </div>
              <div class="caption-line caption-project">
                {{ data?.project_name }}
              </div>
            </div>
          </div>

          <!-- Action Panel (Right Bottom) -->
          <div class="action-panel">
            <div class="action-panel-content">
              <el-input
                v-model="lightboxComment"
                type="textarea"
                :rows="3"
                placeholder="请输入您的修改意见..."
                :disabled="data?.is_expired"
              />
              <div class="action-buttons">
                <div class="annotation-tools">
                  <el-button size="small" :type="annotationMode === 'draw' ? 'primary' : 'default'" @click="setAnnotationMode('draw')">圈选</el-button>
                  <el-button size="small" :type="annotationMode === 'text' ? 'primary' : 'default'" @click="setAnnotationMode('text')">文字</el-button>
                  <el-button size="small" @click="clearAnnotation">清空</el-button>
                </div>
                <el-button
                  :type="currentPhotoData?.feedback?.is_confirmed ? 'success' : 'primary'"
                  :disabled="data?.is_expired"
                  @click="toggleConfirm"
                >
                  {{ currentPhotoData?.feedback?.is_confirmed ? '确认无需修改' : '无需修改' }}
                </el-button>
                <el-button
                  type="warning"
                  :disabled="data?.is_expired"
                  @click="submitRevisionFromLightbox"
                >
                  继续修改
                </el-button>
                <el-button
                  type="info"
                  :disabled="data?.is_expired"
                  @click="discardCurrentPhoto"
                >
                  弃用
                </el-button>
              </div>
            </div>
          </div>

          <button
            v-if="currentPhotoIndex < lightboxPhotos.length - 1"
            class="preview-nav-close next"
            @click="nextPhoto"
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="9 18 15 12 9 6"></polyline>
            </svg>
          </button>

          <!-- Close Button -->
          <button class="preview-nav-close close-btn" @click="closeLightbox">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18"></line>
              <line x1="6" y1="6" x2="18" y2="18"></line>
            </svg>
          </button>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../api/request'

const route = useRoute()
const token = route.params.token as string

const loading = ref(true)
const error = ref('')
const data = ref<any>(null)
const showComment = ref(false)
const commentText = ref('')
const currentPhoto = ref<any>(null)

const sidebarCollapsed = ref(false)
const activeCategories = ref<string[]>([])
const activeTarget = ref<string>('')
const targetRefs = ref<Map<string, HTMLElement>>(new Map())

// Lightbox state
const lightboxVisible = ref(false)
const lightboxPhotos = ref<any[]>([])
const currentPhotoIndex = ref(0)
const polaroidImgRef = ref<HTMLImageElement | null>(null)
const annotationCanvasRef = ref<HTMLCanvasElement | null>(null)
const lightboxComment = ref('')
const lightboxConfirmed = ref(false)
const markAsFinal = ref(false)
const annotationMode = ref<'none' | 'draw' | 'text'>('none')
const hasAnnotation = ref(false)
const drawing = ref(false)
const lastPoint = ref<{ x: number; y: number } | null>(null)

const currentPhotoData = computed(() => lightboxPhotos.value[currentPhotoIndex.value])
const currentPhotoUrl = computed(() => {
  if (!currentPhotoData.value) return ''
  // ✅ 只使用 thumbnail_path，严禁使用 original_path（客户页面安全加固）
  const thumbPath = currentPhotoData.value.thumbnail_path
  if (!thumbPath) {
    console.warn('照片缺少缩略图路径:', currentPhotoData.value.id)
    return ''
  }
  return `/storage/${thumbPath}`
})

// Watch photo change to sync state
watch(currentPhotoData, (newPhoto) => {
  if (newPhoto) {
    lightboxComment.value = newPhoto.feedback?.comment || ''
    lightboxConfirmed.value = newPhoto.feedback?.is_confirmed || false
    markAsFinal.value = false
    clearAnnotation()
  }
})

onMounted(async () => {
  await loadData()
  document.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})

async function loadData() {
  loading.value = true
  try {
    const result = await request.get(`/api/v1/reviews/${token}`)

    if (result.code === 200) {
      data.value = result.data
      // 默认展开所有分类
      activeCategories.value = data.value.categories.map((c: any) => c.category_type)
    } else {
      error.value = result.msg || '加载失败'
    }
  } catch (e: any) {
    if (e.message.includes('403')) {
      error.value = '分享已失效，请联系管理员'
    } else if (e.message.includes('404')) {
      error.value = '审核链接不存在或已失效'
    } else {
      error.value = '网络错误，请稍后重试'
    }
  } finally {
    loading.value = false
  }
}

function getTargetKey(categoryType: string, targetName: string) {
  return `${categoryType}-${targetName}`
}

function setTargetRef(categoryType: string, targetName: string, el: any) {
  if (el) {
    targetRefs.value.set(getTargetKey(categoryType, targetName), el)
  }
}

function scrollToTarget(categoryType: string, targetName: string) {
  const key = getTargetKey(categoryType, targetName)
  const el = targetRefs.value.get(key)
  if (el) {
    const contentArea = document.querySelector('.content-area')
    if (contentArea) {
      const offsetTop = el.offsetTop - 80 // 减去 header 高度
      contentArea.scrollTo({ top: offsetTop, behavior: 'smooth' })
    }
  }
  activeTarget.value = key
}

function handleScroll(e: Event) {
  const contentArea = e.target as HTMLElement
  const scrollTop = contentArea.scrollTop + 100 // 偏移量

  // 找到当前可见的第一个 target
  for (const [key, el] of targetRefs.value.entries()) {
    if (el.offsetTop >= scrollTop) {
      activeTarget.value = key
      break
    }
  }
}

function getCategoryTotalCount(cat: any) {
  return cat.targets.reduce((sum: number, t: any) => sum + t.total_count, 0)
}

function getProcessStateLabel(state: string) {
  const labels: Record<string, string> = {
    raw: '原图',
    retouched: '精修',
    final: '完成图',
  }
  return labels[state] || state
}

// Quick actions from thumbnail
async function quickConfirm(photo: any) {
  try {
    const result = await request.post(`/api/v1/reviews/${token}/feedback`, {
      photo_id: photo.id,
      is_confirmed: !photo.feedback?.is_confirmed,
      feedback_status: !photo.feedback?.is_confirmed ? 'approved' : 'revision',
      comment: photo.feedback?.comment || null,
      mark_as_final: false,
    })

    if (result.code === 200) {
      ElMessage.success(photo.feedback?.is_confirmed ? '已取消确认' : '已确认')
      await loadData()
    } else {
      ElMessage.error(result.msg || '提交失败')
    }
  } catch (e: any) {
    ElMessage.error('提交失败')
  }
}

function quickComment(photo: any) {
  currentPhoto.value = photo
  commentText.value = photo.feedback?.comment || ''
  showComment.value = true
}

function isDiscarded(photo: any) {
  return photo.feedback?.comment === '弃用'
}

async function discardPhoto(photo: any) {
  try {
    const result = await request.post(`/api/v1/reviews/${token}/feedback`, {
      photo_id: photo.id,
      is_confirmed: false,
      feedback_status: 'discarded',
      comment: '弃用',
      mark_as_final: false,
    })
    if (result.code === 200) {
      ElMessage.success('已标记弃用')
      await loadData()
    } else {
      ElMessage.error(result.msg || '提交失败')
    }
  } catch {
    ElMessage.error('提交失败')
  }
}

async function submitComment() {
  if (!commentText.value.trim()) {
    ElMessage.warning('请输入意见')
    return
  }

  try {
    const result = await request.post(`/api/v1/reviews/${token}/feedback`, {
      photo_id: currentPhoto.value.id,
      is_confirmed: currentPhoto.value.feedback?.is_confirmed || false,
      feedback_status: 'revision',
      comment: commentText.value,
      mark_as_final: false,
    })

    if (result.code === 200) {
      ElMessage.success('意见已提交')
      showComment.value = false
      await loadData()
    } else {
      ElMessage.error(result.msg || '提交失败')
    }
  } catch (e: any) {
    ElMessage.error('提交失败')
  }
}

// Lightbox functions
function openLightbox(photo: any, photos: any[], index: number) {
  lightboxPhotos.value = photos
  currentPhotoIndex.value = index
  lightboxComment.value = photo.feedback?.comment || ''
  lightboxConfirmed.value = photo.feedback?.is_confirmed || false
  markAsFinal.value = false
  annotationMode.value = 'none'
  hasAnnotation.value = false
  lightboxVisible.value = true
  document.body.style.overflow = 'hidden'
}

function closeLightbox() {
  lightboxVisible.value = false
  annotationMode.value = 'none'
  document.body.style.overflow = ''
}

function prevPhoto() {
  if (currentPhotoIndex.value > 0) {
    currentPhotoIndex.value--
  }
}

function nextPhoto() {
  if (currentPhotoIndex.value < lightboxPhotos.value.length - 1) {
    currentPhotoIndex.value++
  }
}

async function toggleConfirm() {
  const newConfirmedState = !lightboxConfirmed.value

  try {
    const result = await request.post(`/api/v1/reviews/${token}/feedback`, {
      photo_id: currentPhotoData.value.id,
      is_confirmed: newConfirmedState,
      feedback_status: newConfirmedState ? 'approved' : 'revision',
      comment: lightboxComment.value || null,
      annotation_image: null,
      mark_as_final: newConfirmedState && markAsFinal.value,
    })

    if (result.code === 200) {
      ElMessage.success(newConfirmedState ? '已确认' : '已取消确认')
      await loadData()
      // Update local state
      lightboxConfirmed.value = newConfirmedState
      if (!newConfirmedState) {
        markAsFinal.value = false
      }
      // Update photo in lightboxPhotos
      if (currentPhotoData.value) {
        currentPhotoData.value.feedback = {
          ...currentPhotoData.value.feedback,
          is_confirmed: newConfirmedState,
          comment: lightboxComment.value || null,
        }
      }
    } else {
      ElMessage.error(result.msg || '提交失败')
    }
  } catch (e: any) {
    ElMessage.error('提交失败')
  }
}

async function submitRevisionFromLightbox() {
  if (!lightboxComment.value.trim()) {
    ElMessage.warning('请填写修改内容')
    return
  }
  try {
    const result = await request.post(`/api/v1/reviews/${token}/feedback`, {
      photo_id: currentPhotoData.value.id,
      is_confirmed: false,
      feedback_status: 'revision',
      comment: lightboxComment.value,
      annotation_image: buildAnnotationImage(),
      mark_as_final: false,
    })
    if (result.code === 200) {
      ElMessage.success('修改意见已提交')
      await loadData()
    } else {
      ElMessage.error(result.msg || '提交失败')
    }
  } catch {
    ElMessage.error('提交失败')
  }
}

async function discardCurrentPhoto() {
  if (!currentPhotoData.value) return
  await discardPhoto(currentPhotoData.value)
}

function handleKeydown(e: KeyboardEvent) {
  if (!lightboxVisible.value) return

  if (e.key === 'Escape') {
    closeLightbox()
  } else if (e.key === 'ArrowLeft') {
    prevPhoto()
  } else if (e.key === 'ArrowRight') {
    nextPhoto()
  }
}

function onImageLoad() {
  resizeAnnotationCanvas()
}

function resizeAnnotationCanvas() {
  const img = polaroidImgRef.value
  const canvas = annotationCanvasRef.value
  if (!img || !canvas) return
  const rect = img.getBoundingClientRect()
  if (rect.width <= 0 || rect.height <= 0) return
  canvas.width = Math.round(rect.width)
  canvas.height = Math.round(rect.height)
  canvas.style.width = `${rect.width}px`
  canvas.style.height = `${rect.height}px`
  clearAnnotation()
}

function setAnnotationMode(mode: 'draw' | 'text') {
  annotationMode.value = annotationMode.value === mode ? 'none' : mode
  resizeAnnotationCanvasIfNeeded()
}

function resizeAnnotationCanvasIfNeeded() {
  const canvas = annotationCanvasRef.value
  if (!canvas || canvas.width === 0 || canvas.height === 0) resizeAnnotationCanvas()
}

function pointFromEvent(event: PointerEvent) {
  const canvas = annotationCanvasRef.value
  if (!canvas) return null
  const rect = canvas.getBoundingClientRect()
  return { x: event.clientX - rect.left, y: event.clientY - rect.top }
}

function startAnnotation(event: PointerEvent) {
  if (annotationMode.value === 'none') return
  resizeAnnotationCanvasIfNeeded()
  const point = pointFromEvent(event)
  if (!point) return
  if (annotationMode.value === 'text') {
    const text = window.prompt('请输入标注文字')
    if (!text) return
    const ctx = annotationCanvasRef.value?.getContext('2d')
    if (!ctx) return
    ctx.font = '18px sans-serif'
    ctx.lineWidth = 4
    ctx.strokeStyle = 'rgba(255,255,255,0.95)'
    ctx.fillStyle = '#ef4444'
    ctx.strokeText(text, point.x, point.y)
    ctx.fillText(text, point.x, point.y)
    hasAnnotation.value = true
    return
  }
  drawing.value = true
  lastPoint.value = point
  annotationCanvasRef.value?.setPointerCapture?.(event.pointerId)
}

function drawAnnotation(event: PointerEvent) {
  if (!drawing.value || annotationMode.value !== 'draw') return
  const point = pointFromEvent(event)
  const last = lastPoint.value
  const ctx = annotationCanvasRef.value?.getContext('2d')
  if (!point || !last || !ctx) return
  ctx.strokeStyle = '#ef4444'
  ctx.lineWidth = 4
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.beginPath()
  ctx.moveTo(last.x, last.y)
  ctx.lineTo(point.x, point.y)
  ctx.stroke()
  lastPoint.value = point
  hasAnnotation.value = true
}

function endAnnotation() {
  drawing.value = false
  lastPoint.value = null
}

function clearAnnotation() {
  const canvas = annotationCanvasRef.value
  const ctx = canvas?.getContext('2d')
  if (!canvas || !ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  hasAnnotation.value = false
}

function buildAnnotationImage(): string | null {
  if (!hasAnnotation.value) return null
  const img = polaroidImgRef.value
  const annotation = annotationCanvasRef.value
  if (!img || !annotation || annotation.width === 0 || annotation.height === 0) return null
  const canvas = document.createElement('canvas')
  canvas.width = annotation.width
  canvas.height = annotation.height
  const ctx = canvas.getContext('2d')
  if (!ctx) return null
  ctx.fillStyle = '#fff'
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height)
  ctx.drawImage(annotation, 0, 0)
  return canvas.toDataURL('image/png')
}
</script>

<style scoped>
/* 独立样式重置 - 避免受管理后台样式污染 */
.review-page,
.review-page *,
.review-page *::before,
.review-page *::after {
  box-sizing: border-box;
}

.review-page {
  min-height: 100vh;
  background: #f9fafb;
}

.loading-state,
.error-state {
  max-width: 1200px;
  margin: 0 auto;
  padding: 60px 24px;
}

.review-container {
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.header {
  background: white;
  border-bottom: 1px solid #e5e7eb;
  padding: 20px 32px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.project-info {
  display: flex;
  gap: 16px;
  align-items: center;
}

.cover {
  width: 60px;
  height: 60px;
  border-radius: 8px;
}

.info h1 {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 4px;
}

.info p {
  font-size: 13px;
  color: #6b7280;
  margin: 0;
}

.expired-badge {
  padding: 6px 12px;
  background: #fee2e2;
  color: #dc2626;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
}

.main-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Sidebar */
.sidebar {
  width: 280px;
  background: white;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
  flex-shrink: 0;
}

.sidebar.collapsed {
  width: 50px;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
  font-size: 14px;
}

.nav-collapse {
  flex: 1;
  overflow-y: auto;
  border: none;
}

.nav-collapse :deep(.el-collapse-item__header) {
  padding: 0 16px;
  height: 48px;
  border: none;
  background: white;
}

.nav-collapse :deep(.el-collapse-item__wrap) {
  border: none;
  background: #f9fafb;
}

.nav-collapse :deep(.el-collapse-item__content) {
  padding: 0;
}

.category-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
  padding-right: 12px;
}

.category-label {
  font-weight: 600;
  font-size: 14px;
  color: #111827;
}

.category-count {
  font-size: 12px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 2px 8px;
  border-radius: 10px;
}

.target-list {
  padding: 8px 0;
}

.target-item {
  padding: 12px 24px;
  cursor: pointer;
  transition: all 0.2s;
  border-left: 3px solid transparent;
}

.target-item:hover {
  background: white;
}

.target-item.active {
  background: #eff6ff;
  border-left-color: #3b82f6;
}

.target-name {
  font-size: 14px;
  font-weight: 500;
  color: #374151;
  margin-bottom: 4px;
}

.target-stats {
  font-size: 12px;
  color: #6b7280;
}

.target-stats .confirmed {
  color: #10b981;
  font-weight: 600;
}

.target-stats .separator {
  margin: 0 4px;
}

.target-stats .label {
  margin-left: 4px;
}

/* Content Area */
.content-area {
  flex: 1;
  overflow-y: auto;
  padding: 32px;
}

.category-section {
  margin-bottom: 48px;
}

.category-section:last-child {
  margin-bottom: 0;
}

.category-title {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 32px;
  padding-bottom: 12px;
  border-bottom: 2px solid #e5e7eb;
}

.target-group {
  margin-bottom: 40px;
  scroll-margin-top: 80px;
}

.target-group:last-child {
  margin-bottom: 0;
}

.target-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.target-title {
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  margin: 0;
}

.target-progress {
  font-size: 14px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 4px 12px;
  border-radius: 12px;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 20px;
}

.photo-item {
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #e5e7eb;
  background: white;
  transition: transform 0.2s, box-shadow 0.2s;
}

.photo-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.photo-item.discarded {
  opacity: 0.45;
  filter: grayscale(0.9);
}

.photo-img-wrapper {
  cursor: pointer;
  position: relative;
  overflow: hidden;
}

.photo-img {
  width: 100%;
  aspect-ratio: 1;
  transition: transform 0.3s ease;
}

.photo-img-wrapper:hover .photo-img {
  transform: scale(1.05);
}

/* Process State Badge (Thumbnail) */
.process-state-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.75);
  color: white;
  font-size: 11px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 20px;
  text-align: center;
  backdrop-filter: blur(4px);
  pointer-events: none;
}

.photo-info {
  padding: 8px 12px;
  display: flex;
  justify-content: center;
  align-items: center;
  border-bottom: 1px solid #f3f4f6;
  gap: 8px;
}

.filename {
  font-size: 12px;
  color: #6b7280;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

.version-badge {
  font-size: 11px;
  color: #3b82f6;
  background: #eff6ff;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.photo-actions {
  padding: 12px;
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.photo-actions .el-button {
  flex: 1 1 30%;
  margin-left: 0;
}

.comment-preview {
  padding: 0 12px 12px;
  font-size: 12px;
  color: #6b7280;
  border-top: 1px solid #f3f4f6;
  padding-top: 8px;
  margin-top: -4px;
}

/* Lightbox - Polaroid Style */
.lightbox-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.92);
  z-index: 9999;
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
  max-width: 90vw;
  max-height: 90vh;
}

.polaroid-frame {
  background: white;
  padding: 16px 16px 0 16px;
  border-radius: 8px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(0, 0, 0, 0.05);
  max-width: 85vw;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
  animation: polaroid-appear 0.3s ease-out;
}

@keyframes polaroid-appear {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.polaroid-img {
  max-width: 100%;
  max-height: calc(85vh - 140px);
  object-fit: contain;
  display: block;
  border-radius: 4px;
}

.annotation-stage {
  position: relative;
  display: inline-flex;
  max-width: 100%;
  max-height: calc(85vh - 140px);
}

.annotation-canvas {
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: 4px;
}

.annotation-canvas.active {
  pointer-events: auto;
  cursor: crosshair;
}

/* Process State Label in Lightbox */
.lightbox-process-label {
  position: absolute;
  bottom: 16px;
  right: 16px;
  background: rgba(0, 0, 0, 0.85);
  color: white;
  font-size: 18px;
  font-weight: 800;
  padding: 8px 20px;
  border-radius: 6px;
  text-align: center;
  backdrop-filter: blur(8px);
  pointer-events: none;
}

.polaroid-caption {
  padding: 20px 16px 24px;
  text-align: center;
}

.caption-line {
  margin: 4px 0;
}

.caption-filename {
  font-weight: 800;
  color: #000;
  font-size: 18px;
  margin-bottom: 8px;
}

.caption-id {
  color: #6b7280;
  font-size: 14px;
  font-family: 'Courier New', monospace;
}

.caption-version {
  color: #3b82f6;
  font-size: 12px;
  font-weight: 600;
}

.caption-project {
  color: #9ca3af;
  font-size: 11px;
  margin-top: 8px;
}

/* Navigation Buttons */
.preview-nav-close {
  position: absolute;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(0, 0, 0, 0.08);
  border-radius: 50%;
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
  color: #374151;
  opacity: 0.7;
}

.preview-nav-close:hover {
  opacity: 1;
  transform: scale(1.08);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.preview-nav-close.prev {
  left: -70px;
}

.preview-nav-close.next {
  right: -70px;
}

.preview-nav-close.close-btn {
  position: fixed;
  top: 20px;
  right: 20px;
  width: 44px;
  height: 44px;
}

/* Action Panel (Right Bottom) */
.action-panel {
  position: absolute;
  bottom: 16px;
  left: calc(100% + 20px);
  width: 320px;
  background: white;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
  border: 1px solid rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.action-panel-content {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.action-panel :deep(.el-textarea__inner) {
  border-radius: 8px;
  font-size: 13px;
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.annotation-tools {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.annotation-tools .el-button {
  width: 100%;
  margin-left: 0;
}

.action-buttons .el-button {
  width: 100%;
  border-radius: 8px;
  font-weight: 500;
}

.action-buttons .el-checkbox {
  margin-left: 4px;
  font-size: 13px;
  color: #374151;
}

.action-buttons :deep(.el-checkbox__label) {
  font-size: 13px;
  color: #374151;
}

.action-buttons :deep(.el-checkbox__input.is-disabled + .el-checkbox__label) {
  color: #9ca3af;
}

/* Lightbox Transitions */
.lightbox-fade-enter-active,
.lightbox-fade-leave-active {
  transition: opacity 0.3s ease;
}

.lightbox-fade-enter-from,
.lightbox-fade-leave-to {
  opacity: 0;
}

/* Responsive */
@media (max-width: 768px) {
  .sidebar {
    width: 240px;
  }

  .sidebar.collapsed {
    width: 0;
    border: none;
  }

  .content-area {
    padding: 20px;
  }

  .photo-grid {
    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
    gap: 12px;
  }

  .lightbox-overlay {
    padding: 20px;
  }

  .polaroid-frame {
    padding: 12px 12px 0 12px;
    max-width: 95vw;
    max-height: 90vh;
  }

  .polaroid-img {
    max-height: calc(90vh - 120px);
  }

  .polaroid-caption {
    padding: 16px 12px 20px;
  }

  .caption-filename {
    font-size: 16px;
  }

  .caption-id {
    font-size: 12px;
  }

  .preview-nav-close.prev {
    left: -60px;
  }

  .preview-nav-close.next {
    right: -60px;
  }

  .preview-nav-close {
    width: 44px;
    height: 44px;
  }

  .preview-nav-close.close-btn {
    width: 40px;
    height: 40px;
  }

  .action-panel {
    position: static;
    width: 100%;
    margin-top: 16px;
    left: auto;
    bottom: auto;
  }

  .lightbox-process-label {
    font-size: 14px;
    padding: 6px 14px;
    bottom: 12px;
    right: 12px;
  }
}
</style>
