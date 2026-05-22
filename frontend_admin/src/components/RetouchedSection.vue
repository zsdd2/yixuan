<template>
  <div class="section-card">
    <div class="section-header">
      <h3>精修图</h3>
      <span class="section-count">{{ retouchedPhotos.length }} 张精修 · {{ groupedByParent.length }} 组原图</span>
      <div class="header-spacer" />
      <el-button size="small" type="warning" plain @click="showUploadDialog = true">
        选择图片
      </el-button>
    </div>

    <div v-if="groupedByParent.length > 0" class="retouch-board">
      <div v-for="group in groupedByParent" :key="group.parentId" class="retouch-pair" @click="openGroupDetail(group)">
        <div class="pair-side">
          <div class="pair-label">原图</div>
          <el-image :src="thumbUrl(group.parentPhoto)" fit="cover" lazy class="pair-img">
            <template #error><div class="thumb-error"><el-icon><PictureFilled /></el-icon></div></template>
          </el-image>
          <span class="display-id-badge">#{{ displayId(group.parentPhoto) }}</span>
          <button class="zoom-btn" title="放大查看" @click.stop="emit('preview', group.parentPhoto)">⌕</button>
        </div>
        <div class="pair-arrow">→</div>
        <div class="pair-side latest">
          <div class="pair-label">
            最新精修
            <el-tag v-if="group.latest.retouch_quality" size="small" type="success">{{ qualityLabel(group.latest.retouch_quality) }}</el-tag>
          </div>
          <el-image :src="thumbUrl(group.latest)" fit="cover" lazy class="pair-img">
            <template #error><div class="thumb-error"><el-icon><PictureFilled /></el-icon></div></template>
          </el-image>
          <span class="display-id-badge">#{{ displayId(group.latest) }}</span>
          <span class="version-badge">V{{ group.latest.version }}</span>
          <button class="zoom-btn" title="放大查看" @click.stop="emit('preview', group.latest)">⌕</button>
        </div>
        <div class="pair-meta">
          <span>{{ group.versions.length }} 个版本</span>
          <span v-if="group.latest.revision_notes">{{ group.latest.revision_notes }}</span>
          <span v-if="group.latest.client_notes" class="client-note">客户：{{ group.latest.client_notes }}</span>
        </div>
      </div>
    </div>

    <el-empty v-if="retouchedPhotos.length === 0" description="暂无精修图" :image-size="60" />

    <el-dialog v-model="showDetailDialog" title="精修迭代详情" width="92vw" top="4vh" destroy-on-close class="retouch-detail-dialog">
      <div v-if="activeGroup" class="detail-layout">
        <div class="detail-raw">
          <div class="detail-title">原始图 #{{ displayId(activeGroup.parentPhoto) }}</div>
          <div class="detail-raw-wrap">
            <el-image :src="thumbUrl(activeGroup.parentPhoto)" fit="contain" class="detail-raw-img" />
            <button class="zoom-btn detail" title="放大查看" @click="emit('preview', activeGroup.parentPhoto)">⌕</button>
          </div>
          <div v-if="activeGroup.parentPhoto.original_filename" class="detail-filename">{{ activeGroup.parentPhoto.original_filename }}</div>
        </div>
        <div class="detail-versions">
          <div v-for="versionGroup in activeVersionGroups" :key="versionGroup.version" class="version-group-card">
            <div class="version-group-head">
              <el-tag type="warning" size="small">V{{ versionGroup.version }}</el-tag>
              <span>{{ versionGroup.items.length }} 张</span>
              <span>{{ formatDateTime(versionGroup.latestTime) }}</span>
            </div>
            <div v-for="ver in versionGroup.items" :key="ver.id" class="version-detail-card">
              <div class="version-img-wrap">
                <el-image :src="thumbUrl(ver)" fit="cover" lazy class="version-detail-img">
                  <template #error><div class="thumb-error"><el-icon><PictureFilled /></el-icon></div></template>
                </el-image>
                <button class="zoom-btn detail" title="放大查看" @click="emit('preview', ver)">⌕</button>
              </div>
              <div class="version-detail-meta">
                <div class="version-detail-head">
                  <el-tag v-if="ver.retouch_quality" type="success" size="small">{{ qualityLabel(ver.retouch_quality) }}</el-tag>
                  <span>#{{ displayId(ver) }}</span>
                  <span class="iteration-time">{{ formatDateTime(ver.created_at) }}</span>
                  <div class="version-spacer" />
                  <el-button size="small" text type="primary" @click="editNotes(ver)">编辑备注</el-button>
                  <el-button size="small" text type="danger" @click="deleteVersion(ver)">删除</el-button>
                </div>
                <div v-if="ver.revision_notes" class="meta-line"><b>修改内容：</b>{{ ver.revision_notes }}</div>
                <div v-else class="meta-line muted">暂无修改内容</div>
                <div v-if="ver.client_notes" class="meta-line client-note"><b>客户备注：</b>{{ ver.client_notes }}</div>
                <div v-if="props.feedbackMap.get(ver.id)?.comment" class="meta-line client-note"><b>客户反馈：</b>{{ props.feedbackMap.get(ver.id)?.comment }}</div>
                <a
                  v-if="props.feedbackMap.get(ver.id)?.annotation_path"
                  class="annotation-link"
                  :href="`/storage/${props.feedbackMap.get(ver.id)?.annotation_path}`"
                  target="_blank"
                >查看修改示意图</a>
                <div v-if="ver.is_locked || props.feedbackMap.get(ver.id)?.is_confirmed" class="confirmed-line">客户已确认</div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>

    <el-dialog v-model="showUploadDialog" title="选择精修图" width="640px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="源原图">
          <el-select v-model="uploadParentId" placeholder="选择已确认的原图" filterable style="width: 100%">
            <el-option
              v-for="p in confirmedRaws"
              :key="p.id"
              :label="`#${displayId(p)} ${p.original_filename || ''}`"
              :value="p.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="修改说明">
          <el-input v-model="uploadRevisionNotes" type="textarea" :rows="2" placeholder="本次修改的内容说明" />
        </el-form-item>
        <el-form-item label="精修分类">
          <el-radio-group v-model="uploadRetouchQuality">
            <el-radio value="generated">生成图</el-radio>
            <el-radio value="generated_4k">4K生成图</el-radio>
            <el-radio value="high_res">高清图</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="图片来源">
          <el-tabs v-model="sourceTab" class="source-tabs">
            <el-tab-pane label="从项目选择" name="existing">
              <div class="existing-photo-grid">
                <div
                  v-for="photo in selectablePhotos"
                  :key="photo.id"
                  :class="['photo-thumb', { selected: selectedExistingIds.has(photo.id) }]"
                  @click="toggleExistingSelection(photo.id)"
                >
                  <el-image :src="thumbUrl(photo)" fit="cover" lazy class="thumb-img">
                    <template #error><div class="thumb-error">-</div></template>
                  </el-image>
                  <span class="display-id-badge">#{{ displayId(photo) }}</span>
                  <div v-if="selectedExistingIds.has(photo.id)" class="check-mark">✓</div>
                </div>
              </div>
              <el-empty v-if="selectablePhotos.length === 0" description="暂无可选照片" :image-size="40" />
            </el-tab-pane>
            <el-tab-pane label="上传新文件" name="upload">
              <el-upload
                ref="retouchUploadRef"
                :auto-upload="false"
                multiple
                accept=".jpg,.jpeg,.png,.tif,.tiff,.webp"
                :on-change="onRetouchFileChange"
                :on-remove="onRetouchFileRemove"
              >
                <el-button type="primary" plain>选择文件</el-button>
              </el-upload>
            </el-tab-pane>
          </el-tabs>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button
          type="primary"
          :loading="uploading"
          :disabled="!uploadParentId || (sourceTab === 'existing' ? selectedExistingIds.size === 0 : retouchFiles.length === 0)"
          @click="doUpload"
        >
          确认
        </el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showNotesDialog" title="编辑备注" width="450px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="修改说明">
          <el-input v-model="editingRevisionNotes" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="客户备注">
          <el-input v-model="editingClientNotes" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showNotesDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingNotes" @click="saveNotes">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { PictureFilled } from '@element-plus/icons-vue'
