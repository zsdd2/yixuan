<template>
  <div class="project-center">
    <!-- 操作栏 -->
    <div class="action-bar">
      <el-button type="primary" @click="openCreate">+ 新建项目</el-button>
      <div class="action-bar-right">
        <el-input v-model="searchText" placeholder="搜索项目名称 / 编号 / 产品编码 / 客户" size="default" clearable style="width:280px" @keyup.enter="resetAndFetch">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <div class="filter-toggle" :class="{ active: showFilters || hasActiveFilters }" @click="showFilters = !showFilters">
          <span>筛选</span>
          <span class="filter-arrow" :class="{ expanded: showFilters }">›</span>
          <span v-if="hasActiveFilters" class="filter-dot"></span>
        </div>
      </div>
    </div>

    <!-- 筛选面板 -->
    <div v-if="showFilters" class="filter-panel">
      <div class="filter-row">
        <div class="filter-item">
          <span class="filter-label">状态</span>
          <el-select v-model="filters.status" clearable placeholder="全部" size="default" style="width:120px" @change="resetAndFetch">
            <el-option label="进行中" value="active" />
            <el-option label="已归档" value="archived" />
            <el-option label="已删除" value="deleted" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">客户</span>
          <el-select v-model="filters.client_id" clearable filterable placeholder="全部" size="default" style="width:140px" @visible-change="onFilterClientOpen" @change="resetAndFetch">
            <el-option v-for="c in filterClients" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">模板</span>
          <el-select v-model="filters.template_id" clearable placeholder="全部" size="default" style="width:120px" @visible-change="onFilterTemplateOpen" @change="resetAndFetch">
            <el-option v-for="t in filterTemplates" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </div>
        <div class="filter-item">
          <span class="filter-label">图量</span>
          <el-input-number v-model="filters.min_photo" :min="0" controls-position="right" size="default" style="width:85px" @change="resetAndFetch" />
          <span style="margin:0 2px;color:#c0c4cc;">-</span>
          <el-input-number v-model="filters.max_photo" :min="0" controls-position="right" size="default" style="width:85px" @change="resetAndFetch" />
        </div>
        <div class="filter-item">
          <span class="filter-label">时间</span>
          <el-date-picker v-model="filters.dateRange" type="daterange" range-separator="~" start-placeholder="起" end-placeholder="止" size="default" style="width:220px" @change="resetAndFetch" />
        </div>
        <el-button size="default" text @click="resetFilters">重置</el-button>
      </div>
    </div>

    <!-- 表格 -->
    <el-table
      :data="projects"
      v-loading="loading"
      style="width: 100%"
      row-class-name="project-row"
      @row-click="(row: ProjectItem) => $router.push(`/project/${row.id}`)"
    >
      <el-table-column prop="display_id" label="#" width="120" sortable>
        <template #default="{ row }">
          <span class="display-id">{{ row.display_id }}</span>
        </template>
      </el-table-column>

      <el-table-column label="封面" width="70" align="center">
        <template #default="{ row }">
          <div class="cover-cell" @click.stop>
            <img v-if="row.cover_image" :src="`/storage/${row.cover_image}`" class="cover-img" />
            <div v-else class="cover-placeholder">
              <span>{{ row.name.charAt(0) }}</span>
            </div>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="name" label="项目名称" min-width="160" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="project-name">{{ row.name }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="client_name" label="客户" min-width="100" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.client_name || '—' }}
        </template>
      </el-table-column>

      <el-table-column prop="customer_product_code" label="产品编码" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.customer_product_code" class="customer-code">{{ row.customer_product_code }}</span>
          <span v-else class="text-muted">-</span>
        </template>
      </el-table-column>

      <el-table-column prop="template_name" label="类型" width="100" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.shooting_type || row.template_name" size="small" type="info" effect="plain">{{ row.shooting_type || row.template_name }}</el-tag>
          <span v-else class="text-muted">—</span>
        </template>
      </el-table-column>

      <el-table-column label="状态" width="100" align="center">
        <template #default="{ row }">
          <el-tag :type="statusStyle(row).type" size="small" effect="light">{{ statusStyle(row).label }}</el-tag>
        </template>
      </el-table-column>

      <el-table-column label="目标进度" width="110" align="center">
        <template #default="{ row }">
          <span class="progress-text">
            <strong>{{ row.completed_target_count }}</strong> / {{ row.target_count }}
          </span>
        </template>
      </el-table-column>

      <el-table-column prop="photo_count" label="图量" width="80" align="center" sortable />

      <el-table-column prop="created_at" label="创建时间" width="160" sortable>
        <template #default="{ row }">
          {{ formatDate(row.created_at) }}
        </template>
      </el-table-column>

      <el-table-column label="操作" width="100" fixed="right" align="center">
        <template #default="{ row }">
          <el-dropdown trigger="click" @command="(cmd: string) => onCommand(cmd, row)" @click.stop>
            <el-button type="primary" link @click.stop>操作</el-button>
            <template #dropdown>
              <GlobalStatusMenu :current-status="row.project_status">
                <template #before>
                  <el-dropdown-item command="detail"><span class="mi">📋 详情</span></el-dropdown-item>
                  <el-dropdown-item command="edit"><span class="mi">✎ 编辑</span></el-dropdown-item>
                  <el-dropdown-item command="share"><span class="mi">🔗 分享</span></el-dropdown-item>
                </template>
                <template #after>
                  <el-dropdown-item divided :command="row.archived_at ? 'unarchive' : 'archive'">
                    <span class="mi">
                      <span class="sd" :style="{ background: row.archived_at ? '#67c23a' : '#e6a23c' }" />
                      {{ row.archived_at ? '取消归档' : '归档项目' }}
                    </span>
                  </el-dropdown-item>
                  <el-dropdown-item command="delete" divided><span class="mi mi-danger">🗑️ 删除</span></el-dropdown-item>
                </template>
              </GlobalStatusMenu>
            </template>
          </el-dropdown>
        </template>
      </el-table-column>

      <template #empty>
        <el-empty description="暂无项目数据" />
      </template>
    </el-table>

    <!-- 分页 -->
    <div v-if="total > limit" class="pagination-bar">
      <el-pagination
        v-model:current-page="currentPage"
        :page-size="limit"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="onPageChange"
      />
    </div>

    <!-- 新建项目弹窗 -->
    <el-dialog v-model="showCreate" title="新建项目" width="520px" destroy-on-close>
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="100px">
        <el-form-item label="选择客户" prop="client_id">
          <div class="flex gap-2 w-full">
            <el-select v-model="createForm.client_id" filterable placeholder="搜索选择客户" style="flex:1" @visible-change="onClientDropdownOpen">
              <el-option v-for="c in clientList" :key="c.id" :label="`${c.name} (${c.prefix})`" :value="c.id" />
            </el-select>
            <el-button @click="showQuickClient = true">+</el-button>
          </div>
        </el-form-item>
        <el-form-item label="项目名称" prop="name">
          <el-input v-model="createForm.name" placeholder="请输入项目名称" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="产品编码">
          <el-input v-model="createForm.customer_product_code" placeholder="客户侧产品编码/货号，可中英文" maxlength="128" show-word-limit />
        </el-form-item>
        <el-form-item label="拍摄类型">
          <div class="shooting-type-row">
            <el-select v-model="createForm.template_id" clearable placeholder="选择模板（可选）" style="flex:1" @visible-change="onTemplateDropdownOpen" @change="onTemplateChange">
              <el-option v-for="t in templateList" :key="t.id" :label="`${t.name} (${t.target_count}个目标)`" :value="t.id" />
            </el-select>
            <span style="color:#909399;font-size:13px;padding:0 6px;">或</span>
            <el-input v-model="createForm.shooting_type" :disabled="!!createForm.template_id" placeholder="手动输入类型" style="flex:1" maxlength="64" />
          </div>
          <div v-if="createForm.template_id" style="font-size:11px;color:#67c23a;margin-top:2px;">
            创建后将自动生成模板预设的目标
          </div>
        </el-form-item>
        <el-form-item label="截止时间">
          <el-date-picker v-model="createForm.estimated_end_time" type="datetime" placeholder="选择预估结束时间" style="width: 100%" />
        </el-form-item>
        <el-form-item label="项目介绍">
          <el-input v-model="createForm.description" type="textarea" :rows="3" placeholder="可选，填写项目介绍与要求" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="doCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 快捷新建客户弹窗 -->
    <el-dialog v-model="showQuickClient" title="快速新建客户" width="420px" destroy-on-close append-to-body>
      <el-form :model="quickClientForm" :rules="quickClientRules" ref="quickClientFormRef" label-width="90px">
        <el-form-item label="客户前缀" prop="prefix">
          <el-input v-model="quickClientForm.prefix" placeholder="如: XD（仅英文）" maxlength="10" />
        </el-form-item>
        <el-form-item label="客户姓名" prop="name">
          <el-input v-model="quickClientForm.name" placeholder="客户姓名" maxlength="64" />
        </el-form-item>
        <el-form-item label="电话">
          <el-input v-model="quickClientForm.phone" placeholder="选填" />
        </el-form-item>
        <el-form-item label="公司名称">
          <el-input v-model="quickClientForm.company" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showQuickClient = false">取消</el-button>
        <el-button type="primary" :loading="creatingClient" @click="doQuickCreateClient">创建</el-button>
      </template>
    </el-dialog>

    <!-- 创建后目标快速编辑弹窗 -->
    <el-dialog v-model="showTargetEdit" title="调整项目目标" width="700px" :close-on-click-modal="false">
      <p style="font-size:13px;color:#606266;margin-bottom:14px;">
        项目「<b>{{ newProjectName }}</b>」已创建成功，以下是模板预设的目标，可快速删减修改：
      </p>
      <div class="target-edit-list">
        <div v-for="(t, i) in editTargets" :key="t.id" class="target-edit-row">
          <span class="target-edit-index">{{ i + 1 }}</span>
          <el-input v-model="t.name" size="default" style="flex:2" />
          <el-select v-model="t.category_type" size="default" style="width:100px">
            <el-option label="白图" value="white" /><el-option label="场景" value="scene" />
          </el-select>
          <el-input v-model="t.requirement_desc" placeholder="拍摄要求" size="default" style="flex:3" />
          <el-button type="danger" text size="default" @click="deleteEditTarget(t, i)">删除</el-button>
        </div>
        <el-empty v-if="editTargets.length === 0" description="已清空所有目标" :image-size="40" />
      </div>
      <template #footer>
        <el-button @click="skipTargetEdit">跳过</el-button>
        <el-button type="primary" :loading="savingTargets" @click="saveTargetEdits">确认</el-button>
      </template>
    </el-dialog>

    <!-- 分享审核弹窗 -->
    <ShareReviewModal
      v-if="shareProjectId"
      v-model:visible="showShareReview"
      :project-id="shareProjectId"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import GlobalStatusMenu from '../components/GlobalStatusMenu.vue'
