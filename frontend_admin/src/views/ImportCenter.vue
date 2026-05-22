<template>
  <div class="import-center">
    <!-- 顶部 -->
    <div class="top-bar">
      <el-button @click="goBack" :icon="ArrowLeft">返回项目</el-button>
      <span class="page-title">导入中心</span>
      <span class="project-id">项目 #{{ projectId }}</span>
    </div>

    <!-- Zone A: 导入控制 (紧凑高度) -->
    <div class="import-zone">
      <div class="import-card compact">
        <div class="card-header-row">
          <h3 class="zone-title">图片导入</h3>
          <el-segmented v-model="importMode" :options="importModeOptions" size="default" />
        </div>

        <!-- 本地上传模式 -->
          <div v-if="importMode === 'upload'" class="compact-body">
          <div class="mode-header">
            <span class="mode-label">处理阶段:</span>
            <el-radio-group v-model="uploadProcessState" size="small">
              <el-radio value="raw">原图</el-radio>
              <el-radio value="retouched">精修</el-radio>
              <el-radio value="final">完成</el-radio>
            </el-radio-group>
            <span class="mode-label">拍摄日期:</span>
            <el-date-picker v-model="uploadShotDate" type="date" value-format="YYYY-MM-DD" placeholder="自动识别" size="small" style="width: 140px" clearable />
          </div>
          <el-upload
            ref="uploadRef"
            drag
            multiple
            :auto-upload="false"
            :action="`/api/v1/projects/${projectId}/photos/upload`"
            name="file"
            :data="uploadFormData"
            accept=".jpg,.jpeg,.png,.tif,.tiff,.webp,.heic"
            :on-change="onFileChange"
            :on-success="onSingleUploadSuccess"
            :on-error="onSingleUploadError"
            class="import-upload"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽或 <em>点击选择</em></div>
          </el-upload>
          <div class="tag-select-row">
            <span class="tag-label">标签:</span>
            <el-select v-model="uploadTagIds" multiple size="small" placeholder="选择或新建标签" style="flex:1" filterable allow-create default-first-option>
              <el-option v-for="t in allTags" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
          </div>
          <div v-if="pendingFileCount > 0" class="upload-confirm">
            <span class="pending-hint">已选 {{ pendingFileCount }} 个文件</span>
            <el-button type="primary" size="small" :loading="uploading" @click="submitUpload">确认上传</el-button>
          </div>
          <el-progress v-if="uploading" :percentage="uploadTotal > 0 ? Math.round((uploadDone / uploadTotal) * 100) : 0" :stroke-width="4" :status="uploadDone === uploadTotal && uploadTotal > 0 ? 'success' : undefined" style="margin-top:4px" />
        </div>

        <!-- NAS 扫描模式 -->
        <div v-else class="compact-body">
          <div class="mode-header">
            <span class="mode-label">处理阶段:</span>
            <el-radio-group v-model="nasProcessState" size="small">
              <el-radio value="raw">原图</el-radio>
              <el-radio value="retouched">精修</el-radio>
              <el-radio value="final">完成</el-radio>
            </el-radio-group>
            <span class="mode-label">拍摄日期:</span>
            <el-date-picker v-model="nasShotDate" type="date" value-format="YYYY-MM-DD" placeholder="自动识别" size="small" style="width: 140px" clearable />
          </div>
          <div class="nas-row">
            <el-input v-model="nasSelectedPath" placeholder="点击图标选择文件夹..." readonly size="small">
              <template #suffix>
                <el-icon class="nas-trigger" @click="showNasPicker = true"><FolderOpened /></el-icon>
              </template>
            </el-input>
            <el-button type="success" size="small" :loading="scanning" :disabled="!nasSelectedPath" @click="startNasScan">扫描入库</el-button>
          </div>
          <div class="tag-select-row">
            <span class="tag-label">标签:</span>
            <el-select v-model="nasTagIds" multiple size="small" placeholder="选择或新建标签" style="flex:1" filterable allow-create default-first-option>
              <el-option v-for="t in allTags" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
          </div>
          <div v-if="scanTaskId" class="scan-progress">
            <el-progress :percentage="scanTotal > 0 ? Math.round((scanProcessed / scanTotal) * 100) : 0" :stroke-width="4" :status="scanStatus === 'done' ? 'success' : scanStatus === 'failed' ? 'exception' : undefined" />
            <span class="scan-text">{{ scanStatusText }}</span>
          </div>
        </div>
      </div>
    </div>

    <NASPathPicker v-model="showNasPicker" @select="onNasPathSelected" />

    <!-- Zone B: 项目底片 -->
    <div class="pool-zone">
      <div class="pool-header">
        <h3 class="zone-title">项目底片 <span class="pool-total">({{ photoTotal }} 张)</span></h3>
        <div class="pool-actions">
          <el-button size="small" @click="showTagManager = true">标签管理</el-button>
          <el-button size="small" :disabled="selectedIds.size === 0" @click="showBatchTag = true">
            🏷️ 批量标签 ({{ selectedIds.size }})
          </el-button>
          <el-button type="warning" size="small" @click="openQuickSort">快速分拣</el-button>
          <el-button type="danger" size="small" :disabled="selectedIds.size === 0" :loading="removing" @click="removeFromProject">移除出项目 ({{ selectedIds.size }})</el-button>
        </div>
      </div>

      <!-- 筛选栏 -->
      <div class="filter-bar">
        <div class="filter-group">
          <span class="filter-label">拍摄日期:</span>
          <el-select v-model="filterShotDates" multiple size="small" placeholder="全部日期" clearable style="min-width:200px" @change="onFilterChange">
            <el-option v-for="d in shotDateOptions" :key="d.date" :label="d.label" :value="d.date" />
          </el-select>
        </div>
        <div class="filter-group">
          <span class="filter-label">标签:</span>
          <el-select v-model="filterTagId" size="small" placeholder="全部标签" clearable style="width:130px" @change="onFilterChange">
            <el-option v-for="t in allTags" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </div>
        <el-checkbox v-model="filterUnassigned" size="small" @change="onFilterChange">未分类</el-checkbox>
        <el-button size="small" @click="selectAll" :disabled="photos.length === 0">全选</el-button>
        <el-button size="small" @click="selectedIds.clear()" :disabled="selectedIds.size === 0">取消</el-button>
        <div style="flex:1" />
        <el-pagination v-model:current-page="poolPage" :page-size="poolPageSize" :total="photoTotal" layout="total, prev, pager, next" small />
      </div>

      <!-- 图片网格 8列 -->
      <div class="photo-grid-8" v-loading="loadingPhotos">
        <div v-for="photo in photos" :key="photo.id" :class="['photo-card-sm', { selected: selectedIds.has(photo.id) }]" @click="toggleSelect(photo.id)">
          <div class="card-checkbox">
            <el-icon v-if="selectedIds.has(photo.id)" class="checked"><Select /></el-icon>
            <div v-else class="unchecked" />
          </div>
          <el-image :src="getThumbnailUrl(photo)" fit="cover" lazy class="card-img">
            <template #error><div class="card-img-error"><el-icon><PictureFilled /></el-icon></div></template>
          </el-image>
          <span class="card-id">#{{ String(photo.display_id).padStart(3, '0') }}</span>
          <span v-if="photo.shot_at" class="card-shot-at">{{ formatShotAt(photo.shot_at) }}</span>
          <span class="card-ps" :class="'ps-' + photo.process_state">{{ psLabel[photo.process_state] || '' }}</span>
          <span v-if="photo.target_id" class="card-target">{{ getTargetName(photo.target_id) }}</span>
          <div v-if="photo.tag_ids && photo.tag_ids.length > 0" class="card-tags">
            <span v-for="tid in photo.tag_ids.slice(0, 2)" :key="tid" class="mini-tag" :style="{ background: getTagColor(tid) }">{{ getTagName(tid) }}</span>
          </div>
        </div>
        <el-empty v-if="!loadingPhotos && photos.length === 0" description="暂无照片" :image-size="60" />
      </div>
    </div>

    <!-- ==================== 快速分拣穿梭台 ==================== -->
    <el-dialog v-model="showQuickSort" title="快速分拣" width="62%" top="5vh" :close-on-click-modal="false" destroy-on-close class="qs-dialog" @open="onQsOpen">
      <div class="qs-shuttle">
        <!-- 左栏: 照片池 -->
        <div class="qs-panel qs-left">
          <div class="qs-panel-header">
            <el-segmented v-model="qsPoolMode" :options="qsPoolOptions" size="small" />
            <span class="qs-panel-count">{{ qsFilteredPhotos.length }} 张</span>
          </div>

          <!-- 筛选器区域 -->
          <div class="qs-filters">
            <el-select v-model="qsFilterProcessState" placeholder="处理阶段" clearable size="small" style="width: 110px" @change="loadQsPhotos">
              <el-option label="原图" value="raw" />
              <el-option label="精修" value="retouched" />
              <el-option label="完成" value="final" />
            </el-select>

            <el-select v-model="qsFilterShotDate" placeholder="拍摄日期" clearable size="small" style="width: 130px" @change="loadQsPhotos">
              <el-option v-for="item in qsShotDates" :key="item.date" :label="item.label" :value="item.date" />
            </el-select>

            <el-select v-model="qsFilterTagId" placeholder="标签" clearable size="small" style="width: 110px" @change="loadQsPhotos">
              <el-option v-for="tag in allTags" :key="tag.id" :label="tag.name" :value="tag.id" />
            </el-select>

            <el-select v-model="qsFilterCategoryType" placeholder="大类" clearable size="small" style="width: 100px">
              <el-option label="白图" value="white" />
              <el-option label="场景图" value="scene" />
            </el-select>

            <span class="qs-fixed-hint">滚动选择，固定缩略图</span>

            <el-button size="small" @click="resetQsFilters" :disabled="!hasQsFilters">重置</el-button>
          </div>

          <div class="qs-toolbar">
            <el-button size="small" @click="qsSelectAll" :disabled="qsPaginatedPhotos.length === 0">全选</el-button>
            <el-button size="small" @click="qsSelected.clear()" :disabled="qsSelected.size === 0">取消</el-button>
            <span v-if="qsSelected.size > 0" class="qs-sel-hint">已选 {{ qsSelected.size }}</span>
          </div>
          <div v-if="qsSelected.size > 0" class="qs-selection-bar">
            <span>已选择 {{ qsSelected.size }} 张</span>
            <span>将移入为：{{ psLabel[qsAssignProcessState] }}</span>
          </div>
          <div class="qs-photo-grid" v-loading="qsLoading">
            <div v-for="photo in qsPaginatedPhotos" :key="photo.id" :class="['qs-thumb', { selected: qsSelected.has(photo.id) }]" @click="qsToggle(photo.id)">
              <el-image :src="getThumbnailUrl(photo)" fit="cover" lazy class="qs-thumb-img">
                <template #error><div class="qs-thumb-error"><el-icon><PictureFilled /></el-icon></div></template>
              </el-image>
              <span class="qs-thumb-id">#{{ String(photo.display_id).padStart(3, '0') }}</span>
              <div v-if="qsSelected.has(photo.id)" class="qs-check"><el-icon><Select /></el-icon></div>
              <span v-if="photo.target_id && qsPoolMode === 'all'" class="qs-assigned-dot" />
            </div>
            <el-empty v-if="!qsLoading && qsFilteredPhotos.length === 0" description="无照片" :image-size="50" />
          </div>

          <!-- 分页 -->
        </div>

        <!-- 右栏: 目标分类 -->
        <div class="qs-panel qs-right">
          <div class="qs-panel-header">
            <h4>目标分类</h4>
            <span class="qs-panel-count" v-if="qsSelected.size > 0">点击分类以分配 {{ qsSelected.size }} 张</span>
          </div>
          <div class="qs-state-bar">
            <span>移入状态</span>
            <el-radio-group v-model="qsAssignProcessState" size="small">
              <el-radio-button value="raw">原图</el-radio-button>
              <el-radio-button value="retouched">精修</el-radio-button>
              <el-radio-button value="final">完成</el-radio-button>
            </el-radio-group>
          </div>
          <div v-if="qsLastUndo" class="qs-undo-card">
            <span>{{ qsLastUndo.text }}</span>
            <el-button link type="primary" :loading="qsLastUndo.busy" @click="qsUndoLastOperation">撤销</el-button>
          </div>
          <div class="qs-target-list">
            <div v-if="whiteTargets.length > 0" class="qs-section">
              <h5 class="qs-group-title">白图</h5>
              <div v-for="t in whiteTargets" :key="t.id" :class="['qs-target-card', { disabled: qsSelected.size === 0 }]" @click="qsAssign(t.id)">
                <div class="qs-target-info">
                  <span class="qs-target-name">{{ t.name }}</span>
                  <span class="qs-target-desc">{{ t.requirement_desc || '' }}</span>
                </div>
                <div class="qs-target-stats">
                  <span class="qs-target-count">{{ t.photo_count }} 张</span>
                  <el-icon><ArrowRight /></el-icon>
                </div>
              </div>
            </div>
            <div v-if="sceneTargets.length > 0" class="qs-section">
              <h5 class="qs-group-title">场景图</h5>
              <div v-for="t in sceneTargets" :key="t.id" :class="['qs-target-card', { disabled: qsSelected.size === 0 }]" @click="qsAssign(t.id)">
                <div class="qs-target-info">
                  <span class="qs-target-name">{{ t.name }}</span>
                  <span class="qs-target-desc">{{ t.requirement_desc || '' }}</span>
                </div>
                <div class="qs-target-stats">
                  <span class="qs-target-count">{{ t.photo_count }} 张</span>
                  <el-icon><ArrowRight /></el-icon>
                </div>
              </div>
            </div>
            <div v-if="targets.length === 0" class="qs-empty">暂无目标，请先在项目看板中创建</div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showQuickSort = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 标签管理弹窗 -->
    <el-dialog v-model="showTagManager" title="标签管理" width="480px" destroy-on-close>
      <div class="tag-manager">
        <div class="tag-create-row">
          <el-input v-model="newTagName" placeholder="新标签名称" size="small" style="flex:1" @keyup.enter="createTag" />
          <el-color-picker v-model="newTagColor" size="small" />
          <el-button type="primary" size="small" @click="createTag" :disabled="!newTagName.trim()">添加</el-button>
        </div>
        <div class="tag-list">
          <div v-for="tag in allTags" :key="tag.id" class="tag-item">
            <span class="tag-dot" :style="{ background: tag.color }" />
            <span class="tag-name">{{ tag.name }}</span>
            <el-button size="small" text type="danger" @click="deleteTag(tag.id)">删除</el-button>
          </div>
          <div v-if="allTags.length === 0" class="tag-empty">暂无标签</div>
        </div>
      </div>
    </el-dialog>

    <!-- 批量标签操作弹窗 -->
    <el-dialog v-model="showBatchTag" title="批量标签操作" width="500px" destroy-on-close>
      <p style="font-size:13px;color:#606266;margin-bottom:12px;">已选择 {{ selectedIds.size }} 张照片，选择标签后点击添加或移除：</p>
      <div class="batch-tag-section">
        <div class="tag-create-row" style="margin-bottom:12px;">
          <el-input v-model="batchNewTagName" placeholder="新建标签名称" size="small" style="flex:1" @keyup.enter="createTagForBatch" />
          <el-color-picker v-model="batchNewTagColor" size="small" />
          <el-button type="primary" size="small" @click="createTagForBatch" :disabled="!batchNewTagName.trim()">新建</el-button>
        </div>
        <div class="batch-tag-list">
          <div
            v-for="tag in allTags"
            :key="tag.id"
            :class="['batch-tag-chip', { active: batchSelectedTagIds.has(tag.id) }]"
            @click="toggleBatchTag(tag.id)"
          >
            <span class="tag-dot" :style="{ background: tag.color }" />
            <span>{{ tag.name }}</span>
          </div>
          <div v-if="allTags.length === 0" class="tag-empty">暂无标签，请先新建</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showBatchTag = false">取消</el-button>
        <el-button type="danger" :disabled="batchSelectedTagIds.size === 0" :loading="batchTagLoading" @click="batchRemoveTags">移除标签</el-button>
        <el-button type="primary" :disabled="batchSelectedTagIds.size === 0" :loading="batchTagLoading" @click="batchAddTags">添加标签</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft, ArrowRight, UploadFilled, FolderOpened, Select, PictureFilled,
  Document, Edit, Check
} from '@element-plus/icons-vue'
import NASPathPicker from '../components/NASPathPicker.vue'
import type { TargetItem } from '../components/TargetCard.vue'
import request from '../api/request'

