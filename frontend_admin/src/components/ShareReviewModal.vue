<template>
  <el-dialog
    v-model="visible"
    :title="viewMode === 'create' ? '分享审核' : '分享管理'"
    width="1200px"
    destroy-on-close
    @close="onClose"
  >
    <!-- 创建视图 -->
    <div v-if="viewMode === 'create'" class="share-modal">
      <!-- 左侧：分级选择菜单 -->
      <div class="left-panel">
        <div class="category-section" v-for="cat in categories" :key="cat.type">
          <div class="category-header">{{ cat.label }}</div>
          <div class="target-list">
            <div
              v-for="target in cat.targets"
              :key="target.id"
              class="target-item"
              :class="{ active: selectedTarget?.id === target.id }"
              @click="selectTarget(target, cat.type)"
            >
              <span>{{ target.name }}</span>
              <span class="count">{{ target.photo_count }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：图片预览与选择 -->
      <div class="right-panel">
        <div v-if="!selectedTarget" class="empty-state">
          <el-empty description="请从左侧选择子项目" />
        </div>
        <div v-else class="photo-selection">
          <div class="selection-header">
            <span class="target-title">{{ selectedTarget.name }}</span>
            <div class="actions">
              <el-radio-group v-model="photoType" size="small">
                <el-radio-button label="raw">原图</el-radio-button>
                <el-radio-button label="retouched">精修</el-radio-button>
                <el-radio-button label="final">完成图</el-radio-button>
              </el-radio-group>
              <el-button size="small" @click="selectAll">全选</el-button>
            </div>
          </div>

          <div v-loading="loadingPhotos" class="photo-grid">
            <div
              v-for="photo in currentPhotos"
              :key="photo.id"
              class="photo-card"
              :class="{ selected: isSelected(photo.id) }"
              @click="togglePhoto(photo)"
            >
              <el-image
                :src="photoThumbUrl(photo)"
                fit="cover"
                lazy
                class="photo-img"
              >
                <template #error><div class="photo-img-error">!</div></template>
              </el-image>
              <div class="photo-info">
                <span class="photo-name">{{ photo.original_filename || `#${photo.display_id}` }}</span>
                <el-select
                  v-if="photoType === 'retouched' && photo.version"
                  v-model="photo.selectedVersion"
                  size="small"
                  @click.stop
                >
                  <el-option
                    v-for="v in photo.versions"
                    :key="v"
                    :label="`v${v}`"
                    :value="v"
                  />
                </el-select>
              </div>
              <div v-if="isSelected(photo.id)" class="check-mark">✓</div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 管理视图 -->
    <div v-else class="management-view">
      <el-table :data="sessions" v-loading="loadingSessions" style="width: 100%">
        <el-table-column label="创建人" prop="created_by_name" width="100" />
        <el-table-column label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="到期时间" width="160">
          <template #default="{ row }">
            {{ formatDateTime(row.expired_at) }}
          </template>
        </el-table-column>
        <el-table-column label="查看状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.is_viewed" type="success" size="small">已查看</el-tag>
            <el-tag v-else type="info" size="small">未查看</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="反馈统计" width="200">
          <template #default="{ row }">
            <div style="font-size: 12px; color: #606266;">
              原图 {{ row.statistics.raw_confirmed }} /
              精修 {{ row.statistics.retouched_confirmed }} /
              成片 {{ row.statistics.final_confirmed }}
            </div>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_disabled"
              active-text="正常"
              inactive-text="已作废"
              :active-value="false"
              :inactive-value="true"
              @change="toggleDisable(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="copySessionLink(row.token)">
              复制链接
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <template #footer>
      <div class="footer-content">
        <div v-if="viewMode === 'create'" class="selected-count">已选择 {{ selectedPhotos.length }} 张图片</div>
        <div v-else></div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <el-button v-if="viewMode === 'create'" text type="primary" @click="switchToManagement">
            查看已有分享
          </el-button>
          <el-button v-else text type="primary" @click="switchToCreate">
            返回创建
          </el-button>
          <span v-if="viewMode === 'create'" style="font-size: 14px; color: #606266;">有效期：</span>
          <el-select v-if="viewMode === 'create'" v-model="expiredDays" size="default" style="width: 120px;">
            <el-option label="1天" :value="1" />
            <el-option label="3天" :value="3" />
            <el-option label="7天" :value="7" />
            <el-option label="15天" :value="15" />
            <el-option label="30天" :value="30" />
          </el-select>
          <el-button @click="onClose">{{ viewMode === 'create' ? '取消' : '关闭' }}</el-button>
          <el-button v-if="viewMode === 'create'" type="primary" :loading="generating" @click="generateLink">生成链接</el-button>
        </div>
      </div>
    </template>

    <!-- 生成结果弹窗 -->
    <el-dialog v-model="showResult" title="分享链接已生成" width="500px" append-to-body>
      <div class="result-content">
        <el-input v-model="shareUrl" readonly>
          <template #append>
            <el-button @click="copyLink">复制</el-button>
          </template>
        </el-input>
        <div class="expire-info">链接将于 {{ expiredAt }} 过期</div>
      </div>
    </el-dialog>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'

const props = defineProps<{
  visible: boolean
  projectId: number
}>()

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
}>()

