<template>
  <div class="workspace-view">
    <!-- 顶部 -->
    <div class="workspace-header">
      <el-button @click="$emit('back')" :icon="ArrowLeft">返回看板</el-button>
      <h2 class="target-name">项目工作台 — 工作进度</h2>
      <span v-if="targetInfo" class="target-sub-name">{{ targetInfo.name }}</span>
      <span class="status-badge" :class="'badge-' + (targetInfo?.target_status || '')">
        {{ statusLabel[targetInfo?.target_status || ''] || '' }}
      </span>
      <div class="header-spacer" />
      <el-button type="primary" plain @click="$emit('open-shuttle')">
        📷 照片整理
      </el-button>
      <el-button type="success" :icon="Upload" @click="showImportDialog = true">
        上传 / 扫描
      </el-button>
    </div>

    <!-- 三区段主体 -->
    <div class="workspace-body" v-loading="loading" v-infinite-scroll="loadMorePhotos" :infinite-scroll-disabled="loading || !hasMorePhotos" :infinite-scroll-distance="200">
      <div v-if="targetInfo?.category_type === 'scene'" class="scene-reference-section">
        <div class="scene-goal-panel">
          <div class="reference-head wide">
            <span>场景目标图</span>
            <el-tooltip content="可选择多张项目图片作为场景目标图，不做版本迭代。" placement="top">
              <span class="hint-icon">!</span>
            </el-tooltip>
            <div class="header-spacer" />
            <el-button size="small" type="primary" plain @click="openReferencePicker('scene_goal')">从项目选择</el-button>
          </div>
          <div v-if="currentReferences('scene_goal').length > 0" class="goal-preview-grid">
            <div
              v-for="ref in currentReferences('scene_goal')"
              :key="ref.id"
              class="goal-preview-card"
            >
              <el-image :src="thumbUrl(ref.photo)" fit="cover" lazy class="goal-reference-img" />
              <span>#{{ String(ref.photo.display_id).padStart(3, '0') }}</span>
              <button class="zoom-btn" title="放大查看" @click.stop="openReferencePreview('scene_goal', ref.photo_id)">⌕</button>
            </div>
          </div>
          <div v-else class="reference-empty">未选择场景目标图</div>
        </div>
        <div class="scene-goal-panel">
          <div class="reference-head wide">
            <span>场景空场景</span>
            <el-tooltip content="空场景支持迭代，每次选择会生成一个新版本，并保留历史记录。" placement="top">
              <span class="hint-icon">!</span>
            </el-tooltip>
            <div class="header-spacer" />
            <el-button size="small" type="primary" plain @click="openReferencePicker('empty_scene')">从项目选择</el-button>
          </div>
          <div v-if="currentReference('empty_scene')" class="goal-preview-grid">
            <div class="goal-preview-card">
              <el-image :src="thumbUrl(currentReference('empty_scene')!.photo)" fit="cover" lazy class="goal-reference-img" />
              <span>V{{ currentReference('empty_scene')!.version }}</span>
              <button class="zoom-btn" title="放大查看" @click.stop="openReferencePreview('empty_scene', currentReference('empty_scene')!.photo_id)">⌕</button>
            </div>
          </div>
          <div v-else class="reference-empty">未选择场景空场景</div>
        </div>
      </div>

      <ConfirmedRawSection
        :photos="targetPhotos"
        :feedback-map="feedbackMap"
        @pick-photos="showPhotoPicker = true"
        @confirmed="fetchAllPhotos"
        @preview="openPreview"
      />
      <RetouchedSection
        :photos="targetPhotos"
        :project-photos="allProjectPhotos"
        :project-id="projectId"
        :target-id="targetId"
        :feedback-map="feedbackMap"
        @uploaded="fetchAllPhotos"
        @preview="openPreview"
      />
      <FinalSection
        :photos="targetPhotos"
        :project-id="projectId"
        :target-id="targetId"
        :feedback-map="feedbackMap"
        @uploaded="fetchAllPhotos"
        @preview="openPreview"
        @complete-target="completeTarget"
      />

      <!-- 加载提示 -->
      <div v-if="loading && allProjectPhotos.length > 0" class="loading-more">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>加载中...</span>
      </div>
      <div v-else-if="!hasMorePhotos && allProjectPhotos.length > 0" class="no-more">
        已加载全部 {{ photoTotal }} 张照片
      </div>
    </div>

    <!-- 项目选图器弹窗 -->
    <el-dialog v-model="showPhotoPicker" title="从项目选图" width="700px" destroy-on-close>
      <div class="picker-toolbar">
        <el-input v-model="pickerSearch" placeholder="编号/文件名" :prefix-icon="Search" size="small" clearable style="width: 130px" />
        <el-select v-model="pickerScope" size="small" style="width: 150px">
          <el-option label="当前+未分拣" value="target_unassigned" />
          <el-option label="当前子项目" value="target" />
          <el-option label="未分拣" value="unassigned" />
          <el-option label="全部项目图片" value="all" />
        </el-select>
        <el-select v-model="pickerProcessState" size="small" clearable placeholder="处理状态" style="width: 105px">
          <el-option label="原图" value="raw" />
          <el-option label="精修图" value="retouched" />
          <el-option label="完成图" value="final" />
        </el-select>
        <el-select v-model="pickerStatus" size="small" clearable placeholder="图片状态" style="width: 105px">
          <el-option label="待处理" value="pending" />
          <el-option label="已选中" value="selected" />
        </el-select>
        <el-select v-model="pickerTagId" size="small" clearable placeholder="标签" style="width: 110px">
          <el-option v-for="tag in projectTags" :key="tag.id" :label="tag.name" :value="tag.id" />
        </el-select>
        <span class="picker-hint">当前子项目照片优先显示，也可切换选择未分拣或其他图片</span>
      </div>
      <div class="picker-grid">
        <div
          v-for="photo in pickerPhotos"
          :key="photo.id"
          :class="['photo-thumb', { selected: pickerSelected.has(photo.id) }]"
          @click="togglePicker(photo.id)"
        >
          <el-image :src="thumbUrl(photo)" fit="cover" lazy class="thumb-img">
            <template #error><div class="thumb-error"><el-icon><PictureFilled /></el-icon></div></template>
          </el-image>
          <span class="display-id-badge">#{{ String(photo.display_id).padStart(3, '0') }}</span>
          <span class="process-badge" :class="'ps-' + photo.process_state">{{ processLabel[photo.process_state] }}</span>
          <span v-if="photo.target_id === props.targetId" class="scope-badge">当前</span>
          <span v-else-if="!photo.target_id" class="scope-badge muted">未分拣</span>
          <div v-if="pickerSelected.has(photo.id)" class="check-mark"><el-icon><Select /></el-icon></div>
        </div>
      </div>
      <el-empty v-if="pickerPhotos.length === 0" description="无可选照片" :image-size="60" />
      <template #footer>
        <el-button @click="showPhotoPicker = false">取消</el-button>
        <el-button type="primary" :disabled="pickerSelected.size === 0" @click="movePickedToTarget">
          移入当前目标 ({{ pickerSelected.size }})
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showReferencePicker" title="选择场景参考图" width="720px" destroy-on-close>
      <div class="picker-toolbar">
        <el-input v-model="referenceSearch" placeholder="编号/文件名" :prefix-icon="Search" size="small" clearable style="width: 130px" />
        <el-select v-model="referenceProcessState" size="small" clearable placeholder="处理状态" style="width: 110px">
          <el-option label="原图" value="raw" />
          <el-option label="精修图" value="retouched" />
          <el-option label="完成图" value="final" />
        </el-select>
        <el-select v-model="referenceTagId" size="small" clearable placeholder="标签" style="width: 120px">
          <el-option v-for="tag in projectTags" :key="tag.id" :label="tag.name" :value="tag.id" />
        </el-select>
        <span class="picker-hint">选择项目图片作为{{ referencePickerType === 'scene_goal' ? '场景目标图' : '场景空场景' }}</span>
      </div>
      <div class="picker-grid">
        <div
          v-for="photo in referencePickerPhotos"
          :key="photo.id"
          class="photo-thumb"
          @click="setReference(photo.id)"
        >
          <el-image :src="thumbUrl(photo)" fit="cover" lazy class="thumb-img">
            <template #error><div class="thumb-error"><el-icon><PictureFilled /></el-icon></div></template>
          </el-image>
          <span class="display-id-badge">#{{ String(photo.display_id).padStart(3, '0') }}</span>
          <span class="process-badge" :class="'ps-' + photo.process_state">{{ processLabel[photo.process_state] }}</span>
        </div>
      </div>
    </el-dialog>

    <div v-if="previewVisible" class="preview-mask" @click.self="closePreview">
      <div class="preview-shell">
        <div class="preview-image-wrap">
          <img :src="previewUrl" class="preview-image" />
        </div>
        <div class="preview-caption">
          <div class="caption-line">{{ previewPhotoItem?.original_filename || '—' }}</div>
          <div class="caption-line caption-id">#{{ String(previewPhotoItem?.display_id || '000').padStart(3, '0') }}</div>
        </div>
        <button v-if="previewIndex > 0" class="preview-nav-close prev" @click.stop="previewIndex--">‹</button>
        <button v-if="previewIndex < previewPhotos.length - 1" class="preview-nav-close next" @click.stop="previewIndex++">›</button>
        <button class="preview-close" @click="closePreview">✕</button>
      </div>
    </div>

    <!-- 定点导入弹窗 -->
    <el-dialog
      v-model="showImportDialog"
      title="定点导入 — 上传 / NAS 扫描"
      width="600px"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <el-form label-width="90px" class="import-form">
        <el-form-item label="入库阶段">
          <el-radio-group v-model="importProcessState">
            <el-radio value="raw">原图</el-radio>
            <el-radio value="retouched">精修</el-radio>
            <el-radio value="final">完成</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="拍摄日期">
          <el-date-picker
            v-model="importShotDate"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="不选则自动识别"
            clearable
            style="width: 100%"
          />
        </el-form-item>

        <el-divider content-position="left">方式一：本地上传</el-divider>
        <el-form-item label="选择文件">
          <el-upload
            ref="uploadRef"
            drag
            multiple
            :auto-upload="false"
            :action="`/api/v1/projects/${props.projectId}/photos/upload`"
            name="file"
            :data="uploadFormData"
            accept=".jpg,.jpeg,.png,.tif,.tiff,.webp,.heic"
            :on-change="onFileChange"
            :on-success="onSingleUploadSuccess"
            :on-error="onSingleUploadError"
            class="import-upload"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽或 <em>点击选择文件</em></div>
          </el-upload>
        </el-form-item>

        <el-form-item v-if="pendingFileCount > 0">
          <div class="upload-confirm-row">
            <span class="pending-hint">已选择 {{ pendingFileCount }} 个文件</span>
            <el-button type="primary" :loading="uploading" @click="submitUpload">确认上传</el-button>
          </div>
        </el-form-item>

        <el-form-item v-if="uploading || (uploadDone > 0 && uploadDone < uploadTotal)" label="进度">
          <el-progress
            :percentage="uploadTotal > 0 ? Math.round((uploadDone / uploadTotal) * 100) : 0"
            :stroke-width="8"
            :status="uploadDone === uploadTotal && uploadTotal > 0 ? 'success' : undefined"
          />
          <span class="scan-status-text">{{ uploadDone }} / {{ uploadTotal }}</span>
        </el-form-item>

        <el-divider content-position="left">方式二：NAS 扫描</el-divider>
        <el-form-item label="NAS 路径">
          <div class="nas-row">
            <el-input v-model="importNasPath" placeholder="点击右侧图标选择..." readonly>
              <template #suffix>
                <el-icon class="nas-picker-trigger" @click="showNasPicker = true"><FolderOpened /></el-icon>
              </template>
            </el-input>
            <el-button type="success" :loading="importScanning" :disabled="!importNasPath" @click="startImportScan">扫描入库</el-button>
          </div>
        </el-form-item>

        <el-form-item v-if="importScanTaskId" label="扫描状态">
          <div class="scan-status">
            <el-progress
              :percentage="scanProgressPercent"
              :stroke-width="8"
              :status="scanStatus === 'done' ? 'success' : scanStatus === 'failed' ? 'exception' : undefined"
            />
            <span class="scan-status-text">{{ scanStatusText }}</span>
          </div>
        </el-form-item>
      </el-form>

      <NASPathPicker v-model="showNasPicker" @select="onImportNasPathSelected" />

      <template #footer>
        <el-button @click="closeImportDialog">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Search,
  PictureFilled,
  Select,
  Upload,
  UploadFilled,
  FolderOpened,
  Loading,
} from '@element-plus/icons-vue'
import request from '../api/request'
import NASPathPicker from './NASPathPicker.vue'
import ConfirmedRawSection from './ConfirmedRawSection.vue'
import RetouchedSection from './RetouchedSection.vue'
import FinalSection from './FinalSection.vue'