const API_BASE = ''

interface PhotoItem {
  id: number; project_id: number; target_id: number | null; display_id: number
  original_path: string; thumbnail_path: string | null; status: string
  process_state: string; shot_at: string | null; tag_ids: number[]; created_at: string
}
interface TagItem { id: number; project_id: number; name: string; color: string; sort_order: number }
interface ShotDateOption { date: string; label: string; count: number }
interface PhotoSnapshot { id: number; target_id: number | null; process_state: string }
interface UndoOperation { text: string; snapshots: PhotoSnapshot[]; busy: boolean }

const route = useRoute()
const router = useRouter()
const projectId = computed(() => route.params.id as string)
const psLabel: Record<string, string> = { raw: '原图', retouched: '精修', final: '完成' }

// ── Import Mode ──
const importMode = ref<'upload' | 'nas'>('upload')
const importModeOptions = [
  { label: '本地上传', value: 'upload' },
  { label: 'NAS 扫描', value: 'nas' }
]

// ── Upload ──
const uploadProcessState = ref('raw')
const uploadShotDate = ref<string | null>(null)
const uploadRef = ref()
const pendingFileCount = ref(0)
const uploading = ref(false)
const uploadTotal = ref(0)
const uploadDone = ref(0)
const uploadTagIds = ref<number[]>([])
const uploadFormData = computed(() => ({
  process_state: uploadProcessState.value,
  tag_ids: uploadTagIds.value.join(','),
  shot_date: uploadShotDate.value || '',
}))