import ShareReviewModal from '../components/ShareReviewModal.vue'
import request from '../api/request'

interface ProjectItem {
  id: number
  name: string
  customer_product_code: string | null
  display_id: string
  cover_image: string | null
  client_name: string | null
  template_name: string | null
  photo_count: number
  target_count: number
  completed_target_count: number
  project_status: string
  archived_at: string | null
  deleted_at: string | null
  created_at: string
}

const router = useRouter()
const projects = ref<ProjectItem[]>([])
const loading = ref(false)
const searchText = ref('')
const showFilters = ref(false)
const total = ref(0)
const limit = 20
const currentPage = ref(1)

const filters = reactive({
  status: null as string | null,
  client_id: null as number | null,
  template_id: null as number | null,
  min_photo: undefined as number | undefined,
  max_photo: undefined as number | undefined,
  dateRange: null as [string, string] | null,
})

const filterClients = ref<{ id: number; name: string }[]>([])
const filterTemplates = ref<{ id: number; name: string }[]>([])

const hasActiveFilters = computed(() => {
  return !!(filters.status || filters.client_id || filters.template_id
    || (filters.min_photo !== undefined && filters.min_photo !== null)
    || (filters.max_photo !== undefined && filters.max_photo !== null)
    || filters.dateRange)
})

