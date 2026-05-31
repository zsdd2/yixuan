<template>
  <div class="portfolio-page">
    <!-- 页头 -->
    <div class="portfolio-header">
      <h1 class="portfolio-title">作品中心</h1>
      <span class="portfolio-count">{{ total }} 张作品</span>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <div class="stage-switcher">
        <button
          v-for="s in stages"
          :key="s.value"
          class="stage-btn"
          :class="{ active: processState === s.value }"
          @click="processState = s.value; resetAndFetch()"
        >{{ s.label }}</button>
      </div>
      <el-select v-model="filterShootingType" placeholder="拍摄类型" clearable size="default" style="width:140px" @change="resetAndFetch">
        <el-option v-for="t in filters.shooting_types" :key="t" :label="t" :value="t" />
      </el-select>
      <el-select v-model="filterCategoryType" placeholder="场景风格" clearable size="default" style="width:130px" @change="resetAndFetch">
        <el-option label="白图" value="white" />
        <el-option label="场景" value="scene" />
      </el-select>
      <el-select v-model="filterProjectId" placeholder="项目" clearable filterable size="default" style="width:180px" @change="onProjectChange">
        <el-option v-for="p in filters.projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-select v-model="filterTargetName" placeholder="视角筛选" clearable filterable size="default" style="width:150px" @change="resetAndFetch">
        <el-option v-for="t in availableTargetNames" :key="t" :label="t" :value="t" />
      </el-select>
      <el-select v-model="filterClientId" placeholder="客户" clearable filterable size="default" style="width:150px" @change="resetAndFetch">
        <el-option v-for="c in filters.clients" :key="c.id" :label="c.name" :value="c.id" />
      </el-select>
      <el-select v-model="filterPortfolioTagId" placeholder="作品标签" clearable filterable size="default" style="width:150px" @change="resetAndFetch">
        <el-option v-for="tag in filters.system_tags" :key="tag.id" :label="tag.name" :value="tag.id" />
      </el-select>
    </div>

    <!-- 网格布局 -->
    <div v-loading="loading && photos.length === 0" class="portfolio-grid">
      <div v-for="(photo, idx) in photos" :key="photo.id" class="grid-item">
        <div class="card">
          <div class="card-image-wrap" @click="openPreview(idx)">
            <img
              :src="getStorageUrl(photo.thumbnail_path || photo.original_path)"
              :alt="photo.project_name"
              loading="lazy"
              class="card-image"
              @load="($event.target as HTMLImageElement).classList.add('loaded')"
            />
          </div>
          <div class="card-info">
            <div class="info-line-1">{{ photo.target_name || '未分配' }}</div>
            <div class="info-line-2">#{{ String(photo.display_id).padStart(3, '0') }}</div>
            <div class="info-line-3" :title="photo.original_filename || ''">{{ photo.original_filename || '—' }}</div>
            <div class="info-line-4">{{ photo.project_name }}</div>
            <div class="portfolio-card-tags">
              <span v-for="tag in portfolioTagNames(photo.portfolio_tag_ids)" :key="tag" class="portfolio-card-tag">{{ tag }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <el-empty v-if="!loading && photos.length === 0" description="暂无作品" :image-size="80" />

    <!-- 加载更多触发器 -->
    <div ref="sentinelRef" class="load-sentinel">
      <span v-if="loadingMore" class="loading-text">加载中...</span>
      <span v-else-if="noMore && photos.length > 0" class="loading-text">已展示全部作品</span>
    </div>

    <!-- 大图预览遮罩 - 拍立得相框风格 -->
    <Teleport to="body">
      <div v-if="previewVisible" class="preview-mask" @click.self="closePreview">
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
              <div class="caption-line">{{ photos[previewIdx]?.target_name || '未分配' }}</div>
              <div class="caption-line caption-filename">{{ photos[previewIdx]?.original_filename || '—' }}</div>
              <div class="caption-line caption-id">#{{ String(photos[previewIdx]?.display_id || '000').padStart(3, '0') }}</div>
              <div class="caption-line caption-project">{{ photos[previewIdx]?.project_name }}</div>
            </div>
          </div>
          <!-- 右侧按钮组（下载 + 放大镜） -->
          <button
            class="polaroid-side-btn polaroid-download-btn"
            @click="downloadOriginal(photos[previewIdx])"
            title="下载原图"
          >
            <span class="download-icon">⬇</span>
          </button>
          <button
            v-if="photos[previewIdx]?.thumbnail_path"
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
          <button v-if="previewIdx > 0" class="preview-nav-close prev" @click="previewIdx--">‹</button>
          <button v-if="previewIdx < photos.length - 1" class="preview-nav-close next" @click="previewIdx++">›</button>
        </div>
        <!-- 关闭按钮 -->
        <button class="preview-close" @click="closePreview">✕</button>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../api/request'
import { downloadStorageFile } from '../composables/usePhotoDownload'

const router = useRouter()

interface PortfolioPhoto {
  id: number
  project_id: number
  project_name: string
  display_id: string
  client_name: string
  shooting_type: string | null
  target_name: string | null
  category_type: string | null
  thumbnail_path: string | null
  original_path: string
  original_filename: string | null
  process_state: string
  portfolio_tag_ids: number[]
  shot_at: string | null
  created_at: string
}

const stages = [
  { value: 'final', label: '成片' },
  { value: 'retouched', label: '精修' },
  { value: 'raw', label: '原图' },
]

const photos = ref<PortfolioPhoto[]>([])
const total = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const noMore = ref(false)
const skip = ref(0)
const LIMIT = 30

const processState = ref('final')
const filterShootingType = ref<string>('')
const filterCategoryType = ref<string>('')
const filterProjectId = ref<number | null>(null)
const filterTargetName = ref<string>('')
const filterClientId = ref<number | null>(null)
const filterPortfolioTagId = ref<number | null>(null)

const filters = reactive({
  shooting_types: [] as string[],
  clients: [] as { id: number; name: string }[],
  projects: [] as { id: number; name: string }[],
  target_names: [] as string[],
  system_tags: [] as { id: number; name: string; color: string }[],
})

// 动态计算可用的视角名称列表
const availableTargetNames = computed(() => {
  if (filterProjectId.value) {
    // 如果选择了项目，显示该项目的特定目标名称
    return filters.target_names.filter(name => name) // 过滤空值
  } else {
    // 如果没有选择项目，显示系统通用目标名称（从 filters 获取）
    return filters.target_names
  }
})

const sentinelRef = ref<HTMLElement>()
let observer: IntersectionObserver | null = null

const polaroidImgRef = ref<HTMLImageElement | null>(null)
const polaroidFrameRef = ref<HTMLDivElement | null>(null)
const downloadButtonStyle = ref<Record<string, string>>({})

const showOriginal = ref(false)
const loadingOriginal = ref(false)

const currentPreviewUrl = computed(() => {
  const photo = photos.value[previewIdx.value]
  if (!photo) return ''

  if (showOriginal.value) {
    return `/storage/${photo.original_path}`
  }

  const thumbPath = photo.thumbnail_path || photo.original_path
  return `/storage/${thumbPath}`
})

function getStorageUrl(path: string): string {
  return `/storage/${path}`
}

function goToProject(projectId: number) {
  router.push({ name: 'ProjectDetail', params: { id: projectId } })
}

function portfolioTagNames(ids: number[]) {
  const map = new Map(filters.system_tags.map(tag => [tag.id, tag.name]))
  return (ids || []).map(id => map.get(id)).filter(Boolean) as string[]
}

async function fetchFilters() {
  try {
    const [d, tagData] = await Promise.all([
      request.get('/api/v1/photos/portfolio/filters'),
      request.get('/api/v1/settings/tags'),
    ])
    filters.shooting_types = d.shooting_types
    filters.clients = d.clients
    filters.projects = d.projects
    filters.target_names = d.target_names || []
    filters.system_tags = tagData.items || []
  } catch {}
}

// 当项目改变时，加载该项目的子项目列表
async function onProjectChange() {
  filterTargetName.value = ''

  if (filterProjectId.value) {
    try {
      const d = await request.get(`/api/v1/projects/${filterProjectId.value}/targets`)
      filters.target_names = d.items.map((t: any) => t.name)
    } catch {}
  } else {
    // 项目清空时，重新加载全局目标名称
    await fetchFilters()
  }

  resetAndFetch()
}

function buildQuery(): string {
  const params = new URLSearchParams()
  params.set('skip', String(skip.value))
  params.set('limit', String(LIMIT))
  params.set('process_state', processState.value)
  if (filterShootingType.value) params.set('shooting_type', filterShootingType.value)
  if (filterCategoryType.value) params.set('category_type', filterCategoryType.value)
  if (filterProjectId.value) params.set('project_id', String(filterProjectId.value))
  if (filterTargetName.value) params.set('target_name', filterTargetName.value)
  if (filterClientId.value) params.set('client_id', String(filterClientId.value))
  if (filterPortfolioTagId.value) params.set('portfolio_tag_id', String(filterPortfolioTagId.value))
  return params.toString()
}

async function fetchPhotos(append = false) {
  if (!append) { loading.value = true } else { loadingMore.value = true }
  try {
    const d = await request.get(`/api/v1/photos/portfolio?${buildQuery()}`)
    total.value = d.total
    if (append) {
      photos.value.push(...d.items)
    } else {
      photos.value = d.items
    }
    noMore.value = photos.value.length >= d.total
  } catch {} finally {
    loading.value = false
    loadingMore.value = false
  }
}

function resetAndFetch() {
  skip.value = 0
  noMore.value = false
  fetchPhotos(false)
}

function loadMore() {
  if (loadingMore.value || noMore.value) return
  skip.value = photos.value.length
  fetchPhotos(true)
}

function setupObserver() {
  if (!sentinelRef.value) return
  observer = new IntersectionObserver(
    (entries) => { if (entries[0].isIntersecting) loadMore() },
    { rootMargin: '200px' }
  )
  observer.observe(sentinelRef.value)
}

onMounted(async () => {
  await Promise.all([fetchFilters(), fetchPhotos()])
  await nextTick()
  setupObserver()
})

onUnmounted(() => { observer?.disconnect() })

// ── 大图预览 ──
const previewVisible = ref(false)
const previewIdx = ref(0)

function openPreview(idx: number) {
  previewIdx.value = idx
  showOriginal.value = false // 默认显示缩略图
  loadingOriginal.value = false
  previewVisible.value = true
}

function closePreview() {
  previewVisible.value = false
}

function onImageLoad() {
  // 动态计算图片比例并应用到下载按钮
  if (!polaroidImgRef.value) return

  const img = polaroidImgRef.value
  const aspectRatio = img.naturalWidth / img.naturalHeight

  // 按钮高度固定为 44px，宽度根据比例计算
  const buttonHeight = 44
  const buttonWidth = Math.round(buttonHeight * aspectRatio)

  downloadButtonStyle.value = {
    width: `${buttonWidth}px`,
    height: `${buttonHeight}px`,
  }
}

function toggleOriginal() {
  if (!photos.value[previewIdx.value]?.thumbnail_path) return

  if (showOriginal.value) {
    // 切换回缩略图
    showOriginal.value = false
    loadingOriginal.value = false
  } else {
    // 加载原图
    loadingOriginal.value = true
    showOriginal.value = true

    // 预加载原图
    const photo = photos.value[previewIdx.value]
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

function onPreviewKey(e: KeyboardEvent) {
  if (!previewVisible.value) return
  if (e.key === 'Escape') closePreview()
  else if (e.key === 'ArrowLeft' && previewIdx.value > 0) previewIdx.value--
  else if (e.key === 'ArrowRight' && previewIdx.value < photos.value.length - 1) previewIdx.value++
}

watch(previewIdx, () => {
  showOriginal.value = false
  loadingOriginal.value = false
})

watch(previewVisible, (v) => {
  if (v) window.addEventListener('keydown', onPreviewKey)
  else window.removeEventListener('keydown', onPreviewKey)
})

function downloadOriginal(photo: PortfolioPhoto | undefined) {
  if (!photo) return
  downloadStorageFile(photo.original_path, photo.original_filename || `photo_${photo.display_id}`)
}
</script>

<style scoped>
.portfolio-page {
  padding: 24px 32px;
  min-height: 100vh;
  background: #f9fafb;
}

.portfolio-header {
  display: flex;
  align-items: baseline;
  gap: 16px;
  margin-bottom: 20px;
}
.portfolio-title {
  font-size: 26px;
  font-weight: 700;
  color: #1a1a2e;
  letter-spacing: -0.5px;
}
.portfolio-count {
  font-size: 14px;
  color: #909399;
}

/* ── 筛选栏 ── */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}
.stage-switcher {
  display: flex;
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0,0,0,0.06);
}
.stage-btn {
  padding: 7px 18px;
  border: none;
  background: transparent;
  font-size: 13px;
  color: #606266;
  cursor: pointer;
  transition: all 0.15s;
}
.stage-btn:hover { background: #f5f7fa; }
.stage-btn.active {
  background: #2563eb;
  color: #fff;
  font-weight: 600;
}

/* ── 网格布局 ── */
.portfolio-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 12px;
}

@media (max-width: 1600px) { .portfolio-grid { grid-template-columns: repeat(6, 1fr); } }
@media (max-width: 1200px) { .portfolio-grid { grid-template-columns: repeat(4, 1fr); } }
@media (max-width: 800px) { .portfolio-grid { grid-template-columns: repeat(3, 1fr); } }

/* ── 卡片 ── */
.card {
  border-radius: 14px;
  overflow: hidden;
  background: #fff;
  box-shadow: 0 2px 10px rgba(0,0,0,0.08);
  transition: box-shadow 0.3s, transform 0.3s;
}
.card:hover {
  box-shadow: 0 6px 20px rgba(0,0,0,0.15);
  transform: translateY(-3px);
}

.card-image-wrap {
  position: relative;
  overflow: hidden;
  cursor: pointer;
  aspect-ratio: 4 / 3;
}
.card-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  opacity: 0;
  transition: opacity 0.3s;
}
.card-image.loaded { opacity: 1; }

/* 拍立得卡片信息区 - 四行居中布局 */
.card-info {
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

.portfolio-card-tags {
  min-height: 22px;
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 5px;
  margin-top: 8px;
}

.portfolio-card-tag {
  max-width: 100%;
  border-radius: 999px;
  background: #eef4ff;
  color: #2563eb;
  padding: 2px 7px;
  font-size: 11px;
  line-height: 16px;
}

/* ── 加载 ── */
.load-sentinel {
  text-align: center;
  padding: 24px 0;
}
.loading-text {
  font-size: 13px;
  color: #c0c4cc;
}

/* ── 大图预览 - 拍立得相框风格 ── */
.preview-mask {
  position: fixed; inset: 0; z-index: 9999;
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

/* 右侧按钮组 - 统一样式，垂直排列 */
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
  .polaroid-download-rect {
    top: 12px; /* 移动端对齐图片上边缘（相框 padding 为 12px） */
    /* 移动端按钮高度缩小至 48px（放大1/3后的移动端尺寸） */
    height: 48px;
    font-size: 20px;
  }
  .preview-nav-close.prev {
    left: -60px;
  }
  .preview-nav-close.next {
    right: -60px;
  }
}
</style>