// ── NAS ──
const nasProcessState = ref('raw')
const nasShotDate = ref<string | null>(null)
const showNasPicker = ref(false)
const nasSelectedPath = ref('')
const scanning = ref(false)
const scanTaskId = ref<string | null>(null)
const scanStatus = ref('')
const scanTotal = ref(0)
const scanProcessed = ref(0)
const nasTagIds = ref<number[]>([])
let scanPollTimer: ReturnType<typeof setInterval> | null = null
const scanStatusText = computed(() => {
  if (scanStatus.value === 'queued') return '排队中...'
  if (scanStatus.value === 'running') return `${scanProcessed.value}/${scanTotal.value}`
  if (scanStatus.value === 'done') return `完成 (${scanTotal.value} 张)`
  if (scanStatus.value === 'failed') return '失败'
  return ''
})

// ── Photo Pool ──
const photos = ref<PhotoItem[]>([])
const photoTotal = ref(0)
const loadingPhotos = ref(false)
const poolPage = ref(1)
const poolPageSize = 32

// ── Filters ──
const filterShotDates = ref<string[]>([])
const filterTagId = ref<number | null>(null)
const filterUnassigned = ref(false)
const shotDateOptions = ref<ShotDateOption[]>([])

// ── Selection ──
const selectedIds = reactive(new Set<number>())
const removing = ref(false)

