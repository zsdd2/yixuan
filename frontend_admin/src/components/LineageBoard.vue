<template>
  <div class="lb-root">
    <!-- 顶部 -->
    <div class="lb-topbar">
      <button class="lb-back" @click="$emit('back')">
        <svg viewBox="0 0 20 20" fill="currentColor" class="ic"><path fill-rule="evenodd" d="M17 10a.75.75 0 01-.75.75H5.612l4.158 3.96a.75.75 0 11-1.04 1.08l-5.5-5.25a.75.75 0 010-1.08l5.5-5.25a.75.75 0 011.04 1.08L5.612 9.25H16.25A.75.75 0 0117 10z" clip-rule="evenodd" /></svg>
        返回看板
      </button>
      <h2 class="lb-title">项目工作台 — 工作进度</h2>
      <button class="lb-shuttle-btn" @click="$emit('open-shuttle')">📷 照片整理</button>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="lb-loading">加载中...</div>

    <!-- 垂直任务链 -->
    <div v-else class="lb-chains" v-infinite-scroll="loadMorePhotos" :infinite-scroll-disabled="loading || !hasMorePhotos" :infinite-scroll-distance="200">
      <div v-if="chains.length === 0" class="lb-empty">该目标暂无照片，请先导入</div>

      <div v-for="chain in chains" :key="chain.raw.id" class="chain-block">
        <!-- ═══ 原图区 ═══ -->
        <div class="chain-raw">
          <div class="chain-raw-card">
            <img :src="storageUrl(chain.raw.thumbnail_path || chain.raw.original_path)" class="chain-img" />
            <div class="chain-raw-meta">
              <span class="raw-tag">#RAW-{{ String(chain.raw.display_id).padStart(3, '0') }}</span>
              <span v-if="chain.raw.is_confirmed" class="raw-confirmed">✓ 已确认</span>
              <span class="raw-file">ID {{ chain.raw.id }}</span>
            </div>
          </div>
        </div>

        <!-- 连接线 -->
        <div class="chain-line">
          <div class="line-dot" />
          <div class="line-bar" />
          <div class="line-dot" />
        </div>

        <!-- ═══ 精修版本堆栈 ═══ -->
        <div class="chain-retouched">
          <div class="chain-section-label">精修版本 ({{ chain.retouched.length }})</div>
          <div v-if="chain.retouched.length === 0" class="chain-placeholder">暂无精修图</div>
          <div v-for="(photo, idx) in chain.retouched" :key="photo.id" class="retouch-row">
            <div class="retouch-card">
              <img :src="storageUrl(photo.thumbnail_path || photo.original_path)" class="chain-img" />
              <span class="version-badge">V{{ photo.version }}</span>
            </div>
            <div class="retouch-info">
              <div class="retouch-id">精修 #{{ photo.id }}</div>
              <div class="retouch-source">源: #RAW-{{ String(chain.raw.display_id).padStart(3, '0') }}</div>
              <div class="retouch-notes">{{ photo.revision_notes || '无修改说明' }}</div>
              <div v-if="photo.client_notes" class="retouch-client-notes">客户: {{ photo.client_notes }}</div>
              <button class="edit-btn" @click="openEditDialog(photo)">✏️ 编辑明细</button>
            </div>
          </div>
        </div>

        <!-- 连接线 -->
        <div class="chain-line" v-if="chain.completed.length > 0">
          <div class="line-dot" />
          <div class="line-bar line-bar-green" />
          <div class="line-dot dot-green" />
        </div>

        <!-- ═══ 完成图区 ═══ -->
        <div class="chain-completed">
          <div class="chain-section-label">完成图 ({{ chain.completed.length }})</div>
          <div v-if="chain.completed.length === 0" class="chain-placeholder chain-placeholder-final">
            <span>⏳ 待定稿</span>
          </div>
          <div v-for="photo in chain.completed" :key="photo.id" class="final-card">
            <img :src="storageUrl(photo.thumbnail_path || photo.original_path)" class="chain-img chain-img-lg" />
            <div class="final-badge">
              <svg viewBox="0 0 20 20" fill="currentColor" class="ic-sm"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.857-9.809a.75.75 0 00-1.214-.882l-3.483 4.79-1.88-1.88a.75.75 0 10-1.06 1.061l2.5 2.5a.75.75 0 001.137-.089l4-5.5z" clip-rule="evenodd" /></svg>
              FINAL
            </div>
            <div class="final-meta">完成图 #{{ photo.id }}</div>
          </div>
        </div>
      </div>

      <!-- 加载提示 -->
      <div v-if="loading && allPhotos.length > 0" class="loading-more">
        <span>加载中...</span>
      </div>
      <div v-else-if="!hasMorePhotos && allPhotos.length > 0" class="no-more">
        已加载全部 {{ photoTotal }} 张照片
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <div v-if="editingPhoto" class="edit-mask" @click.self="editingPhoto = null">
      <div class="edit-dialog">
        <div class="edit-head">
          <span>编辑修改明细</span>
          <button class="edit-close" @click="editingPhoto = null">×</button>
        </div>
        <div class="edit-body">
          <label class="edit-label">修改明细</label>
          <textarea v-model="editNotes" class="edit-textarea" rows="3" placeholder="如：客户要求背景调亮"></textarea>
        </div>
        <div class="edit-foot">
          <button class="btn-cancel" @click="editingPhoto = null">取消</button>
          <button class="btn-confirm" @click="saveEdit">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'