export interface PhotoItem {
  id: number
  project_id: number
  target_id: number | null
  parent_id: number | null
  display_id: number
  version: number
  is_confirmed: boolean
  is_locked: boolean
  original_path: string
  original_filename: string | null
  thumbnail_path: string | null
  status: string
  process_state: string
  retouch_quality: string | null
  retouch_batch_id: string | null
  client_notes: string | null
  revision_notes: string | null
  tag_ids?: number[]
  created_at: string
}

interface TargetInfo {
  id: number
  name: string
  category_type: 'white' | 'scene'
  target_status: string
  photo_count: number
}

interface TargetReferenceItem {
  id: number
  asset_type: 'scene_goal' | 'empty_scene'
  photo_id: number
  version: number
  is_current: boolean
  notes: string | null
  photo: Pick<PhotoItem, 'id' | 'display_id' | 'original_filename' | 'thumbnail_path' | 'original_path'>
}

const props = defineProps<{
  projectId: string | number
  targetId: number
}>()

const emit = defineEmits<{ back: [], 'open-shuttle': [] }>()

const statusLabel: Record<string, string> = {
  not_started: '未拍摄',
  shooting: '拍摄中',
  retouching: '精修中',
  client_review: '客户确认中',
  completed: '已完成',
}
const processLabel: Record<string, string> = {
  raw: '原图',
  retouched: '精修',
  final: '完成',
}

