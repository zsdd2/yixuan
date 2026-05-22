<template>
  <el-dialog
    v-model="visibleModel"
    :title="viewMode === 'create' ? '创建客户交付分享' : '分享管理'"
    width="800px"
    :close-on-click-modal="false"
    @close="handleClose"
  >
    <!-- 创建视图 -->
    <div v-if="viewMode === 'create'">
      <el-form :model="form" label-width="120px">
        <el-form-item label="有效期">
          <el-select v-model="form.expiredDays" style="width: 100%;">
            <el-option label="1天" :value="1" />
            <el-option label="3天" :value="3" />
            <el-option label="7天" :value="7" />
            <el-option label="15天" :value="15" />
            <el-option label="30天" :value="30" />
            <el-option label="60天" :value="60" />
            <el-option label="90天" :value="90" />
          </el-select>
        </el-form-item>
      </el-form>

      <div v-if="shareUrl" class="share-result">
        <el-alert type="success" :closable="false" style="margin-bottom: 16px;">
          <template #title>
            <div style="font-weight: 600;">分享链接已生成</div>
          </template>
        </el-alert>

        <div class="url-box">
          <el-input v-model="shareUrl" readonly>
            <template #append>
              <el-button @click="copyUrl">
                <el-icon><DocumentCopy /></el-icon>
                复制
              </el-button>
            </template>
          </el-input>
        </div>
        <div class="expire-info">链接将于 {{ expiredAt }} 过期</div>
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
        <el-table-column label="ZIP状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.zip_status === 'completed'" type="success" size="small">已完成</el-tag>
            <el-tag v-else-if="row.zip_status === 'processing'" type="warning" size="small">打包中</el-tag>
            <el-tag v-else-if="row.zip_status === 'failed'" type="danger" size="small">失败</el-tag>
            <el-tag v-else type="info" size="small">待处理</el-tag>
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
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="copySessionLink(row.token)">
              复制链接
            </el-button>
            <el-button size="small" text type="danger" @click="deleteSession(row.id)">
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <template #footer>
      <div class="footer-content">
        <div></div>
        <div style="display: flex; align-items: center; gap: 12px;">
          <el-button v-if="viewMode === 'create'" text type="primary" @click="switchToManagement">
            查看已有分享
          </el-button>
          <el-button v-else text type="primary" @click="switchToCreate">
            返回创建
          </el-button>
          <el-button @click="handleClose">{{ viewMode === 'create' ? '取消' : '关闭' }}</el-button>
          <el-button v-if="viewMode === 'create'" type="primary" @click="createShare" :loading="creating" :disabled="!!shareUrl">
            生成分享链接
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { DocumentCopy } from '@element-plus/icons-vue'
import request from '../api/request'

interface Props {
  projectId: number
  visible: boolean
}

const props = defineProps<Props>()
const emit = defineEmits(['update:visible', 'created'])

const visibleModel = computed({
  get: () => props.visible,
  set: (val) => emit('update:visible', val)
})

const form = ref({
  expiredDays: 30 as number
})

const creating = ref(false)
const shareUrl = ref('')
const expiredAt = ref('')
const viewMode = ref<'create' | 'management'>('create')
const sessions = ref<any[]>([])
const loadingSessions = ref(false)

watch(() => props.visible, async (val) => {
  if (val) {
    viewMode.value = 'create'
  }
})

async function createShare() {
  creating.value = true
  try {
    const result = await request.post('/api/v1/deliveries/create', {
      project_id: props.projectId,
      expired_days: form.value.expiredDays
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
      ElMessage.success('分享链接已生成')
      emit('created')
    } else {
      ElMessage.error(result.msg || '生成失败')
    }
  } catch (e: any) {
    console.error('创建分享失败:', e)
    const messageMap: Record<string, string> = {
      'Only completed projects can create delivery links': '请先将项目状态设为“已完成”，再生成交付分享链接',
      'Project has no final delivery photos': '当前项目没有最终交付图，无法生成交付分享链接',
    }
    ElMessage.error(`生成失败: ${messageMap[e.message] || e.message || '网络错误'}`)
  } finally {
    creating.value = false
  }
}

function copyUrl() {
  navigator.clipboard.writeText(shareUrl.value).then(() => {
    ElMessage.success('已复制到剪贴板')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
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
    const result = await request.get(`/api/v1/deliveries/project/${props.projectId}/sessions`)
    if (result.code === 200) {
      sessions.value = result.data.items
    } else {
      ElMessage.error(result.msg || '加载失败')
    }
  } catch (e: any) {
    console.error('[loadSessions] 捕获异常:', e)
    ElMessage.error(`加载会话列表失败: ${e.message || '网络错误'}`)
  } finally {
    loadingSessions.value = false
  }
}

async function toggleDisable(row: any) {
  try {
    const result = await request.patch(`/api/v1/deliveries/session/${row.id}/disable`)
    if (result.code === 200) {
      ElMessage.success(result.msg)
    } else {
      ElMessage.error(result.msg || '操作失败')
      row.is_disabled = !row.is_disabled
    }
  } catch (e: any) {
    ElMessage.error('操作失败')
    row.is_disabled = !row.is_disabled
  }
}

async function deleteSession(sessionId: number) {
  try {
    await ElMessageBox.confirm('确认删除此分享记录？', '提示', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning',
    })

    const result = await request.delete(`/api/v1/deliveries/${sessionId}`)
    if (result.code === 200) {
      ElMessage.success('删除成功')
      await loadSessions()
    } else {
      ElMessage.error(result.msg || '删除失败')
    }
  } catch (e: any) {
    if (e !== 'cancel') {
      console.error('删除失败:', e)
      ElMessage.error('删除失败')
    }
  }
}

function copySessionLink(token: string) {
  const url = `${window.location.origin}/delivery/${token}`
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

function handleClose() {
  visibleModel.value = false
  viewMode.value = 'create'
  setTimeout(() => {
    form.value = {
      expiredDays: 30
    }
    shareUrl.value = ''
    expiredAt.value = ''
  }, 300)
}
</script>

<style scoped>
.share-result {
  margin-top: 24px;
  padding-top: 24px;
  border-top: 1px solid #ebeef5;
}

.url-box {
  margin-top: 16px;
}

.expire-info {
  font-size: 13px;
  color: #6b7280;
  text-align: center;
  margin-top: 12px;
}

.footer-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.management-view {
  min-height: 400px;
  max-height: 600px;
  overflow-y: auto;
}
</style>