const props = defineProps<{ projectId: string | number; targetId?: number | null }>()
const emit = defineEmits<{ back: []; 'open-shuttle': [] }>()

interface PhotoItem {
  id: number
  display_id: number
  original_path: string
  thumbnail_path: string | null
  process_state: string
  target_id: number | null
  parent_id: number | null
  version: number
  is_confirmed: boolean
  client_notes: string | null
  revision_notes: string | null
  status: string
}

interface Chain {
  raw: PhotoItem
  retouched: PhotoItem[]
  completed: PhotoItem[]
}

const allPhotos = ref<PhotoItem[]>([])
const loading = ref(false)
const photoSkip = ref(0)
const photoLimit = 50
const photoTotal = ref(0)
const hasMorePhotos = computed(() => allPhotos.value.length < photoTotal.value)

function storageUrl(path: string): string {
  return `/storage/${path}`
}

const rawList = computed(() =>
  allPhotos.value.filter(p => p.process_state === 'raw' && p.status !== 'deleted')
)
const retouchedList = computed(() =>
  allPhotos.value.filter(p => p.process_state === 'retouched' && p.status !== 'deleted')
)
const completedList = computed(() =>
  allPhotos.value.filter(p => p.process_state === 'final' && p.status !== 'deleted')
)

const chains = computed<Chain[]>(() => {
  const confirmedRaws = rawList.value.filter(p => p.is_confirmed)
  return confirmedRaws.map(raw => ({
    raw,
    retouched: retouchedList.value
      .filter(p => p.parent_id === raw.id)
      .sort((a, b) => b.version - a.version),
    completed: completedList.value
      .filter(p => {
        if (p.parent_id === raw.id) return true
        const retouchedParent = retouchedList.value.find(r => r.id === p.parent_id)
        return retouchedParent?.parent_id === raw.id
      }),
  }))
})

async function fetchPhotos() {
  if (!props.projectId || props.projectId === 'undefined') {
    console.warn('[LineageBoard] projectId 无效，跳过照片拉取')
    return
  }

  loading.value = true
  photoSkip.value = 0
  try {
    const d = await request.get(`/api/v1/projects/${props.projectId}/photos`, { skip: '0', limit: String(photoLimit) })
    allPhotos.value = d.items
    photoTotal.value = d.total
  } catch {} finally { loading.value = false }
}