// ── Tags ──
const allTags = ref<TagItem[]>([])
const showTagManager = ref(false)
const newTagName = ref('')
const newTagColor = ref('#409eff')

// ── Targets ──
const targets = ref<(TargetItem & { requirement_desc?: string })[]>([])
const whiteTargets = computed(() => targets.value.filter(t => t.category_type === 'white'))
const sceneTargets = computed(() => targets.value.filter(t => t.category_type === 'scene'))

// ── Quick Sort State ──
const showQuickSort = ref(false)
const qsPoolMode = ref<'unassigned' | 'all'>('unassigned')
const qsPoolOptions = [{ label: '未分类', value: 'unassigned' }, { label: '全部照片', value: 'all' }]
const qsAllPhotos = ref<PhotoItem[]>([])
const qsLoading = ref(false)
const qsSelected = reactive(new Set<number>())

// ── Quick Sort Pagination ──
const qsPage = ref(1)
const qsPageSize = ref(500)

// ── Quick Sort Filters ──
const qsFilterProcessState = ref<string | null>(null)
const qsFilterShotDate = ref<string | null>(null)
const qsFilterTagId = ref<number | null>(null)
const qsFilterCategoryType = ref<string | null>(null)
const qsShotDates = ref<ShotDateOption[]>([])
const qsAssignProcessState = ref<'raw' | 'retouched' | 'final'>('raw')
const qsLastUndo = ref<UndoOperation | null>(null)

const qsFilteredPhotos = computed(() => {
  let filtered = qsAllPhotos.value.filter(p => p.status !== 'deleted')

  // 未分类/全部照片筛选
  if (qsPoolMode.value === 'unassigned') {
    filtered = filtered.filter(p => p.target_id === null)
  }

  // 大类筛选（客户端）
  if (qsFilterCategoryType.value) {
    filtered = filtered.filter(p => {
      if (!p.target_id) return false
      const target = targets.value.find(t => t.id === p.target_id)
      return target?.category_type === qsFilterCategoryType.value
    })
  }

  return filtered
})

const qsPaginatedPhotos = computed(() => {
  const start = (qsPage.value - 1) * qsPageSize.value
  const end = start + qsPageSize.value
  return qsFilteredPhotos.value.slice(start, end)
})

const hasQsFilters = computed(() => {
  return !!(qsFilterProcessState.value || qsFilterShotDate.value || qsFilterTagId.value || qsFilterCategoryType.value)
})

// ── Helpers ──
function goBack() { router.push({ name: 'ProjectDetail', params: { id: projectId.value } }) }

function getThumbnailUrl(photo: PhotoItem): string {
  return `${API_BASE}/storage/${photo.thumbnail_path || photo.original_path}`
}
function getTargetName(id: number): string { return targets.value.find(x => x.id === id)?.name || '' }
function getTagName(id: number): string { return allTags.value.find(x => x.id === id)?.name || '' }
function getTagColor(id: number): string { return allTags.value.find(x => x.id === id)?.color || '#409eff' }
function formatShotAt(iso: string): string {
  const d = new Date(iso)
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}

// ── Data Fetching ──
async function fetchPhotos() {
  if (!projectId.value || projectId.value === 'undefined') {
    console.warn('[ImportCenter] projectId 无效，跳过照片拉取')
    return
  }

  loadingPhotos.value = true
  const skip = (poolPage.value - 1) * poolPageSize
  let url = `/api/v1/projects/${projectId.value}/photos?skip=${skip}&limit=${poolPageSize}`
  // 默认只显示未删除的照片
  url += '&status=pending,selected'
  if (filterTagId.value) url += `&tag_id=${filterTagId.value}`
  if (filterUnassigned.value) url += `&unassigned=true`
  if (filterShotDates.value.length > 0) url += `&shot_dates=${filterShotDates.value.join(',')}`
  try {
    const data = await request.get(url)
    photos.value = data.items
    photoTotal.value = data.total
  } catch { ElMessage.error('获取照片失败') }
  finally { loadingPhotos.value = false }
}

async function fetchShotDates() {
  try {
    const data = await request.get(`/api/v1/projects/${projectId.value}/photos/shot-dates`)
    shotDateOptions.value = (data.items as { date: string; count: number }[]).map(d => ({
      date: d.date,
      count: d.count,
      label: d.date === 'none' ? `无日期 (${d.count})` : `${d.date} (${d.count})`,
    }))
  } catch {}
}

