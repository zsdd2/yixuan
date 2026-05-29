<template>
  <div class="shuttle-view">
    <div class="shuttle-header">
      <h2 class="shuttle-title">照片分拣台</h2>
      <el-tooltip content="左侧选择来源照片，中间设置状态，右侧查看当前子项目照片。照片移动后可撤销一次。" placement="bottom">
        <span class="hint-icon">!</span>
      </el-tooltip>
      <div style="flex:1" />
      <el-button type="success" @click="$emit('import')">📤 导入图片</el-button>
      <el-button @click="$emit('close')">关闭</el-button>
    </div>

    <div class="shuttle-body" v-loading="loading">
      <!-- 左侧：来源照片 -->
      <div class="shuttle-panel">
        <div class="panel-header">
          <span class="panel-title">来源照片</span>
          <el-segmented v-model="leftSourceMode" :options="leftSourceOptions" size="small" />
          <span class="panel-count">{{ filteredSourcePhotos.length }} 张</span>
          <div style="flex:1" />
          <el-button size="small" type="danger" plain :disabled="leftSelected.size === 0" @click="softDeleteSelected">
            删除选中 ({{ leftSelected.size }})
          </el-button>
        </div>

        <!-- 筛选栏 -->
        <div class="filter-bar">
          <div class="filter-group">
            <span class="filter-label">拍摄日期:</span>
            <el-select v-model="filterShotDates" multiple size="small" placeholder="全部日期" clearable style="min-width:180px" @change="onFilterChange">
              <el-option v-for="d in shotDateOptions" :key="d.date" :label="d.label" :value="d.date" />
            </el-select>
          </div>
          <div class="filter-group">
            <span class="filter-label">处理阶段:</span>
            <el-select v-model="filterProcessState" size="small" placeholder="全部阶段" clearable style="width:110px" @change="onFilterChange">
              <el-option label="原图" value="raw" />
              <el-option label="精修" value="retouched" />
              <el-option label="完成" value="final" />
            </el-select>
          </div>
          <el-tooltip content="图片固定尺寸展示，数量多时在当前区域内向下滚动选择。" placement="top">
            <span class="hint-icon subtle">!</span>
          </el-tooltip>
          <el-button size="small" @click="selectAllLeft" :disabled="visibleSourcePhotos.length === 0">全选</el-button>
          <el-button size="small" @click="leftSelected.clear()" :disabled="leftSelected.size === 0">取消</el-button>
        </div>

        <div class="panel-grid">
          <div
            v-for="photo in paginatedUnassignedPhotos"
            :key="photo.id"
            :class="['photo-thumb', { selected: leftSelected.has(photo.id) }]"
            @click="toggleLeft(photo.id)"
          >
            <el-image :src="thumbUrl(photo)" fit="cover" lazy class="thumb-img">
              <template #error><div class="thumb-error"><el-icon><PictureFilled /></el-icon></div></template>
            </el-image>
            <span class="display-id-badge">#{{ String(photo.display_id).padStart(3, '0') }}</span>
            <span v-if="photo.shot_at" class="shot-at-badge">{{ formatShotAt(photo.shot_at) }}</span>
            <span class="state-badge" :class="'state-' + photo.process_state">{{ stateLabel[photo.process_state] || '' }}</span>
            <span v-if="photo.original_filename" class="filename-badge" :title="photo.original_filename">{{ truncName(photo.original_filename) }}</span>
            <div v-if="leftSelected.has(photo.id)" class="check-mark"><el-icon><Select /></el-icon></div>
          </div>
        </div>
        <el-empty v-if="filteredSourcePhotos.length === 0" description="无可选照片" :image-size="50" />
      </div>

      <!-- 中间操作区 -->
      <div class="shuttle-actions">
        <div class="action-group">
          <span class="action-label">移入时设置状态:</span>
          <el-radio-group v-model="moveTargetState" size="small">
            <el-radio value="keep">保持原状态</el-radio>
            <el-radio value="raw">原图</el-radio>
            <el-radio value="retouched">精修</el-radio>
            <el-radio value="final">完成</el-radio>
          </el-radio-group>
        </div>
        <div class="action-summary">
          <span class="summary-line">待移入 {{ leftSelected.size }} 张</span>
          <span class="summary-line">移入后：{{ moveStatePreview }}</span>
          <span class="summary-muted">右侧已选 {{ rightSelected.size }} 张可移出</span>
        </div>
        <div v-if="lastUndo" class="undo-card">
          <span>{{ lastUndo.text }}</span>
          <el-button link type="primary" :loading="lastUndo.busy" @click="undoLastOperation">撤销</el-button>
        </div>
        <el-button type="primary" :disabled="leftSelected.size === 0" @click="moveToTarget">
          移入 →<br/>({{ leftSelected.size }})
        </el-button>
        <el-button type="warning" :disabled="rightSelected.size === 0" @click="removeFromTarget">
          ← 移出<br/>({{ rightSelected.size }})
        </el-button>
      </div>

      <!-- 右侧：当前目标照片 -->
      <div class="shuttle-panel">
        <div class="panel-header">
          <span class="panel-title">当前目标照片</span>
          <span class="panel-count">{{ filteredTargetPhotos.length }} 张</span>
          <div style="flex:1" />
          <el-radio-group v-model="rightFilter" size="small">
            <el-radio-button value="raw">原图</el-radio-button>
            <el-radio-button value="retouched">精修</el-radio-button>
            <el-radio-button value="final">完成</el-radio-button>
            <el-radio-button value="all">全部</el-radio-button>
          </el-radio-group>
        </div>

        <!-- 右侧筛选栏 -->
        <div class="filter-bar">
          <div class="filter-group">
            <span class="filter-label">拍摄日期:</span>
            <el-select v-model="rightFilterShotDates" multiple size="small" placeholder="全部日期" clearable style="min-width:180px" @change="onRightFilterChange">
              <el-option v-for="d in shotDateOptions" :key="d.date" :label="d.label" :value="d.date" />
            </el-select>
          </div>
          <el-tooltip content="右侧仅显示当前目标内照片，可按状态与日期筛选。" placement="top">
            <span class="hint-icon subtle">!</span>
          </el-tooltip>
          <el-button size="small" @click="selectAllRight" :disabled="visibleTargetPhotos.length === 0">全选</el-button>
          <el-button size="small" @click="rightSelected.clear()" :disabled="rightSelected.size === 0">取消</el-button>
        </div>

        <div class="panel-grid">
          <div
            v-for="photo in paginatedTargetPhotos"
            :key="photo.id"
            :class="['photo-thumb', { selected: rightSelected.has(photo.id) }]"
            @click="toggleRight(photo.id)"
          >
            <el-image :src="thumbUrl(photo)" fit="cover" lazy class="thumb-img">
              <template #error><div class="thumb-error"><el-icon><PictureFilled /></el-icon></div></template>
            </el-image>
            <span class="display-id-badge">#{{ String(photo.display_id).padStart(3, '0') }}</span>
            <span v-if="photo.shot_at" class="shot-at-badge">{{ formatShotAt(photo.shot_at) }}</span>
            <span class="state-badge" :class="'state-' + photo.process_state">{{ stateLabel[photo.process_state] || '' }}</span>
            <span v-if="photo.original_filename" class="filename-badge" :title="photo.original_filename">{{ truncName(photo.original_filename) }}</span>
            <div v-if="rightSelected.has(photo.id)" class="check-mark"><el-icon><Select /></el-icon></div>
          </div>
        </div>
        <el-empty v-if="filteredTargetPhotos.length === 0" description="该目标暂无照片" :image-size="50" />

      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { PictureFilled, Select } from '@element-plus/icons-vue'