async function loadMorePhotos() {
  if (loading.value || !hasMorePhotos.value) return

  loading.value = true
  photoSkip.value += photoLimit
  try {
    const d = await request.get(`/api/v1/projects/${props.projectId}/photos`, { skip: String(photoSkip.value), limit: String(photoLimit) })
    allPhotos.value.push(...d.items)
  } catch {} finally { loading.value = false }
}

const editingPhoto = ref<PhotoItem | null>(null)
const editNotes = ref('')

function openEditDialog(photo: PhotoItem) {
  editingPhoto.value = photo
  editNotes.value = photo.client_notes || ''
}

async function saveEdit() {
  if (!editingPhoto.value) return
  try {
    await request.patch(`/api/v1/photos/${editingPhoto.value.id}/notes`, { client_notes: editNotes.value })
    editingPhoto.value.client_notes = editNotes.value
    ElMessage.success('明细已保存')
  } catch {}
  editingPhoto.value = null
}

onMounted(fetchPhotos)
</script>

<style scoped>
.lb-root {
  height: 100%; display: flex; flex-direction: column;
  background: #f8f9fb; font-family: 'Inter', -apple-system, sans-serif;
}

/* Topbar */
.lb-topbar {
  display: flex; align-items: center; gap: 12px;
  padding: 14px 20px; background: #fff;
  border-bottom: 1px solid #e5e7eb; flex-shrink: 0;
}
.lb-back {
  display: flex; align-items: center; gap: 4px;
  border: 1px solid #e2e8f0; background: #fff; color: #475569;
  padding: 6px 14px; border-radius: 8px; font-size: 13px; cursor: pointer;
}
.lb-back:hover { background: #f8fafc; }
.lb-title { font-size: 15px; font-weight: 700; color: #1e293b; }
.lb-shuttle-btn {
  margin-left: auto; border: none;
  background: #2563eb; color: #fff;
  padding: 7px 18px; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
}
.lb-shuttle-btn:hover { background: #1d4ed8; }

.lb-loading, .lb-empty {
  flex: 1; display: flex; align-items: center; justify-content: center;
  font-size: 14px; color: #94a3b8;
}

/* Chains */
.lb-chains {
  flex: 1; overflow-y: auto; padding: 24px 28px;
  display: flex; flex-direction: column; gap: 32px;
}

.loading-more {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  color: #94a3b8;
  font-size: 13px;
}

.no-more {
  text-align: center;
  padding: 16px;
  color: #c0c4cc;
  font-size: 12px;
}

.chain-block {
  background: #fff; border-radius: 16px; padding: 24px;
  border: 1px solid #f0f0f0;
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

/* Raw */
.chain-raw-card {
  display: flex; align-items: center; gap: 14px;
}
.chain-img {
  width: 120px; aspect-ratio: 4/3; object-fit: cover;
  border-radius: 10px; display: block; background: #f1f5f9;
}
.chain-img-lg { width: 200px; }
.chain-raw-meta { display: flex; flex-direction: column; gap: 2px; }
.raw-tag {
  font-size: 15px; font-weight: 700; color: #1e293b;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.raw-file { font-size: 12px; color: #94a3b8; }
.raw-confirmed { font-size: 11px; font-weight: 600; color: #22c55e; background: #f0fdf4; padding: 1px 6px; border-radius: 4px; }
.retouch-client-notes { font-size: 12px; color: #e6a23c; line-height: 1.4; }

/* Line */
.chain-line {
  display: flex; flex-direction: column; align-items: center; padding: 4px 0;
  margin-left: 60px;
}
.line-dot { width: 8px; height: 8px; border-radius: 50%; background: #d1d5db; }
.dot-green { background: #22c55e; }
.line-bar { width: 2px; height: 24px; background: #e2e8f0; }
.line-bar-green { background: #bbf7d0; }

/* Retouched */
.chain-retouched { padding-left: 20px; }
.chain-section-label {
  font-size: 12px; font-weight: 600; color: #94a3b8;
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 10px;
}
.chain-placeholder {
  font-size: 13px; color: #c0c4cc; padding: 12px 0;
  border-left: 2px dashed #e2e8f0; padding-left: 14px;
}
.chain-placeholder-final { border-left-color: #bbf7d0; }

.retouch-row {
  display: flex; gap: 14px; align-items: flex-start;
  padding: 10px 0; border-left: 2px solid #fbbf24; padding-left: 14px;
  margin-bottom: 8px;
}
.retouch-card { position: relative; flex-shrink: 0; }
.version-badge {
  position: absolute; top: 4px; left: 4px;
  background: #1e293b; color: #fff;
  font-size: 11px; font-weight: 700;
  padding: 2px 8px; border-radius: 4px;
}
.retouch-info { display: flex; flex-direction: column; gap: 3px; }
.retouch-id { font-size: 13px; font-weight: 600; color: #1e293b; }
.retouch-source {
  font-size: 11px; color: #3b82f6; font-weight: 600;
  font-family: 'SF Mono', monospace;
}
.retouch-notes { font-size: 12px; color: #94a3b8; line-height: 1.4; }
.edit-btn {
  align-self: flex-start; margin-top: 4px;
  border: 1px solid #e2e8f0; background: #fff; color: #475569;
  padding: 3px 10px; border-radius: 6px; font-size: 11px; cursor: pointer;
}
.edit-btn:hover { background: #f8fafc; border-color: #3b82f6; color: #3b82f6; }

/* Completed */
.chain-completed { padding-left: 20px; }
.final-card {
  position: relative; display: inline-block;
  border-left: 2px solid #22c55e; padding-left: 14px;
}
.final-badge {
  position: absolute; top: 8px; left: 22px;
  display: flex; align-items: center; gap: 3px;
  background: rgba(34,197,94,0.85); color: #fff;
  padding: 3px 10px; border-radius: 6px;
  font-size: 10px; font-weight: 700; letter-spacing: 0.5px;
}
.final-meta { font-size: 12px; color: #64748b; margin-top: 6px; }

/* Icons */
.ic { width: 16px; height: 16px; }
.ic-sm { width: 14px; height: 14px; }

/* Edit Dialog */
.edit-mask {
  position: fixed; inset: 0; z-index: 200;
  background: rgba(0,0,0,0.3); backdrop-filter: blur(2px);
  display: flex; align-items: center; justify-content: center;
}
.edit-dialog {
  width: 400px; background: #fff; border-radius: 14px; overflow: hidden;
  box-shadow: 0 16px 48px rgba(0,0,0,0.15);
}
.edit-head {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px; border-bottom: 1px solid #f0f0f0;
  font-size: 14px; font-weight: 700;
}
.edit-close {
  width: 28px; height: 28px; border-radius: 8px; border: none;
  background: #f1f5f9; color: #64748b; font-size: 18px; cursor: pointer;
}
.edit-body { padding: 20px; }
.edit-label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; }
.edit-textarea {
  width: 100%; padding: 10px; border: 1px solid #d1d5db; border-radius: 8px;
  font-size: 13px; resize: vertical; outline: none; font-family: inherit;
}
.edit-textarea:focus { border-color: #3b82f6; }
.edit-foot {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 20px; border-top: 1px solid #f0f0f0;
}
.btn-cancel {
  padding: 7px 16px; border: 1px solid #d1d5db; border-radius: 8px;
  background: #fff; font-size: 13px; cursor: pointer;
}
.btn-confirm {
  padding: 7px 16px; border: none; border-radius: 8px;
  background: #2563eb; color: #fff; font-size: 13px; font-weight: 600; cursor: pointer;
}
.btn-confirm:hover { background: #1d4ed8; }
</style>