// ── 核心数据 ────────────────────────────────────────────
const targetInfo = ref<TargetInfo | null>(null)
const allProjectPhotos = ref<PhotoItem[]>([])
const targetReferences = ref<TargetReferenceItem[]>([])
const projectTags = ref<{ id: number; name: string; color: string; scope?: string }[]>([])
const photoTotal = ref(0)
const photoSkip = ref(0)
const photoLimit = 50
const hasMorePhotos = computed(() => allProjectPhotos.value.length < photoTotal.value)
const loading = ref(false)

// ── 客户反馈数据 ────────────────────────────────────────
const feedbackMap = ref<Map<number, { is_confirmed: boolean; comment: string | null; annotation_path?: string | null }>>(new Map())
let feedbackPollTimer: ReturnType<typeof setInterval> | null = null

const targetPhotos = computed(() =>
  allProjectPhotos.value.filter(p => p.target_id === props.targetId && p.status !== 'deleted')
)

// ── 项目选图器 ──────────────────────────────────────────
const showPhotoPicker = ref(false)
const pickerSearch = ref('')
const pickerScope = ref<'target_unassigned' | 'target' | 'unassigned' | 'all'>('target_unassigned')
const pickerProcessState = ref<string | null>('raw')
const pickerStatus = ref<string | null>(null)
const pickerTagId = ref<number | null>(null)
const pickerSelected = reactive(new Set<number>())
const showReferencePicker = ref(false)
const referencePickerType = ref<'scene_goal' | 'empty_scene'>('scene_goal')
const referenceSearch = ref('')
const referenceProcessState = ref<string | null>(null)
const referenceTagId = ref<number | null>(null)
const previewVisible = ref(false)
const previewPhotos = ref<PhotoItem[]>([])
const previewIndex = ref(0)
const previewPhotoItem = computed(() => previewPhotos.value[previewIndex.value])
const previewUrl = computed(() => previewPhotoItem.value ? thumbUrl(previewPhotoItem.value) : '')