import request from '../api/request'

interface PhotoItem {
  id: number
  display_id: number
  target_id: number | null
  process_state: string
  status: string
  original_path: string
  original_filename: string | null
  thumbnail_path: string | null
  shot_at: string | null
}

interface ShotDateOption {
  date: string
  label: string
  count: number
}

interface PhotoSnapshot {
  id: number
  target_id: number | null
  process_state: string
}

interface UndoOperation {
  text: string
  snapshots: PhotoSnapshot[]
  busy: boolean
}

const props = defineProps<{
  projectId: string | number
  targetId: number
}>()

const emit = defineEmits<{ close: [], import: [] }>()

const stateLabel: Record<string, string> = { raw: '原图', retouched: '精修', final: '成片' }

const loading = ref(false)
const allPhotos = ref<PhotoItem[]>([])
const photoTotal = ref(0)
const leftSelected = reactive(new Set<number>())
const rightSelected = reactive(new Set<number>())
const rightFilter = ref<string>('raw')
const moveTargetState = ref<string>('keep')
const lastUndo = ref<UndoOperation | null>(null)
const leftSourceMode = ref<'unassigned' | 'project'>('unassigned')
const leftSourceOptions = [
  { label: '未分类', value: 'unassigned' },
  { label: '项目内', value: 'project' },
]