import type { PhotoItem } from './TargetDetail.vue'
import request from '../api/request'

const props = defineProps<{
  photos: PhotoItem[]
  projectPhotos: PhotoItem[]
  projectId: string | number
  targetId: number
  feedbackMap: Map<number, { is_confirmed: boolean; comment: string | null; annotation_path?: string | null }>
}>()

const emit = defineEmits<{ uploaded: [], preview: [photo: PhotoItem] }>()

interface VersionGroup {
  parentId: number
  parentPhoto: PhotoItem
  latest: PhotoItem
  versions: PhotoItem[]
}

const retouchedPhotos = computed(() =>
  props.photos.filter(p => p.process_state === 'retouched' && p.status !== 'deleted')
)

const confirmedRaws = computed(() =>
  props.photos.filter(p => p.process_state === 'raw' && (p.is_confirmed || p.is_locked) && p.status !== 'deleted')
)

const groupedByParent = computed<VersionGroup[]>(() => {
  const map = new Map<number, PhotoItem[]>()
  for (const p of retouchedPhotos.value) {
    if (p.parent_id == null) continue
    if (!map.has(p.parent_id)) map.set(p.parent_id, [])
    map.get(p.parent_id)!.push(p)
  }

  const groups: VersionGroup[] = []
  for (const [parentId, versions] of map) {
    const parentPhoto = props.photos.find(p => p.id === parentId)
    if (!parentPhoto) continue
    versions.sort((a, b) => (b.version - a.version) || (b.id - a.id))
    groups.push({ parentId, parentPhoto, latest: versions[0], versions })
  }
  return groups.sort((a, b) => a.parentPhoto.display_id - b.parentPhoto.display_id)
})

