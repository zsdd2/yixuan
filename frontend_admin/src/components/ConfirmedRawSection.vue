<template>
  <div class="section-card">
    <div class="section-header">
      <h3>确认原图</h3>
      <span class="section-count">已确认 {{ confirmedPhotos.length }} / 原图 {{ allRawPhotos.length }}</span>
      <div class="header-spacer" />
      <el-button size="small" type="primary" plain :disabled="selectedIds.size === 0" @click="confirmSelected">
        确认选中 ({{ selectedIds.size }})
      </el-button>
      <el-button size="small" @click="$emit('pick-photos')">
        从项目选图
      </el-button>
    </div>

    <!-- 待确认区 -->
    <div v-if="unconfirmedPhotos.length > 0" class="sub-section">
      <div class="sub-label">待确认</div>
      <div class="photo-grid">
        <div
          v-for="photo in unconfirmedPhotos"
          :key="photo.id"
          :class="['photo-thumb', { selected: selectedIds.has(photo.id) }]"
          @click="toggleSelect(photo.id)"
        >
          <el-image :src="thumbUrl(photo)" fit="cover" lazy class="thumb-img">
            <template #error><div class="thumb-error"><el-icon><PictureFilled /></el-icon></div></template>
          </el-image>
          <span class="display-id-badge">#{{ String(photo.display_id).padStart(3, '0') }}</span>
          <div class="photo-name-bar" v-if="photo.original_filename" :title="photo.original_filename">{{ truncName(photo.original_filename) }}</div>
          <div v-if="selectedIds.has(photo.id)" class="check-mark"><el-icon><Select /></el-icon></div>

          <!-- 下载图标 -->
          <div
            v-if="photo.original_path"
            class="download-icon"
            :class="{ 'show-on-selected': selectedIds.has(photo.id) }"
            @click.stop="downloadPreview(photo)"
            title="下载原图"
          >
            <el-icon><Download /></el-icon>
          </div>
          <button class="zoom-btn" title="放大查看" @click.stop="emit('preview', photo)">⌕</button>

          <button class="remove-btn remove-top-left" title="移出目标" @click.stop="removeFromTarget(photo)">✕</button>
        </div>
      </div>
    </div>

    <!-- 已确认区 -->
    <div v-if="confirmedPhotos.length > 0" class="sub-section">
      <div class="sub-label confirmed-label">已确认</div>
      <div class="photo-grid">
        <div v-for="photo in confirmedPhotos" :key="photo.id" class="photo-thumb confirmed">
          <el-image :src="thumbUrl(photo)" fit="cover" lazy class="thumb-img">
            <template #error><div class="thumb-error"><el-icon><PictureFilled /></el-icon></div></template>
          </el-image>
          <span class="display-id-badge">#{{ String(photo.display_id).padStart(3, '0') }}</span>
          <div class="photo-name-bar" v-if="photo.original_filename" :title="photo.original_filename">{{ truncName(photo.original_filename) }}</div>
          <span class="confirmed-badge">✓</span>

          <!-- 下载图标 -->
          <div
            v-if="photo.original_path"
            class="download-icon"
            @click.stop="downloadPreview(photo)"
            title="下载原图"
          >
            <el-icon><Download /></el-icon>
          </div>
          <button class="zoom-btn" title="放大查看" @click.stop="emit('preview', photo)">⌕</button>

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

          <button class="remove-btn remove-confirmed" title="取消确认" @click.stop="unconfirmPhoto(photo)">✕</button>
        </div>
      </div>
    </div>

    <el-empty v-if="allRawPhotos.length === 0" description="暂无原图，请先导入" :image-size="60" />
  </div>
</template>