// 左侧筛选和分页
const filterShotDates = ref<string[]>([])
const filterProcessState = ref<string>('')
const leftPage = ref(1)
const leftPageSize = ref(500)

// 右侧筛选和分页
const rightFilterShotDates = ref<string[]>([])
const rightPage = ref(1)
const rightPageSize = ref(500)

// 拍摄日期选项
const shotDateOptions = ref<ShotDateOption[]>([])

const moveStatePreview = computed(() =>
  moveTargetState.value === 'keep'
    ? '保持原状态'
    : (stateLabel[moveTargetState.value] || moveTargetState.value)
)

const unassignedPhotos = computed(() =>
  allPhotos.value
    .filter(p => p.target_id == null && p.status !== 'deleted')
    .sort((a, b) => a.display_id - b.display_id)
)

const sourcePhotos = computed(() => {
  if (leftSourceMode.value === 'project') {
    return allPhotos.value
      .filter(p => p.target_id !== props.targetId && p.status !== 'deleted')
      .sort((a, b) => a.display_id - b.display_id)
  }
  return unassignedPhotos.value
})

const filteredSourcePhotos = computed(() => {
  let list = sourcePhotos.value

  // 按拍摄日期筛选
  if (filterShotDates.value.length > 0) {
    list = list.filter(p => {
      if (!p.shot_at && filterShotDates.value.includes('none')) return true
      if (p.shot_at) {
        const date = p.shot_at.split('T')[0]
        return filterShotDates.value.includes(date)
      }
      return false
    })
  }

  // 按处理阶段筛选
  if (filterProcessState.value) {
    list = list.filter(p => p.process_state === filterProcessState.value)
  }

  return list
})

const paginatedUnassignedPhotos = computed(() => {
  const start = (leftPage.value - 1) * leftPageSize.value
  const end = start + leftPageSize.value
  return filteredSourcePhotos.value.slice(start, end)
})

const visibleSourcePhotos = computed(() => paginatedUnassignedPhotos.value)

const targetPhotos = computed(() => {
  let list = allPhotos.value.filter(p => p.target_id === props.targetId && p.status !== 'deleted')
  if (rightFilter.value !== 'all') {
    list = list.filter(p => p.process_state === rightFilter.value)
  }
  return list
})

const filteredTargetPhotos = computed(() => {
  let list = targetPhotos.value

  // 按拍摄日期筛选
  if (rightFilterShotDates.value.length > 0) {
    list = list.filter(p => {
      if (!p.shot_at && rightFilterShotDates.value.includes('none')) return true
      if (p.shot_at) {
        const date = p.shot_at.split('T')[0]
        return rightFilterShotDates.value.includes(date)
      }
      return false
    })
  }

  return list
})

const paginatedTargetPhotos = computed(() => {
  const start = (rightPage.value - 1) * rightPageSize.value
  const end = start + rightPageSize.value
  return filteredTargetPhotos.value.slice(start, end)
})

const visibleTargetPhotos = computed(() => paginatedTargetPhotos.value)

function truncName(name: string): string {
  return name.length > 12 ? name.slice(0, 10) + '…' : name
}

function thumbUrl(photo: PhotoItem): string {
  const path = photo.thumbnail_path || photo.original_path
  return `/storage/${path}`
}

function formatShotAt(shotAt: string): string {
  const date = new Date(shotAt)
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  const hour = String(date.getHours()).padStart(2, '0')
  const minute = String(date.getMinutes()).padStart(2, '0')
  return `${month}-${day} ${hour}:${minute}`
}

function toggleLeft(id: number) {
  if (leftSelected.has(id)) leftSelected.delete(id)
  else leftSelected.add(id)
}

function toggleRight(id: number) {
  if (rightSelected.has(id)) rightSelected.delete(id)
  else rightSelected.add(id)
}

function selectAllLeft() {
  visibleSourcePhotos.value.forEach(p => leftSelected.add(p.id))
}

function selectAllRight() {
  visibleTargetPhotos.value.forEach(p => rightSelected.add(p.id))
}

function onFilterChange() {
  leftPage.value = 1
  leftSelected.clear()
}

function onRightFilterChange() {
  rightPage.value = 1
  rightSelected.clear()
}

