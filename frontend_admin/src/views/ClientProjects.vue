<template>
  <div class="client-projects-page">
    <div class="page-head">
      <div>
        <el-button text @click="router.push('/clients')">返回客户管理</el-button>
        <h1>{{ clientName }}项目汇总</h1>
        <p>按客户快速查看项目合计、进行中和已完成项目。</p>
      </div>
      <el-segmented v-model="statusFilter" :options="statusOptions" @change="fetchProjects" />
    </div>

    <div class="summary-row">
      <button class="summary-card" :class="{ active: statusFilter === 'all' }" @click="setStatus('all')">
        <span>项目合计</span>
        <b>{{ totals.all }}</b>
      </button>
      <button class="summary-card" :class="{ active: statusFilter === 'active' }" @click="setStatus('active')">
        <span>进行中</span>
        <b>{{ totals.active }}</b>
      </button>
      <button class="summary-card" :class="{ active: statusFilter === 'completed' }" @click="setStatus('completed')">
        <span>已完成</span>
        <b>{{ totals.completed }}</b>
      </button>
    </div>

    <el-table :data="projects" v-loading="loading" border stripe @row-click="openProject">
      <el-table-column prop="display_id" label="项目编号" width="130" />
      <el-table-column label="封面" width="82" align="center">
        <template #default="{ row }">
          <img v-if="row.cover_image" :src="`/storage/${row.cover_image}`" class="cover-img" />
          <div v-else class="cover-placeholder">{{ row.name.charAt(0) }}</div>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="项目名称" min-width="180" show-overflow-tooltip />
      <el-table-column prop="shooting_type" label="拍摄类型" width="130">
        <template #default="{ row }">{{ row.shooting_type || row.template_name || '—' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="110" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="row.archived_at ? 'success' : 'primary'" effect="light">
            {{ row.archived_at ? '已完成' : statusLabel[row.project_status] || '进行中' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="白图" width="110" align="center">
        <template #default="{ row }">{{ row.white_completed }} / {{ row.white_target }}</template>
      </el-table-column>
      <el-table-column label="场景图" width="110" align="center">
        <template #default="{ row }">{{ row.scene_completed }} / {{ row.scene_target }}</template>
      </el-table-column>
      <el-table-column prop="photo_count" label="图量" width="90" align="center" />
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right" align="center">
        <template #default="{ row }">
          <el-button type="primary" link @click.stop="openProject(row)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../api/request'

interface ProjectItem {
  id: number
  display_id: string
  name: string
  cover_image: string | null
  template_name?: string | null
  shooting_type?: string | null
  project_status: string
  archived_at: string | null
  white_target: number
  scene_target: number
  white_completed: number
  scene_completed: number
  photo_count: number
  created_at: string
}

const route = useRoute()
const router = useRouter()
const clientId = computed(() => Number(route.params.clientId))
const clientName = ref('客户')
const projects = ref<ProjectItem[]>([])
const loading = ref(false)
const statusFilter = ref(String(route.query.status || 'all'))
const statusOptions = [
  { label: '全部项目', value: 'all' },
  { label: '进行中', value: 'active' },
  { label: '已完成', value: 'completed' },
]
const statusLabel: Record<string, string> = {
  not_started: '未开始',
  shooting: '拍摄中',
  retouching: '修图中',
  client_review: '客户审核',
  completed: '已完成',
}

const totals = computed(() => ({
  all: projects.value.length,
  active: projects.value.filter(p => !p.archived_at).length,
  completed: projects.value.filter(p => !!p.archived_at).length,
}))

async function fetchClient() {
  const data = await request.get(`/api/v1/clients/${clientId.value}`)
  clientName.value = data.name || '客户'
}

async function fetchProjects() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    params.set('client_id', String(clientId.value))
    params.set('include_completed', 'true')
    params.set('limit', '100')
    if (statusFilter.value === 'active') params.set('status_filter', 'active')
    if (statusFilter.value === 'completed') params.set('status_filter', 'archived')
    const data = await request.get(`/api/v1/projects?${params.toString()}`)
    projects.value = data.items || []
    router.replace({ query: { status: statusFilter.value } })
  } catch (e: any) {
    ElMessage.error(e.message || '项目列表加载失败')
  } finally {
    loading.value = false
  }
}

function setStatus(value: string) {
  statusFilter.value = value
  fetchProjects()
}

function openProject(row: ProjectItem) {
  router.push({ name: 'ProjectDetail', params: { id: row.id } })
}

function formatDate(value: string) {
  if (!value) return '-'
  const date = new Date(value)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

watch(() => route.query.status, value => {
  statusFilter.value = String(value || 'all')
})

onMounted(() => {
  fetchClient()
  fetchProjects()
})
</script>

<style scoped>
.client-projects-page {
  min-height: 100%;
  padding: 20px 28px;
  background: #f4f8fc;
}
.page-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
}
.page-head h1 {
  margin: 6px 0 4px;
  font-size: 26px;
  color: #0f172a;
}
.page-head p {
  margin: 0;
  color: #667085;
}
.summary-row {
  display: grid;
  grid-template-columns: repeat(3, 180px);
  gap: 12px;
  margin-bottom: 14px;
}
.summary-card {
  height: 86px;
  text-align: left;
  padding: 14px 18px;
  background: #fff;
  border: 1px solid #d7e0ea;
  border-radius: 8px;
  cursor: pointer;
}
.summary-card.active {
  border-color: #2f7df6;
  box-shadow: 0 0 0 2px rgba(47, 125, 246, 0.12);
}
.summary-card span {
  display: block;
  color: #667085;
  font-weight: 700;
}
.summary-card b {
  display: block;
  margin-top: 8px;
  font-size: 28px;
  color: #0f172a;
}
.cover-img,
.cover-placeholder {
  width: 48px;
  height: 36px;
  border-radius: 6px;
}
.cover-img {
  object-fit: cover;
}
.cover-placeholder {
  display: grid;
  place-items: center;
  margin: 0 auto;
  color: #fff;
  background: #8aa4c3;
  font-weight: 800;
}
</style>