const pickerPhotos = computed(() => {
  let list = allProjectPhotos.value.filter(p => p.status !== 'deleted')
  if (pickerScope.value === 'target') {
    list = list.filter(p => p.target_id === props.targetId)
  } else if (pickerScope.value === 'unassigned') {
    list = list.filter(p => p.target_id == null)
  } else if (pickerScope.value === 'target_unassigned') {
    list = list.filter(p => p.target_id === props.targetId || p.target_id == null)
  }
  list = filterProjectPhotos(list, pickerSearch.value, pickerProcessState.value, pickerStatus.value, pickerTagId.value)
  return list.sort((a, b) => pickerPriority(a) - pickerPriority(b) || b.display_id - a.display_id)
})

const referencePickerPhotos = computed(() =>
  filterProjectPhotos(
    allProjectPhotos.value.filter(p => p.status !== 'deleted'),
    referenceSearch.value,
    referenceProcessState.value,
    null,
    referenceTagId.value,
  ),
)

function filterProjectPhotos(
  source: PhotoItem[],
  keyword: string,
  processState: string | null,
  status: string | null,
  tagId: number | null,
) {
  let list = source
  if (processState) list = list.filter(p => p.process_state === processState)
  if (status) list = list.filter(p => p.status === status)
  if (tagId) list = list.filter(p => (p.tag_ids || []).includes(tagId))
  const q = keyword.trim().toLowerCase()
  if (q) {
    const num = parseInt(q, 10)
    list = list.filter(p =>
      (!Number.isNaN(num) && p.display_id === num) ||
      (p.original_filename || '').toLowerCase().includes(q)
    )
  }
  return list
}

function pickerPriority(photo: PhotoItem) {
  if (photo.target_id === props.targetId) return 0
  if (photo.target_id == null) return 1
  return 2
}

function togglePicker(id: number) {
  if (pickerSelected.has(id)) pickerSelected.delete(id)
  else pickerSelected.add(id)
}

async function movePickedToTarget() {
  const ids = Array.from(pickerSelected)
  if (ids.length === 0) return
  try {
    await request.patch('/api/v1/photos/bulk-update', { photo_ids: ids, target_id: props.targetId })
    for (const p of allProjectPhotos.value) {
      if (pickerSelected.has(p.id)) p.target_id = props.targetId
    }
    pickerSelected.clear()
    showPhotoPicker.value = false
    ElMessage.success(`已移入 ${ids.length} 张照片`)
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  }
}

function thumbUrl(photo: Pick<PhotoItem, 'thumbnail_path' | 'original_path'>): string {
  const path = photo.thumbnail_path || photo.original_path
  return `/storage/${path}`
}