function snapshotPhotos(ids: number[]): PhotoSnapshot[] {
  return allPhotos.value
    .filter(p => ids.includes(p.id))
    .map(p => ({ id: p.id, target_id: p.target_id, process_state: p.process_state }))
}

function groupSnapshots(snapshots: PhotoSnapshot[]) {
  const groups = new Map<string, PhotoSnapshot[]>()
  for (const item of snapshots) {
    const key = `${item.target_id ?? 'none'}:${item.process_state}`
    const current = groups.get(key) || []
    current.push(item)
    groups.set(key, current)
  }
  return Array.from(groups.values())
}

async function restoreSnapshots(snapshots: PhotoSnapshot[]) {
  for (const group of groupSnapshots(snapshots)) {
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
    const photo = allPhotos.value.find(p => p.id === snapshot.id)
    if (photo) {
      photo.target_id = snapshot.target_id
      photo.process_state = snapshot.process_state
    }
  }
}

async function undoLastOperation() {
  if (!lastUndo.value) return
  lastUndo.value.busy = true
  try {
    await restoreSnapshots(lastUndo.value.snapshots)
    ElMessage.success('已撤销上一次移动')
    lastUndo.value = null
  } catch (e: any) {
    ElMessage.error(e.message || '撤销失败')
    if (lastUndo.value) lastUndo.value.busy = false
  }
}

async function moveToTarget() {
  const ids = Array.from(leftSelected)
  if (ids.length === 0) return
  const snapshots = snapshotPhotos(ids)
  try {
    const body: any = { photo_ids: ids, target_id: props.targetId }
    if (moveTargetState.value !== 'keep') {
      body.process_state = moveTargetState.value
    }
    await request.patch('/api/v1/photos/bulk-update', body)
    for (const p of allPhotos.value) {
      if (leftSelected.has(p.id)) {
        p.target_id = props.targetId
        if (moveTargetState.value !== 'keep') {
          p.process_state = moveTargetState.value
        }
      }
    }
    leftSelected.clear()
    lastUndo.value = { text: `刚移入 ${ids.length} 张照片`, snapshots, busy: false }
    ElMessage.success(`已移入 ${ids.length} 张照片`)
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  }
}

async function removeFromTarget() {
  const ids = Array.from(rightSelected)
  if (ids.length === 0) return
  const snapshots = snapshotPhotos(ids)
  try {
    await request.patch('/api/v1/photos/bulk-update', { photo_ids: ids, remove_from_target: true })
    rightSelected.clear()
    await fetchPhotos()
    lastUndo.value = { text: `刚移出 ${ids.length} 张照片`, snapshots, busy: false }
    ElMessage.success(`已移出 ${ids.length} 张照片`)
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  }
}

