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
          <el-image :src="thumbUrl(photo)" fit="cover" lazy class="final-thumb">
            <template #error><div class="thumb-error"><el-icon><PictureFilled /></el-icon></div></template>
          </el-image>

          <!-- 下载图标 -->
          <div
            v-if="photo.original_path"
            class="download-icon"
            @click.stop="downloadOriginal(photo)"
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
          <button class="zoom-btn" title="放大查看" @click.stop="emit('preview', photo)">⌕</button>
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

    <el-dialog v-model="showUploadDialog" title="选择完成图" width="720px" destroy-on-close>
      <el-form label-width="90px">
        <el-form-item label="关联精修图">
          <div class="source-photo-picker">
            <div class="source-photo-grid">
              <div
                v-for="p in confirmedRetouchedPhotos"
                :key="p.id"
                :class="['source-photo-card', { selected: uploadParentId === p.id }]"
                @click="uploadParentId = p.id"
              >
                <el-image :src="thumbUrl(p)" fit="cover" lazy class="source-photo-img">
                  <template #error><div class="thumb-error"><el-icon><PictureFilled /></el-icon></div></template>
                </el-image>
                <span class="display-id-badge">#{{ displayId(p) }}</span>
                <span v-if="p.retouch_quality" class="quality-badge">{{ qualityLabel(p.retouch_quality) }}</span>
                <button class="zoom-btn card-zoom" title="放大查看" @click.stop="emit('preview', p)">⌕</button>
                <div class="source-photo-name" :title="p.original_filename || ''">{{ p.original_filename || `#${displayId(p)}` }}</div>
              </div>
            </div>
            <el-empty v-if="confirmedRetouchedPhotos.length === 0" description="暂无精修图" :image-size="40" />
          </div>
        </el-form-item>
        <el-form-item label="生成方式">
          <el-radio-group v-model="finalSourceMode">
            <el-radio value="promote">直接使用精修图</el-radio>
            <el-radio value="upload">上传新完成图</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="最终图说明">
          <el-input v-model="uploadNotes" type="textarea" :rows="2" placeholder="最终图说明，可为空" />
        </el-form-item>
        <el-form-item v-if="finalSourceMode === 'upload'" label="上传文件">
          <el-upload
            ref="uploadRef"
            :auto-upload="false"
            :limit="1"
            accept=".jpg,.jpeg,.png,.tif,.tiff,.webp"
            :on-change="onFileChange"
          >
            <el-button type="primary" plain>选择文件</el-button>
          </el-upload>
        </el-form-item>
      </el-form>
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
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
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

const { downloadOriginal } = usePhotoDownload()
const showUploadDialog = ref(false)
const uploadParentId = ref<number | null>(null)
const uploadNotes = ref('')
const uploadFile = ref<File | null>(null)
const uploading = ref(false)
const uploadRef = ref()
const finalSourceMode = ref<'promote' | 'upload'>('promote')

const finalPhotos = computed(() =>
  props.photos.filter(p => p.process_state === 'final' && p.status !== 'deleted')
)

const confirmedRetouchedPhotos = computed(() =>
  props.photos.filter(p => p.process_state === 'retouched' && p.status !== 'deleted' && p.parent_id != null)
)

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
    uploadRef.value?.clearFiles?.()
    emit('uploaded')
  } catch (e: any) {
    ElMessage.error(e.message || '上传失败')
  } finally {
    uploading.value = false
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
  position: absolute; top: 8px; right: 8px;
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

.source-photo-picker {
  width: 100%;
}

.source-photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 10px;
  max-height: 300px;
  overflow-y: auto;
}

.source-photo-card {
  position: relative;
  aspect-ratio: 1;
  border: 2px solid transparent;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  background: #f5f7fa;
  transition: border-color 0.15s, transform 0.15s;
}

.source-photo-card:hover {
  transform: scale(1.03);
}

.source-photo-card.selected {
  border-color: #409eff;
  box-shadow: 0 0 0 2px rgba(64,158,255,0.3);
}

.source-photo-img,
.source-photo-img :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.display-id-badge {
  position: absolute;
  top: 4px;
  left: 4px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(0,0,0,0.55);
  color: white;
  font-size: 11px;
  font-weight: 700;
}

.quality-badge {
  position: absolute;
  top: 4px;
  right: 4px;
  padding: 2px 5px;
  border-radius: 4px;
  background: rgba(230, 162, 60, 0.92);
  color: white;
  font-size: 11px;
  font-weight: 700;
}

.source-photo-name {
  position: absolute;
  left: 4px;
  right: 4px;
  bottom: 4px;
  padding: 2px 4px;
  border-radius: 4px;
  background: rgba(0,0,0,0.55);
  color: white;
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.card-zoom {
  left: 6px;
  bottom: 28px;
}

.source-photo-card:hover .card-zoom {
  display: flex;
}

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
