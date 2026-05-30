<template>
  <div class="card-wrapper" @click="goToDetail">
    <!-- 左上角: 剩余到期时间 -->
    <span v-if="countdownText" class="card-countdown" :class="countdownClass">
      {{ countdownText }}
    </span>

    <!-- 右上角: 三点菜单 -->
    <div class="card-more-wrap" @click.stop>
      <el-dropdown trigger="click" @command="onMenuCommand">
        <button class="card-more-btn">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
            <circle cx="12" cy="5" r="2" />
            <circle cx="12" cy="12" r="2" />
            <circle cx="12" cy="19" r="2" />
          </svg>
        </button>
        <template #dropdown>
          <GlobalStatusMenu :current-status="project.project_status">
            <template #before>
              <el-dropdown-item command="detail"><span class="mi">📋 查看详情</span></el-dropdown-item>
              <el-dropdown-item command="edit"><span class="mi">✏️ 编辑</span></el-dropdown-item>
            </template>
            <template #after>
              <el-dropdown-item divided :command="project.archived_at ? 'unarchive' : 'archive'">
                <span class="mi">
                  <span class="sd" :style="{ background: project.archived_at ? '#67c23a' : '#e6a23c' }" />
                  {{ project.archived_at ? '取消归档' : '归档项目' }}
                </span>
              </el-dropdown-item>
              <el-dropdown-item command="delete" divided><span class="mi mi-danger">🗑️ 删除</span></el-dropdown-item>
            </template>
          </GlobalStatusMenu>
        </template>
      </el-dropdown>
    </div>

    <!-- Section 1: Placeholder -->
    <div class="card-media">
      <el-image
        v-if="project.cover_image"
        :src="`/storage/${project.cover_image}`"
        fit="cover"
        lazy
        class="w-full h-full"
      />
      <div v-else class="placeholder">
        <svg class="placeholder-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="0.8" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      </div>
    </div>

    <!-- Section 2: 标题行 — 项目名左 + 状态 + 图像总数右 -->
    <div class="card-header">
      <h3 class="card-title">{{ project.name }}</h3>
      <span class="project-status-badge" :class="'ps-' + (project.project_status || 'not_started')">
        {{ projectStatusLabel[project.project_status || 'not_started'] || '' }}
      </span>
      <span class="card-photo-count">📷 {{ project.photo_count || 0 }}</span>
    </div>

    <!-- Section 3: 创建信息 -->
    <div class="card-meta">
      {{ project.client_name || 'Admin' }} · {{ formattedDate }}
    </div>

    <!-- Section 4: 白图 + 场景图 已完成目标/总目标 -->
    <div class="card-metrics">
      <div class="metric-row">
        <span class="metric-label">白图</span>
        <span class="metric-value">{{ project.white_completed || 0 }}/{{ project.white_target || 0 }}</span>
        <div class="metric-bar">
          <div class="metric-bar-fill" :style="{ width: whitePercent + '%' }"></div>
        </div>
      </div>
      <div class="metric-row">
        <span class="metric-label">场景图</span>
        <span class="metric-value">{{ project.scene_completed || 0 }}/{{ project.scene_target || 0 }}</span>
        <div class="metric-bar">
          <div class="metric-bar-fill" :style="{ width: scenePercent + '%' }"></div>
        </div>
      </div>
    </div>

    <!-- 编辑弹窗 -->
    <teleport to="body">
      <el-dialog v-model="editVisible" title="编辑项目" width="480px" destroy-on-close @click.stop>
        <el-form :model="editForm" :rules="editRules" ref="editFormRef" label-width="100px">
          <el-form-item label="项目编号">
            <el-input :model-value="project.display_id" disabled />
          </el-form-item>
          <el-form-item label="项目名称" prop="name">
            <el-input v-model="editForm.name" placeholder="项目名称" maxlength="128" show-word-limit />
          </el-form-item>
          <el-form-item label="项目封面">
            <div class="cover-picker">
              <div v-if="editForm.cover_image" class="cover-preview-wrap">
                <el-image :src="getCoverUrl(editForm.cover_image)" fit="cover" class="cover-preview-img" />
                <el-button size="small" text type="danger" @click="editForm.cover_image = null">移除</el-button>
              </div>
              <el-button size="small" @click="showImagePicker = true">选择图片</el-button>
            </div>
          </el-form-item>
          <el-form-item label="截止时间">
            <el-date-picker
              v-model="editForm.estimated_end_time"
              type="datetime"
              placeholder="选择预估结束时间"
              style="width: 100%"
            />
          </el-form-item>
        </el-form>
        <template #footer>
          <el-button @click="editVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveEdit">保存</el-button>
        </template>
      </el-dialog>

    <!-- 图片选择器 -->
    <ImagePicker
      v-model:visible="showImagePicker"
      category="cover"
      :project-id="props.project.id"
      @confirm="onImagePicked"
    />
    </teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import type { Project } from '../views/Dashboard.vue'
