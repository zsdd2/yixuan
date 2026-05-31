<template>
  <div class="section-card">
    <div class="section-header">
      <h3>完成图</h3>
      <span class="section-count">{{ finalPhotos.length }} 张</span>
      <div class="header-spacer" />
      <el-button
        type="primary"
        plain
        size="small"
        :disabled="confirmedRetouchedPhotos.length === 0"
        @click="showUploadDialog = true"
      >
        选择完成图
      </el-button>
      <el-button
        v-if="finalPhotos.length > 0"
        type="success"
        size="small"
        @click="$emit('complete-target')"
      >
        完成归档
      </el-button>
    </div>

    <div v-if="finalPhotos.length > 0" class="photo-grid">
      <div v-for="photo in finalPhotos" :key="photo.id" class="final-card">
        <div class="final-thumb-wrapper">
          <button type="button" class="cancel-final-btn" title="取消完成图" @click.stop="cancelFinalPhoto(photo)">×</button>
          <el-image :src="thumbUrl(photo)" fit="cover" lazy class="final-thumb">
            <template #error><div class="thumb-error"><el-icon><PictureFilled /></el-icon></div></template>
          </el-image>

          <!-- 下载图标 -->
          <div
            v-if="photo.original_path"
            class="download-icon"
            @click.stop="downloadPreview(photo)"
            title="下载原图"
          >
            <el-icon><Download /></el-icon>
          </div>

          <!-- 客户反馈标签 -->
          <div v-if="props.feedbackMap.has(photo.id)" class="client-feedback-badge">
            客户已确认
          </div>
          <div v-if="props.feedbackMap.get(photo.id)?.comment" class="client-comment-icon" :title="props.feedbackMap.get(photo.id)?.comment ?? undefined">
            💬
          </div>
          <a
            v-if="props.feedbackMap.get(photo.id)?.annotation_path"
            class="annotation-link"
            :href="`/storage/${props.feedbackMap.get(photo.id)?.annotation_path}`"
            target="_blank"
            title="查看修改示意图"
            @click.stop
          >示</a>
          <div v-if="photo.is_locked" class="locked-badge" title="已锁定，防止误删">
            🔒
          </div>

          <span class="final-badge">✓ FINAL</span>
          <button type="button" class="zoom-btn" title="放大查看" @click.stop="emit('preview', photo)">⌕</button>
        </div>

        <div class="final-info">
          <span class="final-id">#{{ String(photo.display_id).padStart(3, '0') }}</span>
          <span v-if="photo.original_filename" class="final-filename" :title="photo.original_filename">{{ photo.original_filename }}</span>
          <div v-if="photo.parent_id" class="source-trace">
            <span class="trace-label">来源：</span>
            <span class="trace-value">{{ sourceTrace(photo) }}</span>
          </div>
        </div>
      </div>
    </div>

    <el-empty v-if="finalPhotos.length === 0" description="暂无完成图" :image-size="60" />

    <el-dialog v-model="showUploadDialog" width="1180px" destroy-on-close class="image-select-dialog">
      <div class="image-select-layout">
        <aside class="select-left">
          <h2 class="select-title">选择完成图</h2>
          <div class="hero-preview">
            <el-image v-if="selectedRetouchedPhoto" :src="thumbUrl(selectedRetouchedPhoto)" fit="contain" class="hero-img" />
            <div v-else class="hero-empty">请选择关联精修图</div>
          </div>
          <div class="source-title">关联精修图</div>
          <div class="source-strip">
            <button type="button" class="strip-arrow" :disabled="selectedRetouchedIndex <= 0" @click="selectRetouchedByOffset(-1)">‹</button>
            <div
              v-for="p in visibleRetouchedPhotos"
              :key="p.id"
              :class="['strip-card', { selected: uploadParentId === p.id }]"
              @click="uploadParentId = p.id"
            >
              <el-image :src="thumbUrl(p)" fit="cover" class="strip-img" />
            </div>
            <button type="button" class="strip-arrow" :disabled="selectedRetouchedIndex >= confirmedRetouchedPhotos.length - 1" @click="selectRetouchedByOffset(1)">›</button>
          </div>
          <div class="strip-count">{{ selectedRetouchedIndex + 1 || 0 }} / {{ confirmedRetouchedPhotos.length }}</div>
        </aside>

        <section class="select-right">
          <el-form label-position="top" class="select-form">
            <el-form-item label="生成方式">
              <el-radio-group v-model="finalSourceMode" class="quality-options">
                <el-radio value="promote">直接使用精修图</el-radio>
                <el-radio value="upload">上传新完成图</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="最终图说明">
              <el-input
                v-model="uploadNotes"
                type="textarea"
                :rows="4"
                maxlength="200"
                show-word-limit
                placeholder="最终图说明，可为空"
              />
            </el-form-item>
            <el-form-item label="图片来源">
              <el-tabs v-model="finalSourceTab" class="source-tabs">
                <el-tab-pane label="从项目选择" name="existing">
                  <div class="mode-row">默认显示当前子项目中可生成完成图的精修图。</div>
                  <div class="design-photo-grid">
                    <div
                      v-for="p in confirmedRetouchedPhotos"
                      :key="p.id"
                      :class="['design-photo-card', { selected: uploadParentId === p.id }]"
                      @click="uploadParentId = p.id"
                    >
                      <el-image :src="thumbUrl(p)" fit="contain" lazy class="design-thumb">
                        <template #error><div class="thumb-error"><el-icon><PictureFilled /></el-icon></div></template>
                      </el-image>
                      <span v-if="p.retouch_quality" class="design-state state-retouched">{{ qualityLabel(p.retouch_quality) }}</span>
                      <button type="button" class="zoom-btn design-zoom" title="放大查看" @click.stop="emit('preview', p)">⌕</button>
                      <div class="design-card-footer">
                        <span>#{{ displayId(p) }}</span>
                        <span class="radio-dot" :class="{ checked: uploadParentId === p.id }"></span>
                      </div>
                    </div>
                  </div>
                  <el-empty v-if="confirmedRetouchedPhotos.length === 0" description="暂无精修图" :image-size="40" />
                </el-tab-pane>
                <el-tab-pane label="上传新文件" name="upload">
                  <el-upload
                    v-if="finalSourceMode === 'upload'"
                    ref="uploadRef"
                    :auto-upload="false"
                    :limit="1"
                    accept=".jpg,.jpeg,.png,.tif,.tiff,.webp"
                    :on-change="onFileChange"
                  >
                    <el-button type="primary" plain>选择文件</el-button>
                  </el-upload>
                  <span v-else class="upload-muted">切换为“上传新完成图”后可选择文件。</span>
                </el-tab-pane>
              </el-tabs>
            </el-form-item>
          </el-form>
        </section>
      </div>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploading" :disabled="!uploadParentId || (finalSourceMode === 'upload' && !uploadFile)" @click="uploadFinal">
          {{ finalSourceMode === 'promote' ? '确认生成' : '确认上传' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { PictureFilled, Download } from '@element-plus/icons-vue'
import type { PhotoItem } from './TargetDetail.vue'
import { usePhotoDownload } from '../composables/usePhotoDownload'
import request from '../api/request'

const props = defineProps<{
  photos: PhotoItem[]
  projectId: string | number
  targetId: number
  feedbackMap: Map<number, { is_confirmed: boolean; comment: string | null; annotation_path?: string | null }>
}>()
const emit = defineEmits<{ 'complete-target': [], 'uploaded': [], preview: [photo: PhotoItem] }>()

const { downloadPreview } = usePhotoDownload()
const showUploadDialog = ref(false)
const uploadParentId = ref<number | null>(null)
const uploadNotes = ref('')
const uploadFile = ref<File | null>(null)
const uploading = ref(false)
const uploadRef = ref()
const finalSourceMode = ref<'promote' | 'upload'>('promote')
const finalSourceTab = ref<'existing' | 'upload'>('existing')

watch(showUploadDialog, (visible) => {
  if (visible && uploadParentId.value == null && confirmedRetouchedPhotos.value.length > 0) {
    uploadParentId.value = confirmedRetouchedPhotos.value[0].id
  }
})

watch(finalSourceMode, (mode) => {
  if (mode === 'upload') finalSourceTab.value = 'upload'
  else finalSourceTab.value = 'existing'
})

const finalPhotos = computed(() =>
  props.photos.filter(p => p.process_state === 'final' && p.status !== 'deleted')
)

const confirmedRetouchedPhotos = computed(() =>
  props.photos.filter(p => p.process_state === 'retouched' && p.status !== 'deleted' && p.parent_id != null)
)

const selectedRetouchedPhoto = computed(() =>
  confirmedRetouchedPhotos.value.find(p => p.id === uploadParentId.value) || confirmedRetouchedPhotos.value[0] || null
)

const selectedRetouchedIndex = computed(() => {
  if (!selectedRetouchedPhoto.value) return -1
  return confirmedRetouchedPhotos.value.findIndex(p => p.id === selectedRetouchedPhoto.value!.id)
})

const visibleRetouchedPhotos = computed(() => {
  if (confirmedRetouchedPhotos.value.length <= 2) return confirmedRetouchedPhotos.value
  const index = selectedRetouchedIndex.value >= 0 ? selectedRetouchedIndex.value : 0
  const start = Math.min(Math.max(index, 0), Math.max(confirmedRetouchedPhotos.value.length - 2, 0))
  return confirmedRetouchedPhotos.value.slice(start, start + 2)
})

function selectRetouchedByOffset(offset: number) {
  if (confirmedRetouchedPhotos.value.length === 0) return
  const currentIndex = selectedRetouchedIndex.value >= 0 ? selectedRetouchedIndex.value : 0
  const nextIndex = Math.min(Math.max(currentIndex + offset, 0), confirmedRetouchedPhotos.value.length - 1)
  uploadParentId.value = confirmedRetouchedPhotos.value[nextIndex].id
}

function thumbUrl(photo: PhotoItem): string {
  const path = photo.thumbnail_path || photo.original_path
  return `/storage/${path}`
}

function displayId(photo: PhotoItem): string {
  return String(photo.display_id).padStart(3, '0')
}

function sourceTrace(photo: PhotoItem): string {
  if (!photo.parent_id) return '—'
  const retouched = props.photos.find(p => p.id === photo.parent_id)
  if (!retouched) return `精修图 ID${photo.parent_id}`
  const raw = retouched.parent_id ? props.photos.find(p => p.id === retouched.parent_id) : null
  return raw
    ? `精修图 #${displayId(retouched)} → 原图 #${displayId(raw)}`
    : `精修图 #${displayId(retouched)}`
}

function qualityLabel(value: string | null): string {
  const map: Record<string, string> = {
    generated: '生成图',
    generated_4k: '4K生成图',
    high_res: '高清图',
  }
  return value ? (map[value] || value) : ''
}

function onFileChange(file: any) {
  uploadFile.value = file.raw
}

async function uploadFinal() {
  if (!uploadParentId.value) return
  if (finalSourceMode.value === 'upload' && !uploadFile.value) return
  uploading.value = true
  try {
    if (finalSourceMode.value === 'promote') {
      await request.post(`/api/v1/photos/${uploadParentId.value}/promote-final`, {})
    } else {
      const fd = new FormData()
      fd.append('project_id', String(props.projectId))
      fd.append('target_id', String(props.targetId))
      fd.append('parent_id', String(uploadParentId.value))
      if (uploadNotes.value) fd.append('revision_notes', uploadNotes.value)
      fd.append('file', uploadFile.value!)
      await request.upload('/api/v1/photos/upload-final', fd)
    }
    ElMessage.success('完成图生成成功')
    showUploadDialog.value = false
    uploadParentId.value = null
    uploadNotes.value = ''
    uploadFile.value = null
    finalSourceMode.value = 'promote'
    finalSourceTab.value = 'existing'
    uploadRef.value?.clearFiles?.()
    emit('uploaded')
  } catch (e: any) {
    ElMessage.error(e.message || '上传失败')
  } finally {
    uploading.value = false
  }
}

async function cancelFinalPhoto(photo: PhotoItem) {
  try {
    await ElMessageBox.confirm(
      '确定取消这张完成图吗？取消后会从完成图中移除，关联的精修图/原图仍保留。',
      '取消完成图',
      { type: 'warning', confirmButtonText: '确定取消', cancelButtonText: '返回' }
    )
    await request.patch('/api/v1/photos/bulk-update', {
      photo_ids: [photo.id],
      status: 'deleted',
    })
    ElMessage.success('已取消完成图')
    emit('uploaded')
  } catch (e: any) {
    if (e !== 'cancel' && e !== 'close') {
      ElMessage.error(e.message || '取消失败')
    }
  }
}
</script>

<style scoped>
.section-card { background: white; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
.section-header { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.section-header h3 { margin: 0; font-size: 16px; font-weight: 700; color: #2c3e50; }
.section-count { font-size: 13px; color: #909399; }
.header-spacer { flex: 1; }

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.final-card {
  position: relative;
  border: 2px solid #67c23a;
  border-radius: 10px;
  overflow: hidden;
  background: #f0f9eb;
}

.final-thumb-wrapper { position: relative; width: 100%; aspect-ratio: 1; }
.final-thumb { width: 100%; height: 100%; }
.final-thumb :deep(img) { width: 100%; height: 100%; object-fit: cover; }
.thumb-error { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #f5f7fa; color: #c0c4cc; }

.cancel-final-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 8;
  width: 24px;
  height: 24px;
  border: none;
  border-radius: 50%;
  background: rgba(239, 68, 68, 0.94);
  color: #fff;
  font-size: 18px;
  line-height: 22px;
  cursor: pointer;
  display: none;
  align-items: center;
  justify-content: center;
}

.final-thumb-wrapper:hover .cancel-final-btn { display: flex; }
.cancel-final-btn:hover { background: #dc2626; }

/* 客户反馈标签 */
.client-feedback-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  font-size: 10px;
  font-weight: 600;
  color: white;
  background: #ef4444;
  padding: 2px 6px;
  border-radius: 4px;
  white-space: nowrap;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  z-index: 3;
}

.client-comment-icon {
  position: absolute;
  bottom: 8px;
  right: 8px;
  font-size: 18px;
  cursor: pointer;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
  z-index: 3;
  transition: transform 0.2s;
}

.client-comment-icon:hover {
  transform: scale(1.2);
}

.annotation-link {
  position: absolute;
  bottom: 8px;
  right: 34px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #f59e0b;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
  z-index: 4;
}

.locked-badge {
  position: absolute;
  bottom: 8px;
  left: 8px;
  font-size: 16px;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.3));
  z-index: 3;
}

.final-info { padding: 8px 10px; }
.final-id { font-size: 14px; font-weight: 700; color: #2c3e50; }
.final-filename { font-size: 11px; color: #909399; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.source-trace { font-size: 12px; color: #909399; margin-top: 4px; }
.trace-label { font-weight: 600; }
.trace-value { color: #606266; }

.final-badge {
  position: absolute; top: 8px; right: 38px;
  background: #67c23a; color: white;
  font-size: 11px; font-weight: 700;
  padding: 2px 8px; border-radius: 4px;
}

/* 下载图标 */
.download-icon {
  position: absolute;
  bottom: 8px;
  left: 36px;
  width: 24px;
  height: 24px;
  display: none;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(8px);
  border-radius: 50%;
  cursor: pointer;
  z-index: 3;
  transition: all 0.2s;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
}

.final-thumb-wrapper:hover .download-icon {
  display: flex;
}

.download-icon:hover {
  background: rgba(64, 158, 255, 0.95);
  transform: scale(1.1);
}

.download-icon .el-icon {
  font-size: 14px;
  color: #409eff;
}

.download-icon:hover .el-icon {
  color: white;
}

.zoom-btn {
  position: absolute;
  bottom: 8px;
  left: 66px;
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

.final-thumb-wrapper:hover .zoom-btn { display: flex; }
.zoom-btn:hover { background: #409eff; color: #fff; }

.image-select-dialog :deep(.el-dialog) { border-radius: 12px; }
.image-select-dialog :deep(.el-dialog__header) { padding: 0; }
.image-select-dialog :deep(.el-dialog__body) { padding: 44px 42px 28px; }
.image-select-layout {
  display: grid;
  grid-template-columns: 360px minmax(0, 1fr);
  gap: 42px;
  min-height: 650px;
}
.select-left {
  display: flex;
  flex-direction: column;
  border-right: 1px solid #eadfce;
  padding-right: 26px;
}
.select-title {
  margin: 0 0 58px;
  font-size: 34px;
  line-height: 1.1;
  font-weight: 500;
  color: #2f2a27;
}
.hero-preview {
  width: 100%;
  border-radius: 6px;
  overflow: hidden;
  background: #f6f3ef;
  display: block;
}

.hero-img {
  width: 100%;
  height: auto;
  display: block;
}

.hero-img :deep(img) {
  width: 100%;
  height: auto;
  object-fit: contain;
  display: block;
}
.hero-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #b59b78;
}
.source-title {
  margin: 32px 0 16px;
  color: #aa8253;
  font-size: 16px;
  font-weight: 700;
}
.source-strip {
  display: flex;
  gap: 12px;
  align-items: center;
  overflow: hidden;
}
.strip-card {
  width: 82px;
  height: 82px;
  border: 2px solid transparent;
  border-radius: 6px;
  overflow: hidden;
  cursor: pointer;
  background: #f5f5f5;
}
.strip-card.selected { border-color: #c7a477; }
.strip-img,
.strip-img :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.strip-arrow {
  border: none;
  background: transparent;
  color: #b8905d;
  font-size: 32px;
  cursor: pointer;
}
.strip-arrow:disabled { opacity: 0.35; cursor: default; }
.strip-count {
  margin-top: 24px;
  color: #b8905d;
  font-size: 20px;
  letter-spacing: 1px;
}
.select-right { padding-top: 58px; }
.select-form :deep(.el-form-item__label) {
  color: #303133;
  font-size: 15px;
  font-weight: 700;
}
.select-form :deep(.el-textarea__inner) {
  min-height: 102px !important;
  border-radius: 6px;
}
.quality-options {
  display: flex;
  gap: 72px;
}
.source-tabs { width: 100%; }
.source-tabs :deep(.el-tabs__item) {
  font-size: 17px;
  padding: 0 32px;
}
.source-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background: #eadfce;
}
.source-tabs :deep(.el-tabs__active-bar) {
  height: 2px;
  background: #2f7eea;
}
.mode-row {
  margin: 14px 0 18px;
  color: #9b9b9b;
  font-size: 13px;
}
.design-photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
  max-height: 300px;
  overflow-y: auto;
}
.design-photo-card {
  position: relative;
  border: 2px solid #eadfce;
  border-radius: 8px;
  overflow: hidden;
  background: #fff;
  cursor: pointer;
}
.design-photo-card.selected { border-color: #2f7eea; }
.design-thumb {
  width: 100%;
  height: auto;
  min-height: 0;
  background: #f5f5f5;
  display: block;
}
.design-thumb :deep(img) {
  width: 100%;
  height: auto;
  object-fit: contain;
  display: block;
}
.design-state {
  position: absolute;
  top: 10px;
  right: 10px;
  border-radius: 4px;
  padding: 3px 7px;
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  background: #7c4ee8;
}
.design-card-footer {
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 10px;
  font-size: 15px;
  color: #2f2a27;
}
.radio-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 2px solid #dfcfc0;
}
.radio-dot.checked {
  border-color: #2f7eea;
  background: #2f7eea;
  box-shadow: inset 0 0 0 4px #fff;
}
.design-zoom {
  left: 8px;
  bottom: 46px;
}
.design-photo-card:hover .design-zoom { display: flex; }
.upload-muted { color: #909399; font-size: 13px; }

@media (max-width: 768px) {
  .download-icon {
    width: 28px;
    height: 28px;
    display: flex;
    opacity: 0.85;
  }
  .download-icon .el-icon {
    font-size: 16px;
  }
}
</style>