function currentReference(type: 'scene_goal' | 'empty_scene') {
  return targetReferences.value.find(item => item.asset_type === type && item.is_current)
}

function currentReferences(type: 'scene_goal' | 'empty_scene') {
  return targetReferences.value.filter(item => item.asset_type === type && item.is_current)
}

function openReferencePicker(type: 'scene_goal' | 'empty_scene') {
  referencePickerType.value = type
  showReferencePicker.value = true
}

async function fetchTargetReferences() {
  if (!props.projectId || !props.targetId) return
  try {
    const data = await request.get(`/api/v1/projects/${props.projectId}/targets/${props.targetId}/references`)
    targetReferences.value = data.items || []
  } catch {
    targetReferences.value = []
  }
}

async function setReference(photoId: number) {
  try {
    await request.post(`/api/v1/projects/${props.projectId}/targets/${props.targetId}/references`, {
      asset_type: referencePickerType.value,
      photo_id: photoId,
    })
    showReferencePicker.value = false
    await fetchTargetReferences()
    ElMessage.success('场景参考图已更新')
  } catch (e: any) {
    ElMessage.error(e.message || '设置失败')
  }
}

function openPreview(photo: PhotoItem) {
  const scopedList = targetPhotos.value.filter(
    p => p.process_state === photo.process_state && p.status !== 'deleted',
  )
  const fallbackList = allProjectPhotos.value.filter(
    p => p.process_state === photo.process_state && p.status !== 'deleted',
  )
  previewPhotos.value = scopedList.some(p => p.id === photo.id) ? scopedList : fallbackList
  const idx = previewPhotos.value.findIndex(p => p.id === photo.id)
  previewIndex.value = idx >= 0 ? idx : 0
  previewVisible.value = true
}

function openPreviewById(photoId: number) {
  const photo = allProjectPhotos.value.find(p => p.id === photoId)
  if (photo) openPreview(photo)
}

function openReferencePreview(type: 'scene_goal' | 'empty_scene', photoId: number) {
  const refs = targetReferences.value.filter(item => item.asset_type === type && (type === 'empty_scene' || item.is_current))
  const photos = refs.map(ref => {
    const full = allProjectPhotos.value.find(p => p.id === ref.photo_id)
    if (full) return full
    return {
      id: ref.photo.id,
      project_id: Number(props.projectId),
      target_id: props.targetId,
      parent_id: null,
      display_id: ref.photo.display_id,
      version: ref.version,
      is_confirmed: false,
      is_locked: false,
      original_path: ref.photo.original_path,
      original_filename: ref.photo.original_filename,
      thumbnail_path: ref.photo.thumbnail_path,
      status: 'pending',
      process_state: 'raw',
      retouch_quality: null,
      retouch_batch_id: null,
      client_notes: null,
      revision_notes: ref.notes,
      tag_ids: [],
      created_at: '',
    }
  })
  previewPhotos.value = photos
  const idx = photos.findIndex(p => p.id === photoId)
  previewIndex.value = idx >= 0 ? idx : 0
  previewVisible.value = true
}

function closePreview() {
  previewVisible.value = false
}

// ── 完成归档 ────────────────────────────────────────────
async function completeTarget() {
  try {
    await ElMessageBox.confirm('确定将此子项目标记为完成并归档？', '完成归档', { type: 'warning' })
  } catch { return }

  try {
    await request.patch(`/api/v1/projects/${props.projectId}/targets/${props.targetId}`, { target_status: 'completed' })
    if (targetInfo.value) targetInfo.value.target_status = 'completed'
    ElMessage.success('子项目已完成归档')
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  }
}

// ── 定点导入逻辑 ─────────────────────────────────────────
const showImportDialog = ref(false)
const importProcessState = ref<'raw' | 'retouched' | 'final'>('raw')
const importShotDate = ref<string | null>(null)
const uploadRef = ref()
const pendingFileCount = ref(0)
const uploading = ref(false)
const uploadTotal = ref(0)
const uploadDone = ref(0)
const showNasPicker = ref(false)
const importNasPath = ref('')
const importScanning = ref(false)
const importScanTaskId = ref<string | null>(null)
const scanStatus = ref('')
const scanTotal = ref(0)
const scanProcessed = ref(0)
let scanPollTimer: ReturnType<typeof setInterval> | null = null

const uploadFormData = computed(() => ({
  target_id: String(props.targetId),
  process_state: importProcessState.value,
  shot_date: importShotDate.value || '',
}))

const scanProgressPercent = computed(() => {
  if (scanTotal.value === 0) return 0
  return Math.round((scanProcessed.value / scanTotal.value) * 100)
})