async function softDeleteSelected() {
  const ids = Array.from(leftSelected)
  if (ids.length === 0) return
  try {
    await ElMessageBox.confirm(`确定将 ${ids.length} 张照片移入回收站？物理文件不受影响。`, '删除确认', { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch { return }
  try {
    await request.post('/api/v1/photos/bulk-soft-delete', { photo_ids: ids })
    leftSelected.clear()
    await fetchPhotos()
    ElMessage.success(`已删除 ${ids.length} 张照片`)
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  }
}

async function fetchPhotos() {
  if (!props.projectId || props.projectId === 'undefined') {
    console.warn('[PhotoShuttle] projectId 无效，跳过照片拉取')
    return
  }

  loading.value = true
  try {
    const data = await request.get(`/api/v1/projects/${props.projectId}/photos`, { skip: 0, limit: 500, status: 'pending,selected' })
    allPhotos.value = data.items
    photoTotal.value = data.total
  } catch (e: any) {
    ElMessage.error(e.message || '获取照片失败')
  } finally {
    loading.value = false
  }
}

async function fetchShotDates() {
  try {
    const data = await request.get(`/api/v1/projects/${props.projectId}/photos/shot-dates`)
    shotDateOptions.value = (data.items as { date: string; count: number }[]).map(item => ({
      date: item.date,
      count: item.count,
      label: item.date === 'none' ? `无日期 (${item.count})` : `${item.date} (${item.count})`,
    }))
  } catch {}
}

onMounted(async () => {
  await Promise.all([fetchPhotos(), fetchShotDates()])
})
</script>

<style scoped>
.shuttle-view { padding: 24px 32px; height: 100%; display: flex; flex-direction: column; overflow: hidden; }
.shuttle-header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; flex-shrink: 0; }
.shuttle-title { font-size: 20px; font-weight: 700; color: #2c3e50; margin: 0; }
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
  flex-shrink: 0;
}
.hint-icon.subtle {
  color: #909399;
  border-color: #dcdfe6;
  background: #f8f9fb;
}

.shuttle-body { display: flex; gap: 16px; flex: 1; min-height: 0; }

.shuttle-panel { flex: 1; min-width: 0; display: flex; flex-direction: column; border: 1px solid #ebeef5; border-radius: 8px; overflow: hidden; background: #fff; }
.panel-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; background: #f8f9fb; border-bottom: 1px solid #ebeef5; }
.panel-title { font-size: 14px; font-weight: 600; color: #2c3e50; }
.panel-count { font-size: 12px; color: #909399; }

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: #fafafa;
  border-bottom: 1px solid #ebeef5;
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}
.filter-hint { font-size: 12px; color: #909399; white-space: nowrap; }

.panel-grid {
  flex: 1; overflow-y: auto; padding: 12px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(128px, 128px));
  grid-auto-rows: 128px;
  gap: 10px;
  align-content: start;
  justify-content: start;
}

.photo-thumb {
  position: relative; aspect-ratio: 1; border-radius: 6px; overflow: hidden;
  cursor: pointer; transition: all 0.2s; border: 2px solid transparent;
}
.photo-thumb:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }
.photo-thumb.selected { border-color: #409eff; box-shadow: 0 0 0 2px rgba(64,158,255,0.2); }

.thumb-img { width: 100%; height: 100%; }
.thumb-error { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #f5f7fa; color: #c0c4cc; font-size: 24px; }

.display-id-badge {
  position: absolute; top: 4px; left: 4px; background: rgba(0,0,0,0.7); color: #fff;
  padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: 600;
}

.shot-at-badge {
  position: absolute; top: 4px; right: 4px; background: rgba(103, 194, 58, 0.9); color: #fff;
  padding: 2px 6px; border-radius: 4px; font-size: 10px; font-weight: 500;
}

.state-badge {
  position: absolute; bottom: 24px; left: 4px; padding: 2px 6px; border-radius: 4px;
  font-size: 10px; font-weight: 500; color: #fff;
}
.state-badge.state-raw { background: rgba(144, 147, 153, 0.9); }
.state-badge.state-retouched { background: rgba(230, 162, 60, 0.9); }
.state-badge.state-final { background: rgba(103, 194, 58, 0.9); }

.filename-badge {
  position: absolute; bottom: 4px; left: 4px; right: 4px; background: rgba(0,0,0,0.7); color: #fff;
  padding: 2px 4px; border-radius: 3px; font-size: 10px; text-align: center;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}

.check-mark {
  position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
  width: 32px; height: 32px; border-radius: 50%; background: rgba(64,158,255,0.95);
  display: flex; align-items: center; justify-content: center; color: #fff; font-size: 18px;
}

.panel-pagination {
  padding: 12px 16px;
  border-top: 1px solid #ebeef5;
  display: flex;
  justify-content: center;
  background: #f8f9fb;
}

.shuttle-actions {
  display: flex; flex-direction: column; align-items: stretch; justify-content: center;
  gap: 14px; padding: 18px 14px; background: #f8f9fb; border: 1px solid #ebeef5; border-radius: 8px;
  width: 200px;
  flex-shrink: 0;
}

.action-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  width: 100%;
  box-sizing: border-box;
}

.action-group :deep(.el-radio-group) {
  display: grid;
  grid-template-columns: 1fr;
  gap: 8px;
}

.action-group :deep(.el-radio) {
  height: 24px;
  margin-right: 0;
  display: flex;
  align-items: center;
}

.action-label {
  font-size: 12px;
  color: #606266;
  font-weight: 600;
  margin-bottom: 4px;
}

.action-summary,
.undo-card {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
}

.action-summary {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.summary-line {
  font-size: 13px;
  color: #303133;
  font-weight: 600;
}

.summary-muted {
  font-size: 12px;
  color: #909399;
}

.undo-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: 12px;
  color: #606266;
  border-color: #b3d8ff;
  background: #ecf5ff;
}

.shuttle-actions .el-button {
  width: 100%; height: 56px; font-size: 14px; font-weight: 600; margin-left: 0;
}
</style>