import ImagePicker from './ImagePicker.vue'
import GlobalStatusMenu from './GlobalStatusMenu.vue'
import request from '../api/request'

const props = defineProps<{ project: Project }>()
const emit = defineEmits<{ (e: 'updated'): void }>()
const router = useRouter()

const projectStatusLabel: Record<string, string> = {
  not_started: '未开始',
  shooting: '拍摄中',
  retouching: '修图中',
  completed: '已完成',
}

const editVisible = ref(false)
const saving = ref(false)
const editFormRef = ref<FormInstance>()
const editForm = reactive({
  name: '',
  estimated_end_time: null as string | null,
  cover_image: null as string | null,
})

const editRules: FormRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
}

const formattedDate = computed(() => {
  if (!props.project.created_at) return '—'
  return props.project.created_at.slice(0, 10)
})

const remainingHours = computed(() => {
  if (!props.project.estimated_end_time) return null
  const end = new Date(props.project.estimated_end_time).getTime()
  return (end - Date.now()) / (1000 * 60 * 60)
})

const countdownText = computed(() => {
  const h = remainingHours.value
  if (h === null) return ''
  if (h <= -24) return `逾期${Math.floor(-h / 24)}天`
  if (h <= 0) return `逾期${Math.ceil(-h)}小时`
  if (h < 24) return `${Math.floor(h)}小时`
  return `${Math.floor(h / 24)}天`
})

const countdownClass = computed(() => {
  const h = remainingHours.value
  if (h === null) return ''
  if (h <= 0) return 'countdown-danger'
  if (h < 72) return 'countdown-warn'
  return 'countdown-safe'
})

const whitePercent = computed(() => {
  const t = props.project.white_target
  if (!t) return 0
  return Math.min(100, Math.round(((props.project.white_completed || 0) / t) * 100))
})

const scenePercent = computed(() => {
  const t = props.project.scene_target
  if (!t) return 0
  return Math.min(100, Math.round(((props.project.scene_completed || 0) / t) * 100))
})

function goToDetail() {
  router.push({ name: 'ProjectDetail', params: { id: props.project.id } })
}

function onMenuCommand(cmd: string) {
  if (cmd === 'detail') goToDetail()
  else if (cmd === 'edit') openEdit()
  else if (cmd === 'delete') confirmDelete()
  else if (cmd === 'archive') toggleArchive('archive')
  else if (cmd === 'unarchive') toggleArchive('unarchive')
  else if (cmd.startsWith('status:')) setProjectStatus(cmd.replace('status:', ''))
}

async function setProjectStatus(newStatus: string) {
  try {
    // 如果设置为已完成状态，提示是否归档
    if (newStatus === 'completed' && !props.project.archived_at) {
      try {
        await ElMessageBox.confirm(
          '项目已完成，是否同时归档？归档后 15 天内未恢复的回收站照片将被物理删除。',
          '归档确认',
          {
            type: 'warning',
            confirmButtonText: '归档',
            cancelButtonText: '仅标记完成',
            distinguishCancelAndClose: true,
          }
        )
        // 用户选择归档
        await toggleArchive('archive')
        return
      } catch (action) {
        // 用户选择"仅标记完成"或关闭弹窗
        if (action === 'cancel') {
          // 继续执行状态更新
        } else {
          // 用户关闭弹窗，取消操作
          return
        }
      }
    }

    await request.patch(`/api/v1/projects/${props.project.id}`, { project_status: newStatus })
    ElMessage.success('项目状态已更新')
    emit('updated')
  } catch (e: any) {
    ElMessage.error(e.message || '修改失败')
  }
}

async function toggleArchive(action: 'archive' | 'unarchive') {
  const msg = action === 'archive'
    ? '归档后，15 天内未恢复的回收站照片将被物理删除，确定继续？'
    : '取消归档后，回收站将不再被定时清理，确定继续？'
  try { await ElMessageBox.confirm(msg, '操作确认', { type: 'warning' }) } catch { return }
  try {
    await request.post(`/api/v1/projects/${props.project.id}/${action}`)
    ElMessage.success(action === 'archive' ? '已归档' : '已取消归档')
    emit('updated')
  } catch (e: any) { ElMessage.error(e.message) }
}

function openEdit() {
  editForm.name = props.project.name
  editForm.estimated_end_time = props.project.estimated_end_time
  editForm.cover_image = props.project.cover_image || null
  editVisible.value = true
}

