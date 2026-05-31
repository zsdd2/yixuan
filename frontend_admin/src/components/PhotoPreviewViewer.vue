<template>
  <Teleport to="body">
    <div v-if="modelValue && currentPhoto" class="preview-mask" @click.self="close">
      <div class="polaroid-wrapper">
        <div class="polaroid-frame">
          <img :src="currentPreviewUrl" class="polaroid-img" @error="onImageError" />
          <div class="polaroid-caption">
            <div class="caption-line">{{ currentPhoto.target_name || currentPhoto.original_filename || '未命名图片' }}</div>
            <div class="caption-line caption-filename">{{ currentPhoto.original_filename || '无文件名' }}</div>
            <div class="caption-line caption-id">#{{ String(currentPhoto.display_id || 0).padStart(3, '0') }}</div>
            <div v-if="currentPhoto.project_name" class="caption-line caption-project">{{ currentPhoto.project_name }}</div>
          </div>
        </div>

        <button type="button" class="polaroid-side-btn polaroid-download-btn" title="下载原图" @click.stop="downloadCurrent">
          <span class="download-icon">↓</span>
        </button>
        <button
          type="button"
          v-if="currentPhoto.thumbnail_path"
          class="polaroid-side-btn polaroid-zoom-btn"
          :class="{ active: showOriginal }"
          title="查看原图/缩略图"
          @click.stop="toggleOriginal"
        >
          <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <circle cx="11" cy="11" r="8" stroke-width="2"/>
            <path d="M21 21l-4.35-4.35" stroke-width="2" stroke-linecap="round"/>
            <path v-if="!showOriginal" d="M11 8v6M8 11h6" stroke-width="2" stroke-linecap="round"/>
            <path v-else d="M8 11h6" stroke-width="2" stroke-linecap="round"/>
          </svg>
        </button>

        <button type="button" v-if="currentIndex > 0" class="preview-nav-close prev" @click.stop="goPrev">‹</button>
        <button type="button" v-if="currentIndex < photos.length - 1" class="preview-nav-close next" @click.stop="goNext">›</button>
      </div>
      <button type="button" class="preview-close" @click="close">×</button>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { computed, ref, watch, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { downloadStorageFile } from '../composables/usePhotoDownload'

export interface PreviewPhoto {
  id: number
  display_id: number | string
  original_path: string
  original_filename?: string | null
  thumbnail_path?: string | null
  target_name?: string | null
  project_name?: string | null
}

const props = defineProps<{
  modelValue: boolean
  photos: PreviewPhoto[]
  index: number
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'update:index': [value: number]
}>()

const showOriginal = ref(false)

const currentIndex = computed(() => Math.min(Math.max(props.index, 0), Math.max(props.photos.length - 1, 0)))
const currentPhoto = computed(() => props.photos[currentIndex.value])
const currentPreviewUrl = computed(() => {
  const photo = currentPhoto.value
  if (!photo) return ''
  const path = showOriginal.value ? photo.original_path : (photo.thumbnail_path || photo.original_path)
  return `/storage/${path}`
})

function close() {
  emit('update:modelValue', false)
}

function goPrev() {
  if (currentIndex.value > 0) emit('update:index', currentIndex.value - 1)
}

function goNext() {
  if (currentIndex.value < props.photos.length - 1) emit('update:index', currentIndex.value + 1)
}

function toggleOriginal() {
  showOriginal.value = !showOriginal.value
}

function downloadCurrent() {
  const photo = currentPhoto.value
  if (!photo) return
  const path = showOriginal.value ? photo.original_path : (photo.thumbnail_path || photo.original_path)
  const filename = showOriginal.value
    ? (photo.original_filename || `photo_${photo.display_id}`)
    : `thumb_${photo.display_id}`
  downloadStorageFile(path, filename)
}

function onImageError() {
  ElMessage.error('图片加载失败')
}

function onKeydown(e: KeyboardEvent) {
  if (!props.modelValue) return
  if (e.key === 'Escape') close()
  else if (e.key === 'ArrowLeft') goPrev()
  else if (e.key === 'ArrowRight') goNext()
}

watch(() => props.modelValue, (visible) => {
  showOriginal.value = false
  if (visible) window.addEventListener('keydown', onKeydown)
  else window.removeEventListener('keydown', onKeydown)
})

watch(() => props.index, () => {
  showOriginal.value = false
})

onUnmounted(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.preview-mask {
  position: fixed;
  inset: 0;
  z-index: 9999;
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
  background: #fff;
  padding: 16px 16px 0;
  border-radius: 8px;
  border: 1px solid rgba(0, 0, 0, 0.05);
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

.polaroid-caption {
  padding: 20px 16px 24px;
  text-align: center;
  background: #fff;
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
  font-family: "Courier New", monospace;
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
  background: #fff;
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

.polaroid-side-btn:hover {
  background: #f9fafb;
  transform: translateY(1px);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.15);
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
  top: 86px;
}

.polaroid-zoom-btn.active {
  background: #3b82f6;
  color: #fff;
  border-color: #3b82f6;
}

.preview-close {
  position: absolute;
  top: 20px;
  right: 24px;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
  font-size: 32px;
  cursor: pointer;
  opacity: 0.85;
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-close:hover {
  opacity: 1;
  background: rgba(255, 255, 255, 0.25);
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
  color: #fff;
  font-size: 32px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.75;
}

.preview-nav-close:hover {
  background: rgba(255, 255, 255, 0.25);
  opacity: 1;
}

.preview-nav-close.prev { left: -70px; }
.preview-nav-close.next { right: -70px; }

@media (max-width: 768px) {
  .polaroid-frame {
    max-width: 95vw;
    max-height: 90vh;
  }
  .polaroid-side-btn {
    left: auto;
    right: 12px;
    width: 46px;
    height: 46px;
  }
  .polaroid-download-btn { top: 12px; }
  .polaroid-zoom-btn { top: 66px; }
  .preview-nav-close.prev { left: -58px; }
  .preview-nav-close.next { right: -58px; }
}
</style>