const visible = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val),
})

const categories = ref<any[]>([])
const selectedTarget = ref<any>(null)
const photoType = ref<'raw' | 'retouched' | 'final'>('raw')
const currentPhotos = ref<any[]>([])
const loadingPhotos = ref(false)
const selectedPhotos = ref<any[]>([])
const generating = ref(false)
const showResult = ref(false)
const shareUrl = ref('')
const expiredAt = ref('')
const expiredDays = ref(7)
const viewMode = ref<'create' | 'management'>('create')
const sessions = ref<any[]>([])
const loadingSessions = ref(false)

watch(() => props.visible, async (val) => {
  if (val) {
    viewMode.value = 'create'
    await loadTargets()
  }
})

watch([selectedTarget, photoType], async () => {
  if (selectedTarget.value) {
    await loadPhotos()
  }
})

async function loadTargets() {
  try {
    const data = await request.get(`/api/v1/projects/${props.projectId}/targets`)

    const white = data.items.filter((t: any) => t.category_type === 'white')
    const scene = data.items.filter((t: any) => t.category_type === 'scene')

    // 计算全部图片的总数
    const totalCount = data.items.reduce((sum: number, t: any) => sum + (t.photo_count || 0), 0)

    categories.value = [
      { type: 'all', label: '全部图片', targets: [{ id: 0, name: '全部图片', photo_count: totalCount }] },
      { type: 'white', label: '白图', targets: white },
      { type: 'scene', label: '场景图', targets: scene },
    ]
  } catch (e: any) {
    ElMessage.error(e.message || '加载目标失败')
  }
}

function selectTarget(target: any, categoryType: string) {
  selectedTarget.value = { ...target, category_type: categoryType }
  selectedPhotos.value = []
}

async function loadPhotos() {
  if (!selectedTarget.value) return

  loadingPhotos.value = true
  try {
    const allItems: any[] = []
    const limit = 500
    let skip = 0
    let total = 0

    do {
      const params: any = {
        process_state: photoType.value,
        status: 'pending,selected',
        skip,
        limit,
      }

      if (selectedTarget.value.id !== 0) {
        params.target_id = selectedTarget.value.id
      }

      const data = await request.get(`/api/v1/projects/${props.projectId}/photos`, params)
      allItems.push(...(data.items || []))
      total = data.total || allItems.length
      skip += limit
    } while (allItems.length < total)

    currentPhotos.value = allItems.map((p: any) => ({
      ...p,
      selectedVersion: p.version || 1,
      versions: p.version ? Array.from({ length: p.version }, (_, i) => i + 1) : [],
    }))
  } catch (e: any) {
    ElMessage.error(e.message || '加载照片失败')
  } finally {
    loadingPhotos.value = false
  }
}

function isSelected(photoId: number) {
  return selectedPhotos.value.some(p => p.photo_id === photoId)
}

function photoThumbUrl(photo: any): string {
  const path = photo.thumbnail_path || photo.original_path
  return path ? `/storage/${path}` : ''
}

function togglePhoto(photo: any) {
  const idx = selectedPhotos.value.findIndex(p => p.photo_id === photo.id)
  if (idx > -1) {
    selectedPhotos.value.splice(idx, 1)
  } else {
    selectedPhotos.value.push({
      photo_id: photo.id,
      version: photoType.value === 'retouched' ? photo.selectedVersion : null,
      category_type: selectedTarget.value.category_type,
      target_name: selectedTarget.value.name,
    })
  }
}

function selectAll() {
  const allIds = currentPhotos.value.map(p => p.id)
  const allSelected = allIds.every(id => isSelected(id))

  if (allSelected) {
    selectedPhotos.value = selectedPhotos.value.filter(
      p => !allIds.includes(p.photo_id)
    )
  } else {
    currentPhotos.value.forEach(photo => {
      if (!isSelected(photo.id)) {
        selectedPhotos.value.push({
          photo_id: photo.id,
          version: photoType.value === 'retouched' ? photo.selectedVersion : null,
          category_type: selectedTarget.value.category_type,
          target_name: selectedTarget.value.name,
        })
      }
    })
  }
}