const showDetailDialog = ref(false)
const activeGroup = ref<VersionGroup | null>(null)
const activeVersionGroups = computed(() => {
  if (!activeGroup.value) return []
  const map = new Map<number, PhotoItem[]>()
  for (const photo of activeGroup.value.versions) {
    if (!map.has(photo.version)) map.set(photo.version, [])
    map.get(photo.version)!.push(photo)
  }
  return Array.from(map.entries())
    .map(([version, items]) => {
      items.sort((a, b) => (b.id - a.id))
      return {
        version,
        items,
        latestTime: items.reduce((latest, item) => {
          if (!latest) return item.created_at
          return new Date(item.created_at).getTime() > new Date(latest).getTime() ? item.created_at : latest
        }, ''),
      }
    })
    .sort((a, b) => b.version - a.version)
})

function openGroupDetail(group: VersionGroup) {
  activeGroup.value = group
  showDetailDialog.value = true
}

function thumbUrl(photo: PhotoItem): string {
  const path = photo.thumbnail_path || photo.original_path
  return `/storage/${path}`
}

function displayId(photo: PhotoItem): string {
  return String(photo.display_id).padStart(3, '0')
}

function qualityLabel(value: string | null): string {
  const map: Record<string, string> = {
    generated: '生成图',
    generated_4k: '4K生成图',
    high_res: '高清图',
  }
  return value ? (map[value] || value) : ''
}