const scanStatusText = computed(() => {
  if (scanStatus.value === 'queued') return '排队中...'
  if (scanStatus.value === 'running') return `${scanProcessed.value}/${scanTotal.value}`
  if (scanStatus.value === 'done') return `扫描完成 (${scanTotal.value} 张)`
  if (scanStatus.value === 'failed') return '扫描失败'
  return ''
})

function onFileChange(_file: any, fileList: any[]) {
  pendingFileCount.value = fileList.filter((f: any) => f.status === 'ready').length
}

function submitUpload() {
  if (!uploadRef.value) return
  uploadTotal.value = pendingFileCount.value
  uploadDone.value = 0
  uploading.value = true
  uploadRef.value.submit()
}

function onSingleUploadSuccess(response: any, _file: any, fileList: any[]) {
  uploadDone.value++
  if (response && response.id) {
    allProjectPhotos.value.unshift({
      id: response.id,
      project_id: response.project_id,
      target_id: response.target_id,
      parent_id: response.parent_id ?? null,
      display_id: response.display_id,
      version: response.version ?? 1,
      is_confirmed: response.is_confirmed ?? false,
      is_locked: response.is_locked ?? false,
      original_path: response.original_path,
      original_filename: response.original_filename ?? null,
      thumbnail_path: response.thumbnail_path,
      status: response.status,
      process_state: response.process_state || 'raw',
      retouch_quality: response.retouch_quality ?? null,
      retouch_batch_id: response.retouch_batch_id ?? null,
      client_notes: response.client_notes ?? null,
      revision_notes: response.revision_notes ?? null,
      tag_ids: response.tag_ids || [],
      created_at: new Date().toISOString(),
    })
  }
  const remaining = fileList.filter((f: any) => f.status === 'ready').length
  pendingFileCount.value = remaining
  if (uploadDone.value >= uploadTotal.value) {
    uploading.value = false
    ElMessage.success(`全部 ${uploadDone.value} 张上传完成`)
  }
}

function onSingleUploadError(_error: any, _file: any, fileList: any[]) {
  uploadDone.value++
  pendingFileCount.value = fileList.filter((f: any) => f.status === 'ready').length
  ElMessage.error('部分文件上传失败')
  if (uploadDone.value >= uploadTotal.value) uploading.value = false
}

function onImportNasPathSelected(path: string) {
  importNasPath.value = path === '.' ? '/' : '/' + path
}