async function generateLink() {
  if (selectedPhotos.value.length === 0) {
    ElMessage.warning('请至少选择一张图片')
    return
  }

  generating.value = true
  try {
    const result = await request.post('/api/v1/reviews/create', {
      project_id: props.projectId,
      photo_selections: selectedPhotos.value,
      expired_days: expiredDays.value,
    })

    if (result.code === 200) {
      // 后端已返回完整 URL（如果配置了外网链接）或相对路径
      const shareUrlFromBackend = result.data.share_url

      // 如果是相对路径，拼接当前域名
      if (shareUrlFromBackend.startsWith('/')) {
        shareUrl.value = `${window.location.origin}${shareUrlFromBackend}`
      } else {
        // 已经是完整 URL
        shareUrl.value = shareUrlFromBackend
      }

      expiredAt.value = new Date(result.data.expired_at).toLocaleString('zh-CN')
      showResult.value = true
    } else {
      ElMessage.error(result.msg || '生成失败')
    }
  } catch (e: any) {
    console.error('生成链接失败:', e)
    ElMessage.error(e.message || '生成失败')
  } finally {
    generating.value = false
  }
}

function copyLink() {
  navigator.clipboard.writeText(shareUrl.value)
  ElMessage.success('链接已复制')
}

function onClose() {
  visible.value = false
  viewMode.value = 'create'
  selectedTarget.value = null
  selectedPhotos.value = []
  currentPhotos.value = []
}

async function switchToManagement() {
  viewMode.value = 'management'
  await loadSessions()
}

function switchToCreate() {
  viewMode.value = 'create'
}

async function loadSessions() {
  loadingSessions.value = true
  try {
    console.log('[loadSessions] 开始请求，projectId:', props.projectId)

    const url = `/api/v1/reviews/project/${props.projectId}/sessions`
    console.log('[loadSessions] 请求 URL:', url)

    const result = await request.get(url)
    console.log('[loadSessions] 响应数据:', result)

    if (result.code === 200) {
      sessions.value = result.data.sessions
      console.log('[loadSessions] 成功加载会话数量:', sessions.value.length)
    } else {
      console.error('[loadSessions] 业务错误:', result.msg)
      ElMessage.error(result.msg || '加载失败')
    }
  } catch (e: any) {
    console.error('[loadSessions] 捕获异常:', e)
    ElMessage.error(e.message || '加载会话列表失败')
  } finally {
    loadingSessions.value = false
  }
}

async function toggleDisable(row: any) {
  try {
    const result = await request.patch(`/api/v1/reviews/session/${row.id}/disable?is_disabled=${row.is_disabled}`)
    if (result.code === 200) {
      ElMessage.success(result.msg)
    } else {
      ElMessage.error(result.msg || '操作失败')
      row.is_disabled = !row.is_disabled
    }
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
    row.is_disabled = !row.is_disabled
  }
}

function copySessionLink(token: string) {
  const url = `${window.location.origin}/share/${token}`
  navigator.clipboard.writeText(url)
  ElMessage.success('链接已复制')
}

function formatDateTime(dateStr: string) {
  return new Date(dateStr).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<style scoped>
.share-modal {
  display: flex;
  gap: 16px;
  height: 600px;
}

.left-panel {
  width: 240px;
  border-right: 1px solid #e5e7eb;
  overflow-y: auto;
}

.category-header {
  font-size: 12px;
  font-weight: 600;
  color: #6b7280;
  padding: 12px 16px 8px;
  text-transform: uppercase;
}

.target-list {
  padding: 0 8px;
}

.target-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.target-item:hover {
  background: #f3f4f6;
}

.target-item.active {
  background: #eff6ff;
  color: #2563eb;
  font-weight: 500;
}

.count {
  font-size: 12px;
  color: #9ca3af;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
}

.photo-selection {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.selection-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 16px;
  border-bottom: 1px solid #e5e7eb;
  margin-bottom: 16px;
}

.target-title {
  font-size: 16px;
  font-weight: 600;
}

.actions {
  display: flex;
  gap: 12px;
}

.photo-grid {
  flex: 1;
  overflow-y: auto;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(132px, 132px));
  grid-auto-rows: 176px;
  align-content: start;
  justify-content: start;
  gap: 12px;
  padding: 4px;
}

.photo-card {
  position: relative;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
  height: 176px;
  border: 1px solid #e5e7eb;
  background: #fff;
}

.photo-card:hover .photo-img {
  border-color: #3b82f6;
}

.photo-card.selected .photo-img {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.photo-img {
  width: 100%;
  height: 132px;
  border: 2px solid transparent;
  border-radius: 8px;
  transition: all 0.2s;
}

.photo-img :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.photo-img-error {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f4f6;
  color: #9ca3af;
  font-weight: 700;
}

.photo-info {
  height: 42px;
  box-sizing: border-box;
  padding: 6px 8px;
  background: white;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.photo-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.check-mark {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 24px;
  height: 24px;
  background: #2563eb;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: bold;
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.selected-count {
  font-size: 14px;
  color: #6b7280;
}

.result-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.expire-info {
  font-size: 13px;
  color: #6b7280;
  text-align: center;
}

.management-view {
  height: 600px;
  overflow-y: auto;
}
</style>