async function onFilterClientOpen(visible: boolean) {
  if (visible && filterClients.value.length === 0) {
    try { const d = await request.get('/api/v1/clients'); filterClients.value = d.items } catch {}
  }
}
async function onFilterTemplateOpen(visible: boolean) {
  if (visible && filterTemplates.value.length === 0) {
    try { const d = await request.get('/api/v1/settings/templates'); filterTemplates.value = d.items } catch {}
  }
}

function resetFilters() {
  filters.status = null; filters.client_id = null; filters.template_id = null
  filters.min_photo = undefined; filters.max_photo = undefined; filters.dateRange = null
  searchText.value = ''
  resetAndFetch()
}

function resetAndFetch() {
  currentPage.value = 1
  fetchProjects()
}

const showCreate = ref(false)
const creating = ref(false)
const createFormRef = ref<FormInstance>()
const createForm = reactive({
  name: '',
  customer_product_code: '',
  client_id: null as number | null,
  template_id: null as number | null,
  shooting_type: '',
  estimated_end_time: null as string | null,
  description: '',
})

// 分享审核
const showShareReview = ref(false)
const shareProjectId = ref<number | null>(null)
const createRules: FormRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  client_id: [{ required: true, message: '请选择客户', trigger: 'change' }],
}

interface ClientOption { id: number; name: string; prefix: string }
const clientList = ref<ClientOption[]>([])
const showQuickClient = ref(false)
const creatingClient = ref(false)
const quickClientFormRef = ref<FormInstance>()
const quickClientForm = reactive({ name: '', prefix: '', phone: '', company: '' })
const quickClientRules: FormRules = {
  prefix: [{ required: true, message: '请输入前缀', trigger: 'blur' }, { pattern: /^[A-Za-z]+$/, message: '仅英文', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
}

interface TemplateOption { id: number; name: string; target_count: number }
const templateList = ref<TemplateOption[]>([])

function formatDate(iso: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

function statusStyle(row: ProjectItem): { type: '' | 'success' | 'warning' | 'info' | 'danger'; label: string } {
  if (row.deleted_at) return { type: 'danger', label: '已删除' }
  if (row.archived_at) return { type: 'info', label: '已归档' }
  const map: Record<string, { type: '' | 'success' | 'warning' | 'info' | 'danger'; label: string }> = {
    not_started: { type: 'info', label: '未开始' },
    shooting: { type: '', label: '拍摄中' },
    retouching: { type: 'warning', label: '修图中' },
    completed: { type: 'success', label: '已完成' },
  }
  return map[row.project_status] || { type: 'info', label: '未开始' }
}

async function fetchProjects() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    params.set('skip', String((currentPage.value - 1) * limit))
    params.set('limit', String(limit))
    if (searchText.value) params.set('search', searchText.value)
    if (filters.status) params.set('status_filter', filters.status)
    if (filters.client_id) params.set('client_id', String(filters.client_id))
    if (filters.template_id) params.set('template_id', String(filters.template_id))
    if (filters.min_photo !== undefined && filters.min_photo !== null) params.set('min_photo_count', String(filters.min_photo))
    if (filters.max_photo !== undefined && filters.max_photo !== null) params.set('max_photo_count', String(filters.max_photo))
    if (filters.dateRange && filters.dateRange[0]) {
      const d0 = new Date(filters.dateRange[0])
      const d1 = new Date(filters.dateRange[1])
      params.set('date_from', `${d0.getFullYear()}-${String(d0.getMonth()+1).padStart(2,'0')}-${String(d0.getDate()).padStart(2,'0')}`)
      params.set('date_to', `${d1.getFullYear()}-${String(d1.getMonth()+1).padStart(2,'0')}-${String(d1.getDate()).padStart(2,'0')}`)
    }
    const data = await request.get(`/api/v1/projects?${params.toString()}`)
    projects.value = data.items
    total.value = data.total
  } catch { ElMessage.error('获取项目列表失败') }
  finally { loading.value = false }
}

function onPageChange(page: number) {
  currentPage.value = page
  fetchProjects()
}

function openCreate() {
  Object.assign(createForm, { name: '', customer_product_code: '', client_id: null, template_id: null, shooting_type: '', estimated_end_time: null, description: '' })
  showCreate.value = true
}

function onTemplateChange(val: number | null) {
  if (val) {
    const tpl = templateList.value.find(t => t.id === val)
    if (tpl) createForm.shooting_type = tpl.name
  } else {
    createForm.shooting_type = ''
  }
}

function onCommand(cmd: string, row: ProjectItem) {
  if (cmd === 'detail') {
    router.push(`/project/${row.id}`)
  } else if (cmd === 'edit') {
    router.push(`/project/${row.id}/edit`)
  } else if (cmd === 'share') {
    shareProjectId.value = row.id
    showShareReview.value = true
  } else if (cmd === 'archive') {
    confirmArchive(row)
  } else if (cmd === 'unarchive') {
    doUnarchive(row)
  } else if (cmd === 'delete') {
    confirmDelete(row)
  } else if (cmd.startsWith('status:')) {
    setProjectStatus(row, cmd.replace('status:', ''))
  }
}

async function setProjectStatus(row: ProjectItem, newStatus: string) {
  try {
    // 如果设置为已完成状态，提示是否归档
    if (newStatus === 'completed' && !row.archived_at) {
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
        await confirmArchive(row)
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

    await request.patch(`/api/v1/projects/${row.id}`, { project_status: newStatus })
    ElMessage.success('项目状态已更新')
    await fetchProjects()
  } catch (e: any) {
    ElMessage.error(e.message || '修改失败')
  }
}

async function confirmArchive(row: ProjectItem) {
  try { await ElMessageBox.confirm(`确定归档项目「${row.name}」？归档后 15 天将自动清理回收站内容。`, '归档确认', { type: 'warning' }) } catch { return }
  try {
    await request.post(`/api/v1/projects/${row.id}/archive`)
    ElMessage.success('项目已归档并标记为已完成')
    await fetchProjects()
  } catch { ElMessage.error('归档失败') }
}

async function doUnarchive(row: ProjectItem) {
  try {
    await request.post(`/api/v1/projects/${row.id}/unarchive`)
    ElMessage.success('已取消归档')
    await fetchProjects()
  } catch { ElMessage.error('操作失败') }
}

async function confirmDelete(row: ProjectItem) {
  try { await ElMessageBox.confirm(`确定删除项目「${row.name}」？`, '删除确认', { type: 'warning' }) } catch { return }
  try {
    await request.post(`/api/v1/projects/${row.id}/soft-delete`)
    ElMessage.success('项目已移入回收站')
    await fetchProjects()
  } catch { ElMessage.error('删除失败') }
}

async function fetchClients() {
  try {
    const d = await request.get('/api/v1/clients')
    clientList.value = d.items
  } catch {}
}
function onClientDropdownOpen(visible: boolean) { if (visible) fetchClients() }

async function fetchTemplates() {
  try {
    const d = await request.get('/api/v1/settings/templates')
    templateList.value = d.items
  } catch {}
}
function onTemplateDropdownOpen(visible: boolean) { if (visible) fetchTemplates() }

async function doCreate() {
  const valid = await createFormRef.value?.validate().catch(() => false)
  if (!valid) return
  creating.value = true
  try {
    const body: Record<string, any> = {
      name: createForm.name.trim(),
      client_id: createForm.client_id,
    }
    if (createForm.template_id) body.template_id = createForm.template_id
    if (createForm.customer_product_code?.trim()) body.customer_product_code = createForm.customer_product_code.trim()
    if (createForm.shooting_type?.trim()) body.shooting_type = createForm.shooting_type.trim()
    if (createForm.estimated_end_time) body.estimated_end_time = createForm.estimated_end_time
    if (createForm.description?.trim()) body.description = createForm.description.trim()

    const created = await request.post('/api/v1/projects', body)
    ElMessage.success('项目创建成功')
    showCreate.value = false

    if (createForm.template_id) {
      newProjectId.value = created.id
      newProjectName.value = createForm.name.trim()
      await fetchCreatedTargets(created.id)
      showTargetEdit.value = true
    }

    await fetchProjects()
  } catch (e: any) { ElMessage.error(e.message || '创建失败') }
  finally { creating.value = false }
}

async function doQuickCreateClient() {
  const valid = await quickClientFormRef.value?.validate().catch(() => false)
  if (!valid) return
  creatingClient.value = true
  try {
    const data = await request.post('/api/v1/clients', {
      name: quickClientForm.name,
      prefix: quickClientForm.prefix.toUpperCase(),
      phone: quickClientForm.phone || null,
      company: quickClientForm.company || null
    })
    await fetchClients()
    createForm.client_id = data.id
    showQuickClient.value = false
    Object.assign(quickClientForm, { name: '', prefix: '', phone: '', company: '' })
    ElMessage.success('客户已创建')
  } catch (e: any) { ElMessage.error(e.message) }
  finally { creatingClient.value = false }
}

// ═══ 创建后目标快速编辑 ═══
const showTargetEdit = ref(false)
const newProjectId = ref<number | null>(null)
const newProjectName = ref('')
const editTargets = ref<any[]>([])
const savingTargets = ref(false)

async function fetchCreatedTargets(projectId: number) {
  try {
    const d = await request.get(`/api/v1/projects/${projectId}/targets`)
    editTargets.value = d.items.map((t: any) => ({ ...t }))
  } catch {}
}

async function deleteEditTarget(t: any, index: number) {
  if (t.id && newProjectId.value) {
    try {
      await request.delete(`/api/v1/projects/${newProjectId.value}/targets/${t.id}`)
    } catch {}
  }
  editTargets.value.splice(index, 1)
}

async function saveTargetEdits() {
  if (!newProjectId.value) return
  savingTargets.value = true
  try {
    for (const t of editTargets.value) {
      if (t.id) {
        await request.patch(`/api/v1/projects/${newProjectId.value}/targets/${t.id}`, {
          name: t.name,
          category_type: t.category_type,
          requirement_desc: t.requirement_desc || null
        })
      }
    }
    ElMessage.success('目标已更新')
    showTargetEdit.value = false
  } catch { ElMessage.error('保存失败') }
  finally { savingTargets.value = false }
}

function skipTargetEdit() {
  showTargetEdit.value = false
}

onMounted(() => {
  fetchProjects()
  fetchClients()
})
</script>

<style scoped>
.project-center {
  padding: 20px 28px;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.action-bar {
  display: flex;
  align-items: center;
  background: white;
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.action-bar-right {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-left: auto;
}

.filter-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 13px;
  color: #606266;
  cursor: pointer;
  transition: all 0.15s;
  user-select: none;
  position: relative;
}

.filter-toggle:hover { background: #f5f7fa; color: #303133; }
.filter-toggle.active { color: #409eff; }

.filter-arrow {
  font-size: 14px;
  transition: transform 0.2s ease;
  transform: rotate(0deg);
}

.filter-arrow.expanded {
  transform: rotate(90deg);
}

.filter-dot {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #f56c6c;
}

.filter-panel {
  background: white;
  padding: 12px 16px;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.filter-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.filter-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
}

:deep(.project-row) {
  cursor: pointer;
  height: 64px;
}

:deep(.project-row:hover > td) {
  background: #fafbfc !important;
}

:deep(.el-table) {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

:deep(.el-table th.el-table__cell) {
  background: #fafbfc;
  font-weight: 600;
  color: #606266;
  font-size: 13px;
}

.display-id {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 13px;
  font-weight: 600;
  color: #409eff;
}

.cover-cell {
  width: 40px;
  height: 40px;
  border-radius: 4px;
  overflow: hidden;
  margin: 0 auto;
}

.cover-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 14px;
  font-weight: 700;
}

.project-name {
  font-weight: 500;
  color: #303133;
}

.text-muted {
  color: #c0c4cc;
}

.progress-text {
  font-size: 13px;
  color: #606266;
}

.progress-text strong {
  color: #67c23a;
  font-weight: 700;
}

.pagination-bar {
  display: flex;
  justify-content: flex-end;
  padding: 12px 0;
}

.flex { display: flex; }
.gap-2 { gap: 8px; }
.w-full { width: 100%; }
.shooting-type-row { display: flex; align-items: center; width: 100%; }

.target-edit-list { display: flex; flex-direction: column; gap: 8px; max-height: 400px; overflow-y: auto; }
.target-edit-row { display: flex; align-items: center; gap: 8px; }
.target-edit-index { width: 24px; text-align: center; font-size: 13px; color: #909399; flex-shrink: 0; }

/* Unified context menu */
.ctx-menu { min-width: 160px; padding: 4px 0; }
.mi { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.mi-danger { color: #f56c6c; }
.sd { display: inline-block; width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
</style>