async function startImportScan() {
  importScanning.value = true
  scanStatus.value = ''
  importScanTaskId.value = null
  try {
    const data = await request.post('/api/v1/photos/scan-nas', {
      project_id: Number(props.projectId),
      target_id: props.targetId,
      nas_path: importNasPath.value.replace(/^\//, ''),
      process_state: importProcessState.value,
      shot_date: importShotDate.value || null,
    })
    importScanTaskId.value = data.task_id
    scanStatus.value = 'queued'
    startScanPolling(data.task_id)
    ElMessage.success('扫描任务已提交')
  } catch (e: any) {
    ElMessage.error(e.message || '扫描失败')
  } finally {
    importScanning.value = false
  }
}

function startScanPolling(taskId: string) {
  stopScanPolling()
  scanPollTimer = setInterval(async () => {
    try {
      const data = await request.get(`/api/v1/photos/scan-nas/${taskId}/status`)
      scanStatus.value = data.status
      scanTotal.value = data.total
      scanProcessed.value = data.processed
      if (data.status === 'done' || data.status === 'failed') {
        stopScanPolling()
        if (data.status === 'done') {
          await fetchAllPhotos()
          ElMessage.success(`NAS 扫描完成，共 ${data.total} 张`)
        }
      }
    } catch {}
  }, 1500)
}

function stopScanPolling() {
  if (scanPollTimer) { clearInterval(scanPollTimer); scanPollTimer = null }
}

function closeImportDialog() {
  showImportDialog.value = false
  stopScanPolling()
  pendingFileCount.value = 0
  uploading.value = false
  uploadTotal.value = 0
  uploadDone.value = 0
}

// ── 数据获取 ───────────────────────────────────────────
async function fetchAllPhotos() {
  if (!props.projectId || props.projectId === 'undefined') {
    console.warn('[TargetDetail] projectId 无效，跳过照片拉取')
    return
  }

  loading.value = true
  photoSkip.value = 0
  try {
    const limit = 500
    let skip = 0
    let total = 0
    const items: PhotoItem[] = []
    do {
      const data = await request.get(`/api/v1/projects/${props.projectId}/photos`, { skip, limit })
      items.push(...(data.items || []))
      total = data.total || items.length
      skip += limit
    } while (items.length < total)
    allProjectPhotos.value = items
    photoTotal.value = total
    photoSkip.value = items.length
  } catch (e: any) {
    ElMessage.error(e.message || '获取照片失败')
  } finally {
    loading.value = false
  }
}

async function loadMorePhotos() {
  if (loading.value || !hasMorePhotos.value) return

  loading.value = true
  photoSkip.value += photoLimit
  try {
    const data = await request.get(`/api/v1/projects/${props.projectId}/photos`, { skip: photoSkip.value, limit: photoLimit })
    allProjectPhotos.value.push(...data.items)
  } catch (e: any) {
    ElMessage.error(e.message || '加载更多失败')
  } finally {
    loading.value = false
  }
}

async function fetchTargetInfo() {
  try {
    const data = await request.get(`/api/v1/projects/${props.projectId}/targets`)
    targetInfo.value = data.items.find((t: any) => t.id === props.targetId) || null
    if (targetInfo.value?.category_type === 'scene') {
      await fetchTargetReferences()
    }
  } catch {}
}

async function fetchProjectTags() {
  try {
    const data = await request.get(`/api/v1/projects/${props.projectId}/tags`)
    projectTags.value = data.items || []
  } catch {
    projectTags.value = []
  }
}

// ── 客户反馈轮询 ────────────────────────────────────────
async function fetchProjectFeedbacks() {
  try {
    const result = await request.get(`/api/v1/reviews/project/${props.projectId}/feedbacks`)
    if (result.code === 200 && result.data) {
      // 合并所有会话的反馈，最新的覆盖旧的
      const newMap = new Map<number, { is_confirmed: boolean; comment: string | null; annotation_path?: string | null }>()
      for (const session of result.data) {
        for (const feedback of session.feedbacks) {
          newMap.set(feedback.photo_id, {
            is_confirmed: feedback.is_confirmed,
            comment: feedback.comment,
            annotation_path: feedback.annotation_path || null,
          })
        }
      }
      feedbackMap.value = newMap
    }
  } catch {}
}

function startFeedbackPolling() {
  stopFeedbackPolling()
  fetchProjectFeedbacks() // 立即执行一次
  feedbackPollTimer = setInterval(fetchProjectFeedbacks, 30000) // 每 30 秒轮询
}

function stopFeedbackPolling() {
  if (feedbackPollTimer) {
    clearInterval(feedbackPollTimer)
    feedbackPollTimer = null
  }
}

onMounted(async () => {
  await Promise.all([fetchAllPhotos(), fetchTargetInfo(), fetchProjectTags()])
  startFeedbackPolling()
})

onUnmounted(() => {
  stopScanPolling()
  stopFeedbackPolling()
})
</script>

<style scoped>
.workspace-view { padding: 24px 32px; height: 100%; display: flex; flex-direction: column; overflow-y: auto; }
.workspace-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; flex-shrink: 0; }
.target-name { font-size: 20px; font-weight: 700; color: #2c3e50; margin: 0; }
.target-sub-name { font-size: 15px; color: #606266; font-weight: 500; }
.header-spacer { flex: 1; }

.status-badge { font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 10px; }
.badge-not_started    { background: #f0f2f5; color: #909399; }
.badge-shooting       { background: #ecf5ff; color: #409eff; }
.badge-retouching     { background: #fdf6ec; color: #e6a23c; }
.badge-client_review  { background: #f5f0ff; color: #9b59b6; }
.badge-completed      { background: #f0f9eb; color: #67c23a; }

.workspace-body { display: flex; flex-direction: column; gap: 24px; flex: 1; min-height: 0; }

.scene-reference-section {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.scene-goal-panel {
  padding: 16px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.scene-reference-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.reference-head {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 112px;
  font-size: 14px;
  font-weight: 700;
  color: #303133;
}

.reference-head.wide {
  margin-bottom: 12px;
}

.hint-icon {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #409eff;
  border: 1px solid #a0cfff;
  background: #ecf5ff;
  font-size: 12px;
  font-weight: 700;
  cursor: help;
}

.reference-preview {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
  font-size: 12px;
  color: #606266;
}

.reference-img {
  width: 56px;
  height: 56px;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
}

.reference-img-wrap {
  position: relative;
  width: 56px;
  height: 56px;
  flex-shrink: 0;
}

.reference-img :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.goal-preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 220px));
  gap: 12px;
}

.goal-preview-card {
  position: relative;
  height: 150px;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f7fa;
}

.goal-preview-card span {
  position: absolute;
  left: 8px;
  bottom: 8px;
  padding: 2px 7px;
  border-radius: 4px;
  background: rgba(0,0,0,0.55);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
}

.goal-reference-img {
  width: 100%;
  height: 100%;
}

.goal-reference-img :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.zoom-btn {
  position: absolute;
  bottom: 8px;
  left: 8px;
  width: 26px;
  height: 26px;
  display: none;
  align-items: center;
  justify-content: center;
  border: none;
  border-radius: 50%;
  background: rgba(255,255,255,0.92);
  color: #409eff;
  cursor: pointer;
  z-index: 4;
  font-size: 15px;
  font-weight: 700;
  box-shadow: 0 2px 4px rgba(0,0,0,0.15);
}

.zoom-btn.small {
  width: 22px;
  height: 22px;
  bottom: 4px;
  left: 4px;
}

.goal-preview-card:hover .zoom-btn,
.reference-img-wrap:hover .zoom-btn {
  display: flex;
}

.zoom-btn:hover { background: #409eff; color: #fff; }

.reference-empty {
  height: 112px;
  border-radius: 8px;
  border: 1px dashed #dcdfe6;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #909399;
  font-size: 13px;
  background: #fafafa;
}

.loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  color: #909399;
  font-size: 13px;
}

.no-more {
  text-align: center;
  padding: 16px;
  color: #c0c4cc;
  font-size: 12px;
}

/* 选图器 */
.picker-toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.picker-hint { font-size: 13px; color: #909399; }
.picker-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 8px; max-height: 400px; overflow-y: auto;
}
.photo-thumb {
  position: relative; border-radius: 8px; overflow: hidden; cursor: pointer;
  border: 2px solid transparent; transition: border-color 0.15s; aspect-ratio: 1;
}
.photo-thumb:hover { transform: scale(1.03); }
.photo-thumb.selected { border-color: #409eff; box-shadow: 0 0 0 2px rgba(64,158,255,0.3); }
.thumb-img { width: 100%; height: 100%; }
.thumb-img :deep(img) { width: 100%; height: 100%; object-fit: cover; }
.thumb-error { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #f5f7fa; color: #c0c4cc; }
.display-id-badge {
  position: absolute; top: 4px; left: 4px; font-size: 11px; font-weight: 700;
  color: white; background: rgba(0,0,0,0.55); padding: 1px 5px; border-radius: 4px;
}
.process-badge {
  position: absolute; left: 4px; bottom: 4px; font-size: 11px; font-weight: 700;
  color: #fff; padding: 1px 5px; border-radius: 4px; background: rgba(64, 158, 255, 0.9);
}
.process-badge.ps-retouched { background: rgba(230, 162, 60, 0.92); }
.process-badge.ps-final { background: rgba(103, 194, 58, 0.92); }
.scope-badge {
  position: absolute; right: 4px; bottom: 4px; font-size: 11px; font-weight: 700;
  color: #fff; padding: 1px 5px; border-radius: 4px; background: rgba(22, 119, 255, 0.9);
}
.scope-badge.muted { background: rgba(107, 114, 128, 0.9); }
.check-mark {
  position: absolute; top: 4px; right: 4px; width: 22px; height: 22px;
  background: #409eff; border-radius: 50%; display: flex; align-items: center;
  justify-content: center; color: white; font-size: 14px;
}

/* 导入弹窗 */
.import-form { max-height: 60vh; overflow-y: auto; }
.import-upload { width: 100%; }
.import-upload :deep(.el-upload-dragger) { width: 100%; padding: 20px 0; }
.nas-row { display: flex; gap: 8px; width: 100%; }
.nas-row .el-input { flex: 1; }
.nas-picker-trigger { cursor: pointer; color: var(--el-color-primary); font-size: 18px; }
.scan-status { display: flex; flex-direction: column; gap: 4px; width: 100%; }
.scan-status-text { font-size: 12px; color: #909399; }
.upload-confirm-row { display: flex; align-items: center; justify-content: space-between; width: 100%; gap: 12px; }
.pending-hint { font-size: 13px; color: #606266; }

.preview-mask {
  position: fixed;
  inset: 0;
  z-index: 3000;
  background: rgba(0, 0, 0, 0.88);
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-shell {
  position: relative;
  width: min(92vw, 1280px);
  height: min(88vh, 860px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.preview-image-wrap {
  max-width: 100%;
  max-height: calc(100% - 72px);
  display: flex;
  align-items: center;
  justify-content: center;
}

.preview-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 8px;
}

.preview-caption {
  margin-top: 12px;
  color: #fff;
  text-align: center;
}

.caption-line { font-size: 13px; opacity: 0.9; }
.caption-id { font-weight: 700; opacity: 1; }

.preview-close,
.preview-nav-close {
  position: absolute;
  border: none;
  color: white;
  background: rgba(255,255,255,0.16);
  cursor: pointer;
}

.preview-close {
  top: 10px;
  right: 10px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
}

.preview-nav-close {
  top: 50%;
  width: 48px;
  height: 72px;
  margin-top: -36px;
  border-radius: 8px;
  font-size: 42px;
}

.preview-nav-close.prev { left: 10px; }
.preview-nav-close.next { right: 10px; }
</style>