async function saveEdit() {
  const valid = await editFormRef.value?.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    const body: Record<string, any> = {
      name: editForm.name.trim(),
    }
    if (editForm.estimated_end_time) body.estimated_end_time = editForm.estimated_end_time
    body.cover_image = editForm.cover_image

    await request.patch(`/api/v1/projects/${props.project.id}`, body)
    ElMessage.success('项目已更新')
    editVisible.value = false
    emit('updated')
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const showImagePicker = ref(false)

function getCoverUrl(path: string): string {
  return `/storage/${path}`
}

function onImagePicked(image: { url: string; id?: number; source: 'system' | 'project' }) {
  editForm.cover_image = image.url
}

async function confirmDelete() {
  try {
    await ElMessageBox.confirm(
      '删除后项目将移入回收站，可随时恢复。确定删除？',
      '删除确认',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' },
    )
  } catch { return }

  try {
    await request.post(`/api/v1/projects/${props.project.id}/soft-delete`)
    ElMessage.success('项目已移入回收站')
    emit('updated')
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}
</script>

<style scoped>
.card-wrapper {
  position: relative;
  background: #FFFFFF;
  border-radius: 14px;
  overflow: visible;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.04);
}

.card-wrapper:hover {
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

/* 倒计时 */
.card-countdown {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 10;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 7px;
  backdrop-filter: blur(8px);
}
.countdown-safe { background: rgba(255,255,255,0.4); color: #059669; backdrop-filter: blur(4px); }
.countdown-warn { background: rgba(255,255,255,0.4); color: #D97706; backdrop-filter: blur(4px); }
.countdown-danger { background: rgba(255,255,255,0.4); color: #DC2626; backdrop-filter: blur(4px); }

/* 三点菜单 */
.card-more-wrap {
  position: absolute;
  top: 8px;
  right: 8px;
  z-index: 10;
}

.card-more-btn {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  border: none;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #9CA3AF;
  transition: all 0.15s ease;
  opacity: 0;
}
.card-wrapper:hover .card-more-btn { opacity: 1; }
.card-more-btn:hover { background: #fff; color: #4B5563; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }

/* 占位图 */
.card-media {
  aspect-ratio: 3 / 2;
  background: linear-gradient(135deg, #F8FAFC, #F1F5F9);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: 14px 14px 0 0;
}
.placeholder { display: flex; align-items: center; justify-content: center; width: 100%; height: 100%; }
.placeholder-icon { width: 44px; height: 44px; color: #D1D5DB; }

/* 标题行: 项目名左 + 图片数右 */
.card-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 12px 14px 0;
  gap: 6px;
}
.card-title {
  font-size: 14px;
  font-weight: 700;
  color: #111827;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
}
.card-photo-count {
  font-size: 11px;
  color: #9CA3AF;
  white-space: nowrap;
  flex-shrink: 0;
}

.project-status-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 7px;
  white-space: nowrap;
  flex-shrink: 0;
}
.ps-not_started { background: #f0f2f5; color: #909399; }
.ps-shooting    { background: #ecf5ff; color: #409eff; }
.ps-retouching  { background: #fdf6ec; color: #e6a23c; }
.ps-completed   { background: #f0f9eb; color: #67c23a; }

/* 创建信息 */
.card-meta {
  padding: 3px 14px 0;
  font-size: 11px;
  color: #9CA3AF;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 白图/场景图指标 */
.card-metrics {
  padding: 10px 14px 14px;
  display: flex;
  flex-direction: column;
  gap: 7px;
}

.metric-row {
  display: grid;
  grid-template-columns: 42px 38px 1fr;
  align-items: center;
  gap: 6px;
}

.metric-label {
  font-size: 11px;
  color: #6B7280;
  font-weight: 500;
}

.metric-value {
  font-size: 11px;
  color: #9CA3AF;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.metric-bar {
  height: 4px;
  background: #F1F5F9;
  border-radius: 2px;
  overflow: hidden;
}

.metric-bar-fill {
  height: 100%;
  background: #86EFAC;
  border-radius: 2px;
  transition: width 0.5s ease;
}

/* 封面选择 */
.cover-picker { display: flex; flex-direction: column; gap: 8px; }
.cover-preview-wrap { display: flex; align-items: center; gap: 8px; }
.cover-preview-img { width: 80px; height: 60px; border-radius: 6px; overflow: hidden; }
.cover-preview-img :deep(img) { width: 100%; height: 100%; object-fit: cover; }
.cover-actions { display: flex; gap: 8px; }

/* Unified context menu */
.ctx-menu { min-width: 160px; padding: 4px 0; }
.mi { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.mi-danger { color: #f56c6c; }
.sd { display: inline-block; width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.is-current { background: #f0f7ff; }
.is-current :deep(.el-dropdown-menu__item) { font-weight: 600; color: #2563eb; }
</style>