async function fetchTargets() {
  try {
    const data = await request.get(`/api/v1/projects/${projectId.value}/targets`)
    targets.value = data.items
  } catch {}
}

async function fetchTags() {
  try {
    const data = await request.get(`/api/v1/projects/${projectId.value}/tags`)
    allTags.value = data.items
  } catch {}
}

function onFilterChange() { poolPage.value = 1; fetchPhotos() }
watch(poolPage, () => fetchPhotos())

// ── Selection ──
function toggleSelect(id: number) { selectedIds.has(id) ? selectedIds.delete(id) : selectedIds.add(id) }
function selectAll() { photos.value.forEach(p => selectedIds.add(p.id)) }

// ── Upload ──
function onFileChange(_f: any, fl: any[]) { pendingFileCount.value = fl.filter((f: any) => f.status === 'ready').length }
function submitUpload() { if (!uploadRef.value) return; uploadTotal.value = pendingFileCount.value; uploadDone.value = 0; uploading.value = true; uploadRef.value.submit() }
function onSingleUploadSuccess(_r: any, _f: any, fl: any[]) {
  uploadDone.value++; pendingFileCount.value = fl.filter((f: any) => f.status === 'ready').length
  if (uploadDone.value >= uploadTotal.value) { uploading.value = false; ElMessage.success(`${uploadDone.value} 张上传完成`); fetchPhotos(); fetchShotDates() }
}
function onSingleUploadError(_e: any, file: any, fl: any[]) {
  uploadDone.value++; pendingFileCount.value = fl.filter((f: any) => f.status === 'ready').length
  const rawMsg = typeof _e === 'string' ? _e : _e?.message || ''
  let detail = '上传失败'
  try { const parsed = JSON.parse(rawMsg); detail = parsed.detail || detail } catch {}
  if (detail.includes('已存在')) {
    ElMessage.warning(`${file.name}: ${detail}`)
  } else {
    ElMessage.error(`${file.name}: ${detail}`)
  }
  if (uploadDone.value >= uploadTotal.value) { uploading.value = false; fetchPhotos() }
}