function formatDateTime(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

async function deleteVersion(photo: PhotoItem) {
  const label = `V${photo.version} #${displayId(photo)}`
  try {
    await ElMessageBox.confirm(`确定删除精修版本 ${label}？该操作会解除与源原图的关联。`, '删除精修图', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch { return }
  try {
    await request.post('/api/v1/photos/bulk-soft-delete', { photo_ids: [photo.id] })
    photo.status = 'deleted'
    ElMessage.success(`精修版本 ${label} 已删除`)
    emit('uploaded')
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

const showUploadDialog = ref(false)
const uploadParentId = ref<number | null>(null)
const uploadRevisionNotes = ref('')
const uploadRetouchQuality = ref<'generated' | 'generated_4k' | 'high_res'>('generated')
const retouchUploadRef = ref()
const retouchFiles = ref<File[]>([])
const uploading = ref(false)
const sourceTab = ref<'existing' | 'upload'>('existing')
const selectedExistingIds = ref(new Set<number>())

const selectablePhotos = computed(() =>
  props.projectPhotos.filter(p => p.status !== 'deleted' && p.process_state !== 'retouched' && p.process_state !== 'final')
)

function toggleExistingSelection(id: number) {
  const next = new Set(selectedExistingIds.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  selectedExistingIds.value = next
}

function onRetouchFileChange(_file: any, files: any[]) {
  retouchFiles.value = files.map(item => item.raw).filter(Boolean)
}

function onRetouchFileRemove(_file: any, files: any[]) {
  retouchFiles.value = files.map(item => item.raw).filter(Boolean)
}

async function doUpload() {
  if (!uploadParentId.value) return
  uploading.value = true
  try {
    const batchId = `retouch-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`

    if (sourceTab.value === 'existing') {
      const ids = Array.from(selectedExistingIds.value)
      if (ids.length === 0) return
      for (const id of ids) {
        const fd = buildRetouchForm(batchId)
        fd.append('existing_photo_id', String(id))
        await request.upload('/api/v1/photos/upload-retouched', fd)
      }
      ElMessage.success(`已关联 ${ids.length} 张精修图`)
    } else {
      if (retouchFiles.value.length === 0) return
      for (const file of retouchFiles.value) {
        const fd = buildRetouchForm(batchId)
        fd.append('file', file)
        await request.upload('/api/v1/photos/upload-retouched', fd)
      }
      ElMessage.success(`已上传 ${retouchFiles.value.length} 张精修图`)
      resetDialog()
      emit('uploaded')
      return
    }

    resetDialog()
    emit('uploaded')
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  } finally {
    uploading.value = false
  }
}

function buildRetouchForm(batchId: string) {
  const fd = new FormData()
  fd.append('project_id', String(props.projectId))
  fd.append('target_id', String(props.targetId))
  fd.append('parent_id', String(uploadParentId.value))
  if (uploadRevisionNotes.value) fd.append('revision_notes', uploadRevisionNotes.value)
  fd.append('retouch_quality', uploadRetouchQuality.value)
  fd.append('retouch_batch_id', batchId)
  return fd
}

function resetDialog() {
  showUploadDialog.value = false
  uploadParentId.value = null
  uploadRevisionNotes.value = ''
  uploadRetouchQuality.value = 'generated'
  retouchFiles.value = []
  selectedExistingIds.value = new Set()
  sourceTab.value = 'existing'
  retouchUploadRef.value?.clearFiles?.()
}

const showNotesDialog = ref(false)
const editingPhotoId = ref<number | null>(null)
const editingRevisionNotes = ref('')
const editingClientNotes = ref('')
const savingNotes = ref(false)

function editNotes(photo: PhotoItem) {
  editingPhotoId.value = photo.id
  editingRevisionNotes.value = photo.revision_notes || ''
  editingClientNotes.value = photo.client_notes || ''
  showNotesDialog.value = true
}

async function saveNotes() {
  if (editingPhotoId.value == null) return
  savingNotes.value = true
  try {
    await request.patch(`/api/v1/photos/${editingPhotoId.value}/notes`, {
      revision_notes: editingRevisionNotes.value,
      client_notes: editingClientNotes.value,
    })
    const photo = props.photos.find(p => p.id === editingPhotoId.value)
    if (photo) {
      photo.revision_notes = editingRevisionNotes.value
      photo.client_notes = editingClientNotes.value
    }
    showNotesDialog.value = false
    ElMessage.success('备注已保存')
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    savingNotes.value = false
  }
}
</script>

<style scoped>
.section-card { background: white; border-radius: 8px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.section-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.section-header h3 { margin: 0; font-size: 16px; font-weight: 700; color: #2c3e50; }
.section-count { font-size: 13px; color: #909399; }
.header-spacer, .version-spacer { flex: 1; }

.retouch-board {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(420px, 1fr));
  gap: 14px;
}

.retouch-pair {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 24px minmax(0, 1fr);
  gap: 12px;
  align-items: center;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  cursor: pointer;
  background: #fff;
}

.retouch-pair:hover {
  border-color: #e6a23c;
  box-shadow: 0 6px 18px rgba(0,0,0,0.08);
}

.pair-side {
  position: relative;
  min-width: 0;
}

.pair-label {
  height: 24px;
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: #606266;
}

.pair-img {
  width: 100%;
  aspect-ratio: 4 / 3;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f7fa;
  cursor: zoom-in;
}

.pair-img :deep(img), .thumb-img :deep(img), .version-detail-img :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.pair-arrow {
  align-self: center;
  color: #c0c4cc;
  font-size: 18px;
  font-weight: 700;
}

.pair-meta {
  grid-column: 1 / -1;
  display: flex;
  gap: 10px;
  min-height: 20px;
  color: #909399;
  font-size: 12px;
  overflow: hidden;
}

.pair-meta span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.display-id-badge, .version-badge {
  position: absolute;
  top: 32px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(0,0,0,0.55);
  color: white;
  font-size: 11px;
  font-weight: 700;
}

.display-id-badge { left: 6px; }
.version-badge { right: 6px; background: rgba(230,162,60,0.9); }

.client-note { color: #e6a23c; }
.thumb-error { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #f5f7fa; color: #c0c4cc; }

.detail-layout {
  display: grid;
  grid-template-columns: minmax(320px, 42%) minmax(360px, 1fr);
  gap: 18px;
  height: 78vh;
  min-height: 520px;
}

.detail-raw, .detail-versions {
  min-height: 0;
}

.detail-raw-wrap,
.version-img-wrap {
  position: relative;
}

.detail-raw-wrap {
  height: calc(100% - 52px);
}

.detail-title {
  font-size: 14px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 10px;
}

.detail-raw-img {
  width: 100%;
  height: 100%;
  border-radius: 8px;
  background: #f5f7fa;
  cursor: zoom-in;
}

.detail-filename {
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.detail-versions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  padding-right: 6px;
}

.version-detail-card {
  display: grid;
  grid-template-columns: 180px minmax(0, 1fr);
  gap: 12px;
  padding: 12px;
  border: 1px solid #ebeef5;
  border-radius: 8px;
}

.version-group-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}

.version-group-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  color: #606266;
  font-size: 12px;
}

.version-group-card .version-detail-card {
  border-color: #f0f2f5;
}

.version-group-card .version-detail-card + .version-detail-card {
  margin-top: 10px;
}

.version-detail-img {
  width: 180px;
  height: 136px;
  border-radius: 8px;
  overflow: hidden;
  cursor: zoom-in;
}

.version-img-wrap {
  width: 180px;
  height: 136px;
}

.zoom-btn {
  position: absolute;
  bottom: 8px;
  left: 8px;
  width: 24px;
  height: 24px;
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

.pair-side:hover .zoom-btn,
.detail-raw-wrap:hover .zoom-btn,
.version-img-wrap:hover .zoom-btn {
  display: flex;
}

.zoom-btn:hover { background: #409eff; color: #fff; }

.version-detail-meta {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.version-detail-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.iteration-time {
  color: #909399;
  font-size: 12px;
}

.meta-line {
  font-size: 13px;
  color: #606266;
  line-height: 1.5;
}

.muted { color: #c0c4cc; }
.confirmed-line { font-size: 12px; color: #67c23a; font-weight: 700; }
.annotation-link {
  font-size: 12px;
  color: #409eff;
  font-weight: 700;
  text-decoration: none;
}

.source-tabs { width: 100%; }
.existing-photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
  gap: 8px;
  max-height: 280px;
  overflow-y: auto;
}

.photo-thumb {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  transition: border-color 0.15s;
  aspect-ratio: 1;
}

.photo-thumb:hover { transform: scale(1.03); }
.photo-thumb.selected { border-color: #409eff; box-shadow: 0 0 0 2px rgba(64,158,255,0.3); }
.thumb-img { width: 100%; height: 100%; }
.check-mark {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  background: #409eff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 12px;
  font-weight: 700;
}

@media (max-width: 900px) {
  .retouch-board { grid-template-columns: 1fr; }
  .detail-layout { grid-template-columns: 1fr; height: auto; }
  .detail-raw-img { height: 320px; }
  .version-detail-card { grid-template-columns: 120px minmax(0, 1fr); }
  .version-detail-img { width: 120px; height: 96px; }
}
</style>