<script setup lang="ts">
import { computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { PictureFilled, Select, Download } from '@element-plus/icons-vue'
import type { PhotoItem } from './TargetDetail.vue'
import { usePhotoDownload } from '../composables/usePhotoDownload'
import request from '../api/request'

const props = defineProps<{
  photos: PhotoItem[]
  feedbackMap: Map<number, { is_confirmed: boolean; comment: string | null; annotation_path?: string | null }>
}>()
const emit = defineEmits<{
  'pick-photos': []
  'confirmed': []
  'preview': [photo: PhotoItem]
}>()

const selectedIds = reactive(new Set<number>())
const { downloadPreview } = usePhotoDownload()

const allRawPhotos = computed(() => props.photos.filter(p => p.process_state === 'raw' && p.status !== 'deleted'))
const confirmedPhotos = computed(() =>
  allRawPhotos.value.filter(p => p.is_confirmed).sort((a, b) => a.display_id - b.display_id)
)
const unconfirmedPhotos = computed(() =>
  allRawPhotos.value.filter(p => !p.is_confirmed).sort((a, b) => a.display_id - b.display_id)
)

function truncName(name: string): string {
  return name.length > 18 ? name.slice(0, 16) + '…' : name
}

function thumbUrl(photo: PhotoItem): string {
  const path = photo.thumbnail_path || photo.original_path
  return `/storage/${path}`
}

function toggleSelect(id: number) {
  if (selectedIds.has(id)) selectedIds.delete(id)
  else selectedIds.add(id)
}

async function confirmSelected() {
  const ids = Array.from(selectedIds)
  if (ids.length === 0) return
  try {
    await request.post('/api/v1/photos/confirm-raw', { photo_ids: ids })
    for (const photo of props.photos) {
      if (selectedIds.has(photo.id)) photo.is_confirmed = true
    }
    selectedIds.clear()
    ElMessage.success(`已确认 ${ids.length} 张原图`)
    emit('confirmed')
  } catch (e: any) {
    ElMessage.error(e.message || '确认失败')
  }
}

async function removeFromTarget(photo: PhotoItem) {
  try {
    await request.patch('/api/v1/photos/bulk-update', { photo_ids: [photo.id], remove_from_target: true })
    photo.target_id = null
    selectedIds.delete(photo.id)
    ElMessage.success('已移出目标')
    emit('confirmed')
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  }
}

async function unconfirmPhoto(photo: PhotoItem) {
  try {
    await request.post('/api/v1/photos/unconfirm-raw', { photo_ids: [photo.id] })
    photo.is_confirmed = false
    ElMessage.success('已取消确认')
    emit('confirmed')
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  }
}
</script>

<style scoped>
.section-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.section-header h3 { margin: 0; font-size: 16px; font-weight: 700; color: #2c3e50; }
.section-count { font-size: 13px; color: #909399; }
.header-spacer { flex: 1; }

.sub-section { margin-bottom: 16px; }
.sub-label { font-size: 13px; font-weight: 600; color: #909399; margin-bottom: 8px; padding-left: 4px; }
.confirmed-label { color: #67c23a; }

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 8px;
}
.photo-thumb {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  transition: border-color 0.15s;
}
.photo-thumb:hover { transform: scale(1.03); }
.photo-thumb.selected { border-color: #409eff; box-shadow: 0 0 0 2px rgba(64,158,255,0.3); }
.photo-thumb.confirmed { border-color: #67c23a; cursor: default; }

.thumb-img { width: 100%; aspect-ratio: 1; }
.thumb-img :deep(img) { width: 100%; height: 100%; object-fit: cover; }
.thumb-error { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #f5f7fa; color: #c0c4cc; }

.display-id-badge {
  position: absolute; top: 4px; left: 4px;
  font-size: 11px; font-weight: 700; color: white;
  background: rgba(0,0,0,0.55); padding: 1px 5px; border-radius: 4px;
}
.check-mark {
  position: absolute; top: 4px; right: 4px;
  width: 22px; height: 22px; background: #409eff;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  color: white; font-size: 14px;
}
.confirmed-badge {
  position: absolute; top: 4px; right: 4px;
  width: 22px; height: 22px; background: #67c23a;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  color: white; font-size: 12px; font-weight: 700;
}

.photo-name-bar {
  padding: 3px 6px;
  font-size: 11px;
  color: #606266;
  background: #f8f9fb;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: center;
}

.remove-btn {
  position: absolute;
  width: 20px; height: 20px;
  background: rgba(0,0,0,0.5); border: none; border-radius: 50%;
  color: white; font-size: 12px; cursor: pointer;
  display: none; align-items: center; justify-content: center;
  line-height: 1; padding: 0; z-index: 2;
}
.photo-thumb:hover .remove-btn { display: flex; }
.remove-btn:hover { background: rgba(220,53,69,0.85); }

/* 待确认：X放左上角 display_id 右侧，不与右上角 check-mark 冲突 */
.remove-top-left { top: 4px; left: auto; right: auto; left: 52px; }

/* 已确认：hover 时 X 替代 confirmed-badge 位置 */
.remove-confirmed { top: 4px; right: 4px; }
.photo-thumb.confirmed:hover .confirmed-badge { display: none; }

/* 客户反馈标签 */
.client-feedback-badge {
  position: absolute;
  top: 30px;
  right: 4px;
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
  bottom: 4px;
  right: 4px;
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
  bottom: 4px;
  right: 30px;
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

/* 下载图标 */
.download-icon {
  position: absolute;
  bottom: 8px;
  left: 8px;
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

/* hover 时显示 */
.photo-thumb:hover .download-icon {
  display: flex;
}

/* selected 时显示 */
.download-icon.show-on-selected {
  display: flex;
}

/* hover 效果 */
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
  left: 40px;
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

.photo-thumb:hover .zoom-btn { display: flex; }
.zoom-btn:hover { background: #409eff; color: #fff; }

/* 移动端适配 */
@media (max-width: 768px) {
  .download-icon {
    width: 28px;
    height: 28px;
    display: flex;
    opacity: 0.85;
  }
  .download-icon.show-on-selected {
    opacity: 1;
  }
  .download-icon .el-icon {
    font-size: 16px;
  }
}
</style>