// ── NAS Scan ──
function onNasPathSelected(path: string) { nasSelectedPath.value = path === '.' ? '/' : '/' + path }
async function startNasScan() {
  scanning.value = true; scanStatus.value = ''; scanTaskId.value = null
  try {
    const data = await request.post('/api/v1/photos/scan-nas', {
      project_id: Number(projectId.value),
      nas_path: nasSelectedPath.value.replace(/^\//, ''),
      process_state: nasProcessState.value,
      tag_ids: nasTagIds.value,
      shot_date: nasShotDate.value || null,
    })
    scanTaskId.value = data.task_id; scanStatus.value = 'queued'; startScanPolling(data.task_id); ElMessage.success('扫描任务已提交')
  } catch { ElMessage.error('网络请求失败') }
  finally { scanning.value = false }
}
function startScanPolling(taskId: string) {
  stopScanPolling()
  scanPollTimer = setInterval(async () => {
    try {
      const data = await request.get(`/api/v1/photos/scan-nas/${taskId}/status`)
      scanStatus.value = data.status; scanTotal.value = data.total; scanProcessed.value = data.processed
      if (data.status === 'done' || data.status === 'failed') { stopScanPolling(); if (data.status === 'done') { await fetchPhotos(); await fetchShotDates(); ElMessage.success(`NAS 扫描完成，共 ${data.total} 张`) } }
    } catch {}
  }, 2000)
}
function stopScanPolling() { if (scanPollTimer) { clearInterval(scanPollTimer); scanPollTimer = null } }

// ── Delete ──
async function removeFromProject() {
  const ids = Array.from(selectedIds)
  try {
    await ElMessageBox.confirm(
      `确定将选中的 ${ids.length} 张照片移入回收站？照片将从项目底片中移除，但 NAS 原始文件完好无损。`,
      '移除确认',
      { type: 'warning', confirmButtonText: '移入回收站', cancelButtonText: '取消' }
    )
  } catch { return }

  removing.value = true
  try {
    await request.post('/api/v1/photos/bulk-soft-delete', {
      photo_ids: ids
    })
    ids.forEach(id => selectedIds.delete(id))
    ElMessage.success(`已将 ${ids.length} 张照片移入回收站`)
    await Promise.all([fetchPhotos(), fetchTargets(), fetchShotDates()])
  } catch (e: any) {
    ElMessage.error(e.message || '移除失败')
  } finally {
    removing.value = false
  }
}

// ── Quick Sort ──
function openQuickSort() { showQuickSort.value = true }

async function loadQsPhotos() {
  qsLoading.value = true
  try {
    const params = new URLSearchParams({
      skip: '0',
      limit: '500'
    })

    // 添加筛选参数
    if (qsFilterProcessState.value) params.append('process_state', qsFilterProcessState.value)
    if (qsFilterShotDate.value) params.append('shot_dates', qsFilterShotDate.value)
    if (qsFilterTagId.value) params.append('tag_id', qsFilterTagId.value.toString())

    const data = await request.get(`/api/v1/projects/${projectId.value}/photos?${params}`)
    qsAllPhotos.value = data.items
  } catch {
    ElMessage.error('加载照片失败')
  } finally {
    qsLoading.value = false
  }
}

async function loadQsShotDates() {
  try {
    const data = await request.get(`/api/v1/projects/${projectId.value}/photos/shot-dates`)
    qsShotDates.value = (data.items as { date: string; count: number }[]).map(d => ({
      date: d.date,
      count: d.count,
      label: d.date === 'none' ? `无日期 (${d.count})` : `${d.date} (${d.count})`,
    }))
  } catch {
    console.error('加载拍摄日期失败')
  }
}

function resetQsFilters() {
  qsFilterProcessState.value = null
  qsFilterShotDate.value = null
  qsFilterTagId.value = null
  qsFilterCategoryType.value = null
  loadQsPhotos()
}

async function onQsOpen() {
  if (!projectId.value || projectId.value === 'undefined') {
    console.warn('[ImportCenter] projectId 无效，跳过快捷分拣照片拉取')
    ElMessage.error('项目 ID 无效，请刷新页面重试')
    showQuickSort.value = false
    return
  }

  // 重置状态
  qsSelected.clear()
  qsPoolMode.value = 'unassigned'
  resetQsFilters()

  // 并行加载数据
  await Promise.all([
    loadQsPhotos(),
    loadQsShotDates()
  ])
}
function qsToggle(id: number) { qsSelected.has(id) ? qsSelected.delete(id) : qsSelected.add(id) }
function qsSelectAll() { qsPaginatedPhotos.value.forEach(p => qsSelected.add(p.id)) }
watch(qsPoolMode, () => qsSelected.clear())

function qsSnapshotPhotos(ids: number[]): PhotoSnapshot[] {
  return qsAllPhotos.value
    .filter(p => ids.includes(p.id))
    .map(p => ({ id: p.id, target_id: p.target_id, process_state: p.process_state }))
}

function qsGroupSnapshots(snapshots: PhotoSnapshot[]) {
  const groups = new Map<string, PhotoSnapshot[]>()
  for (const item of snapshots) {
    const key = `${item.target_id ?? 'none'}:${item.process_state}`
    const current = groups.get(key) || []
    current.push(item)
    groups.set(key, current)
  }
  return Array.from(groups.values())
}

async function qsRestoreSnapshots(snapshots: PhotoSnapshot[]) {
  for (const group of qsGroupSnapshots(snapshots)) {
    const first = group[0]
    const body: any = {
      photo_ids: group.map(item => item.id),
      process_state: first.process_state,
    }
    if (first.target_id == null) {
      body.remove_from_target = true
    } else {
      body.target_id = first.target_id
    }
    await request.patch('/api/v1/photos/bulk-update', body)
  }
  for (const snapshot of snapshots) {
    const photo = qsAllPhotos.value.find(p => p.id === snapshot.id)
    if (photo) {
      photo.target_id = snapshot.target_id
      photo.process_state = snapshot.process_state
    }
  }
}

async function qsUndoLastOperation() {
  if (!qsLastUndo.value) return
  qsLastUndo.value.busy = true
  try {
    await qsRestoreSnapshots(qsLastUndo.value.snapshots)
    qsLastUndo.value = null
    await fetchTargets()
    ElMessage.success('已撤销上一次分配')
  } catch (e: any) {
    ElMessage.error(e.message || '撤销失败')
    if (qsLastUndo.value) qsLastUndo.value.busy = false
  }
}

async function qsAssign(targetId: number) {
  let snapshots: PhotoSnapshot[] = []
  const ids = Array.from(qsSelected); if (ids.length === 0) { ElMessage.warning('请先在左侧选择照片'); return }
  snapshots = qsSnapshotPhotos(ids)
  try {
    await request.patch('/api/v1/photos/bulk-update', {
      photo_ids: ids,
      target_id: targetId,
      process_state: qsAssignProcessState.value,
    })
    for (const p of qsAllPhotos.value) {
      if (qsSelected.has(p.id)) {
        p.target_id = targetId
        p.process_state = qsAssignProcessState.value
      }
    }
    qsSelected.clear()
    qsLastUndo.value = {
      text: `刚分配 ${ids.length} 张到「${getTargetName(targetId)}」`,
      snapshots,
      busy: false,
    }
    ElMessage.success(`已将 ${ids.length} 张照片分配至「${getTargetName(targetId)}」并设为「${psLabel[qsAssignProcessState.value]}」`)
    await fetchTargets()
  } catch (e: any) { ElMessage.error(e.message || '分配失败') }
}

// ── Quick Sort - Target Expand ──
const expandedTargets = reactive(new Set<number>())

function toggleTargetExpand(targetId: number) {
  if (expandedTargets.has(targetId)) {
    expandedTargets.delete(targetId)
  } else {
    expandedTargets.add(targetId)
  }
}

function getTargetStatusType(status: string): string {
  const map: Record<string, string> = {
    'not_started': 'info',
    'shooting': 'warning',
    'retouching': 'primary',
    'client_review': 'warning',
    'completed': 'success'
  }
  return map[status] || 'info'
}

function getTargetStatusLabel(status: string): string {
  const map: Record<string, string> = {
    'not_started': '未开始',
    'shooting': '拍摄中',
    'retouching': '精修中',
    'client_review': '客户审核',
    'completed': '已完成'
  }
  return map[status] || status
}

async function qsAssignWithState(targetId: number, processState: string) {
  const ids = Array.from(qsSelected)
  if (ids.length === 0) {
    ElMessage.warning('请先在左侧选择照片')
    return
  }

  try {
    await request.patch('/api/v1/photos/bulk-update', {
      photo_ids: ids,
      target_id: targetId,
      process_state: processState
    })

    // 更新本地数据
    for (const p of qsAllPhotos.value) {
      if (qsSelected.has(p.id)) {
        p.target_id = targetId
        p.process_state = processState
      }
    }

    qsSelected.clear()
    expandedTargets.delete(targetId)

    const targetName = getTargetName(targetId)
    const stateLabel = psLabel[processState] || processState
    ElMessage.success(`已将 ${ids.length} 张照片分配至「${targetName}」并设置为「${stateLabel}」`)

    await fetchTargets()
  } catch (e: any) {
    ElMessage.error(e.message || '分配失败')
  }
}

// ── Tag Management ──
const showBatchTag = ref(false)
const batchSelectedTagIds = reactive(new Set<number>())
const batchTagLoading = ref(false)
const batchNewTagName = ref('')
const batchNewTagColor = ref('#409eff')

function toggleBatchTag(id: number) { batchSelectedTagIds.has(id) ? batchSelectedTagIds.delete(id) : batchSelectedTagIds.add(id) }

async function createTagForBatch() {
  const name = batchNewTagName.value.trim(); if (!name) return
  try {
    const tag = await request.post(`/api/v1/projects/${projectId.value}/tags`, { name, color: batchNewTagColor.value })
    batchNewTagName.value = ''
    await fetchTags()
    batchSelectedTagIds.add(tag.id)
    ElMessage.success('标签已创建')
  } catch (e: any) { ElMessage.error(e.message || '创建标签失败') }
}

async function batchAddTags() {
  batchTagLoading.value = true
  try {
    await request.post('/api/v1/photos/bulk-add-tags', { photo_ids: Array.from(selectedIds), tag_ids: Array.from(batchSelectedTagIds) })
    ElMessage.success('标签已添加')
    showBatchTag.value = false
    batchSelectedTagIds.clear()
    await fetchPhotos()
  } catch (e: any) { ElMessage.error(e.message || '添加标签失败') }
  finally { batchTagLoading.value = false }
}

async function batchRemoveTags() {
  batchTagLoading.value = true
  try {
    await request.post('/api/v1/photos/bulk-remove-tags', { photo_ids: Array.from(selectedIds), tag_ids: Array.from(batchSelectedTagIds) })
    ElMessage.success('标签已移除')
    showBatchTag.value = false
    batchSelectedTagIds.clear()
    await fetchPhotos()
  } catch (e: any) { ElMessage.error(e.message || '移除标签失败') }
  finally { batchTagLoading.value = false }
}

async function createTag() {
  const name = newTagName.value.trim(); if (!name) return
  try {
    await request.post(`/api/v1/projects/${projectId.value}/tags`, { name, color: newTagColor.value })
    newTagName.value = ''
    await fetchTags()
    ElMessage.success('标签已创建')
  } catch (e: any) { ElMessage.error(e.message || '创建标签失败') }
}
async function deleteTag(tagId: number) {
  try { await ElMessageBox.confirm('删除此标签？已打的标签关联将解除。', '确认', { type: 'warning' }) } catch { return }
  try {
    await request.delete(`/api/v1/projects/${projectId.value}/tags/${tagId}`)
    await fetchTags()
    ElMessage.success('标签已删除')
  } catch { ElMessage.error('删除失败') }
}

// ── Init ──
onMounted(() => { Promise.all([fetchPhotos(), fetchTargets(), fetchTags(), fetchShotDates()]) })
onUnmounted(() => { stopScanPolling() })
</script>

<style scoped>
.import-center { padding: 20px 28px; min-height: 100%; display: flex; flex-direction: column; gap: 16px; }
.top-bar { display: flex; align-items: center; gap: 16px; }
.page-title { font-size: 20px; font-weight: 700; color: #2c3e50; }
.project-id { font-size: 13px; color: #7f8c8d; background: #ecf0f1; padding: 3px 10px; border-radius: 4px; font-family: 'Courier New', monospace; }

/* Zone A */
.import-zone { margin-bottom: 16px; }
.import-card.compact { background: white; border-radius: 10px; padding: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.card-header-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.zone-title { font-size: 14px; font-weight: 600; color: #2c3e50; margin: 0; }
.mode-header { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.mode-label { font-size: 12px; color: #909399; white-space: nowrap; }
.compact-body .import-upload :deep(.el-upload-dragger) { width: 100%; padding: 10px 0; min-height: auto; }
.compact-body .import-upload :deep(.el-icon--upload) { margin: 0; font-size: 20px; }
.compact-body .import-upload :deep(.el-upload__text) { font-size: 12px; margin: 0; }
.import-upload { width: 100%; }
.upload-confirm { display: flex; align-items: center; justify-content: space-between; margin-top: 6px; }
.pending-hint { font-size: 12px; color: #606266; }
.nas-row { display: flex; gap: 8px; }
.nas-row .el-input { flex: 1; }
.nas-trigger { cursor: pointer; color: var(--el-color-primary); font-size: 16px; }
.scan-progress { margin-top: 6px; }
.scan-text { font-size: 11px; color: #909399; }
.tag-select-row { display: flex; align-items: center; gap: 6px; margin-top: 6px; }
.tag-label { font-size: 12px; color: #909399; white-space: nowrap; }

/* Zone B */
.pool-zone { background: white; border-radius: 12px; padding: 14px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); flex: 1; display: flex; flex-direction: column; min-height: 0; }
.pool-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.pool-total { font-size: 13px; font-weight: 400; color: #909399; }
.pool-actions { display: flex; gap: 8px; align-items: center; }
.filter-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.filter-group { display: flex; align-items: center; gap: 4px; }
.filter-label { font-size: 12px; color: #909399; white-space: nowrap; }

/* 8-col grid */
.photo-grid-8 { display: grid; grid-template-columns: repeat(8, 1fr); gap: 8px; flex: 1; overflow-y: auto; align-content: start; }
.photo-card-sm { position: relative; border-radius: 6px; overflow: hidden; aspect-ratio: 1; border: 2px solid transparent; transition: border-color 0.15s; cursor: pointer; }
.photo-card-sm.selected { border-color: #409eff; box-shadow: 0 0 0 2px rgba(64,158,255,0.25); }
.card-checkbox { position: absolute; top: 4px; left: 4px; width: 18px; height: 18px; z-index: 2; }
.card-checkbox .checked { width: 18px; height: 18px; background: #409eff; border-radius: 3px; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; }
.card-checkbox .unchecked { width: 18px; height: 18px; border: 2px solid rgba(255,255,255,0.8); border-radius: 3px; background: rgba(0,0,0,0.2); }
.card-img { width: 100%; height: 100%; display: block; }
.card-img :deep(img) { width: 100%; height: 100%; object-fit: cover; }
.card-img-error { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #f5f7fa; color: #c0c4cc; }
.card-id { position: absolute; bottom: 3px; left: 3px; font-size: 10px; font-weight: 700; color: white; background: rgba(0,0,0,0.55); padding: 1px 4px; border-radius: 3px; }
.card-shot-at { position: absolute; top: 4px; right: 4px; font-size: 9px; color: white; background: rgba(0,0,0,0.5); padding: 1px 3px; border-radius: 3px; }
.card-ps { position: absolute; bottom: 3px; right: 3px; font-size: 9px; font-weight: 600; padding: 1px 4px; border-radius: 3px; }
.ps-raw { background: rgba(192,196,204,0.85); color: white; }
.ps-retouched { background: rgba(230,162,60,0.85); color: white; }
.ps-final { background: rgba(103,194,58,0.85); color: white; }
.card-target { position: absolute; top: 4px; left: 50%; transform: translateX(-50%); font-size: 9px; font-weight: 600; color: white; background: rgba(64,158,255,0.8); padding: 1px 4px; border-radius: 3px; white-space: nowrap; max-width: 80%; overflow: hidden; text-overflow: ellipsis; }
.card-tags { position: absolute; bottom: 16px; left: 3px; display: flex; gap: 2px; }
.mini-tag { font-size: 8px; color: white; padding: 0 3px; border-radius: 2px; line-height: 1.4; max-width: 40px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Quick Sort Shuttle */
.qs-dialog :deep(.el-dialog__body) { padding: 0 20px 10px; }
.qs-shuttle { display: flex; gap: 16px; height: 75vh; }
.qs-panel { background: #f5f7fa; border-radius: 10px; padding: 14px; display: flex; flex-direction: column; min-height: 0; }
.qs-left { flex: 3; }
.qs-right { flex: 2; overflow-y: auto; }
.qs-panel-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.qs-panel-header h4 { font-size: 14px; font-weight: 600; color: #2c3e50; margin: 0; }
.qs-panel-count { font-size: 12px; color: #909399; }
.qs-filters { display: flex; gap: 8px; padding: 8px 12px; background: #fff; border-radius: 6px; margin-bottom: 8px; flex-wrap: wrap; }
.qs-fixed-hint { font-size: 12px; color: #909399; align-self: center; }
.qs-toolbar { display: flex; gap: 8px; align-items: center; margin-bottom: 8px; }
.qs-sel-hint { font-size: 12px; color: #409eff; font-weight: 500; }
.qs-selection-bar,
.qs-undo-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 10px;
  margin-bottom: 8px;
  border-radius: 8px;
  font-size: 12px;
}
.qs-selection-bar {
  color: #303133;
  background: #fff;
  border: 1px solid #dcdfe6;
  font-weight: 600;
}
.qs-undo-card {
  color: #606266;
  background: #ecf5ff;
  border: 1px solid #b3d8ff;
}
.qs-photo-grid {
  flex: 1;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(118px, 118px));
  grid-auto-rows: 118px;
  justify-content: start;
  align-content: start;
  gap: 10px;
  padding: 10px;
  min-height: 400px;
}
.qs-thumb { position: relative; border-radius: 6px; overflow: hidden; aspect-ratio: 1; cursor: pointer; border: 2px solid transparent; transition: border-color 0.15s; }
.qs-thumb.selected { border-color: #409eff; box-shadow: 0 0 0 2px rgba(64,158,255,0.3); }
.qs-thumb-img { width: 100%; height: 100%; }
.qs-thumb-img :deep(img) { width: 100%; height: 100%; object-fit: cover; }
.qs-thumb-error { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #f5f7fa; color: #c0c4cc; }
.qs-thumb-id { position: absolute; bottom: 2px; left: 2px; font-size: 9px; font-weight: 700; color: white; background: rgba(0,0,0,0.5); padding: 0 3px; border-radius: 2px; }
.qs-check { position: absolute; top: 3px; right: 3px; width: 18px; height: 18px; background: #409eff; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: white; font-size: 12px; }
.qs-assigned-dot { position: absolute; bottom: 4px; right: 4px; width: 8px; height: 8px; border-radius: 50%; background: #67c23a; border: 1px solid white; }
.qs-target-list { overflow-y: auto; flex: 1; }
.qs-state-bar { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 8px 10px; background: #fff; border-radius: 8px; margin-bottom: 10px; font-size: 12px; color: #606266; }
.qs-section { margin-bottom: 14px; }
.qs-group-title { font-size: 12px; font-weight: 600; color: #909399; margin: 0 0 8px 0; }
.qs-target-card { display: flex; justify-content: space-between; align-items: center; padding: 10px 12px; border-radius: 8px; cursor: pointer; transition: background 0.15s; margin-bottom: 6px; background: white; border: 1px solid #ebeef5; }
.qs-target-card:hover:not(.disabled) { background: #ecf5ff; border-color: #409eff; }
.qs-target-card.disabled { opacity: 0.5; cursor: default; }
.qs-target-info { display: flex; flex-direction: column; gap: 2px; }
.qs-target-name { font-size: 14px; color: #2c3e50; font-weight: 500; }
.qs-target-desc { font-size: 11px; color: #909399; }
.qs-target-stats { display: flex; align-items: center; gap: 6px; color: #909399; }
.qs-target-count { font-size: 12px; }
.qs-empty { text-align: center; color: #c0c4cc; font-size: 13px; padding: 24px 0; }

/* Tag Manager */
.tag-create-row { display: flex; gap: 8px; align-items: center; margin-bottom: 14px; }
.tag-list { max-height: 300px; overflow-y: auto; }
.tag-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid #f0f2f5; }
.tag-dot { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
.tag-name { flex: 1; font-size: 14px; color: #2c3e50; }
.tag-empty { text-align: center; color: #c0c4cc; font-size: 13px; padding: 20px; }

/* Batch tag */
.batch-tag-list { display: flex; flex-wrap: wrap; gap: 8px; }
.batch-tag-chip { display: flex; align-items: center; gap: 4px; padding: 6px 12px; border-radius: 16px; border: 2px solid #ebeef5; cursor: pointer; transition: all 0.15s; font-size: 13px; }
.batch-tag-chip:hover { border-color: #409eff; }
.batch-tag-chip.active { border-color: #409eff; background: #ecf5ff; }
</style>
