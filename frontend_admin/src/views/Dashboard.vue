<template>
  <div class="min-h-screen">
    <!-- 顶部 Header -->
    <div class="flex justify-between items-center mx-auto border-b border-gray-100" style="height: 82px; max-width: 1400px; padding: 0 32px;">
      <h1 style="font-size: 28px;" class="font-bold text-gray-800 tracking-tight leading-none">进度工作台</h1>
      <div class="flex items-center gap-3">
        <el-checkbox v-model="showCompleted" @change="fetchProjects" label="显示已完成" />
        <button
          class="create-project-btn"
          @click="showCreate = true"
        >
          <span class="btn-icon">+</span>
          <span class="btn-text">新建项目</span>
        </button>
      </div>
    </div>

    <!-- 内容区 -->
    <div class="mx-auto pt-4 pb-10" style="max-width: 1400px; padding-left: 32px; padding-right: 32px;">

    <!-- 骨架屏加载 -->
    <div v-if="loading" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
      <div v-for="i in 8" :key="i" class="bg-white rounded-2xl overflow-hidden shadow-sm">
        <el-skeleton animated>
          <template #template>
            <el-skeleton-item variant="image" style="width: 100%; height: 180px" />
            <div class="p-5 space-y-4">
              <el-skeleton-item variant="h3" style="width: 60%" />
              <el-skeleton-item variant="text" style="width: 80%" />
              <el-skeleton-item variant="text" style="width: 100%" />
              <el-skeleton-item variant="text" style="width: 100%" />
            </div>
          </template>
        </el-skeleton>
      </div>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="flex justify-center py-20">
      <el-result
        icon="warning"
        title="数据加载失败"
        :sub-title="isServerError ? '数据库可能未同步，请联系管理员执行迁移脚本 (python reset_db.py)' : error"
      >
        <template #extra>
          <el-button type="primary" @click="fetchProjects">重新加载</el-button>
        </template>
      </el-result>
    </div>

    <!-- 空状态 -->
    <div v-else-if="projects.length === 0" class="flex justify-center py-28">
      <el-empty description="还没有项目，开始创建第一个吧">
        <button class="px-5 py-2 text-sm font-medium text-gray-800 bg-white border border-gray-300 rounded-xl hover:border-gray-400 transition-colors" @click="showCreate = true">+ 新建项目</button>
      </el-empty>
    </div>

    <!-- 项目列表 4列 -->
    <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
      <ProjectCard
        v-for="project in projects"
        :key="project.id"
        :project="project"
        @updated="fetchProjects"
      />
    </div>

    </div><!-- /内容区 -->

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
        <el-form-item label="拍摄类型">
          <div style="display:flex;align-items:center;width:100%;">
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import ProjectCard from '../components/ProjectCard.vue'
import request from '../api/request'

export interface Project {
  id: number
  name: string
  display_id: string
  cover_image: string | null
  client_name: string | null
  created_by: number
  photo_count: number
  target_count: number
  white_target: number
  scene_target: number
  white_count: number
  scene_count: number
  white_completed: number
  scene_completed: number
  estimated_end_time: string | null
  archived_at: string | null
  description: string | null
  project_status: string
  created_at: string
}

interface ProjectListResponse {
  total: number
  items: Project[]
  skip: number
  limit: number
}

const projects = ref<Project[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const errorStatus = ref(0)
const showCreate = ref(false)
const creating = ref(false)
const showCompleted = ref(false)
const createFormRef = ref<FormInstance>()
const createForm = reactive({
  name: '',
  client_id: null as number | null,
  template_id: null as number | null,
  shooting_type: '',
  estimated_end_time: null as string | null,
  description: '',
})

const isServerError = computed(() => errorStatus.value >= 500)

// ── Client selection ──
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

async function fetchClients() {
  try {
    const d = await request.get('/api/v1/clients')
    clientList.value = d.items
  } catch {}
}
function onClientDropdownOpen(visible: boolean) { if (visible) fetchClients() }

// ── Template selection ──
interface TemplateOption { id: number; name: string; target_count: number }
const templateList = ref<TemplateOption[]>([])

async function fetchTemplates() {
  try {
    const d = await request.get('/api/v1/settings/templates')
    templateList.value = d.items
  } catch {}
}
function onTemplateDropdownOpen(visible: boolean) { if (visible) fetchTemplates() }

function onTemplateChange(val: number | null) {
  if (val) {
    const tpl = templateList.value.find(t => t.id === val)
    if (tpl) createForm.shooting_type = tpl.name
  } else {
    createForm.shooting_type = ''
  }
}

const createRules: FormRules = {
  name: [{ required: true, message: '请输入项目名称', trigger: 'blur' }],
  client_id: [{ required: true, message: '请选择客户', trigger: 'change' }],
}

async function fetchProjects() {
  loading.value = true
  error.value = null
  errorStatus.value = 0
  try {
    const params: Record<string, any> = {}
    if (showCompleted.value) params.include_completed = 'true'
    const data: ProjectListResponse = await request.get('/api/v1/projects', params)
    projects.value = data.items
  } catch (e: any) {
    error.value = e.message || '网络错误，请稍后重试'
    errorStatus.value = 500
  } finally {
    loading.value = false
  }
}

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
    if (createForm.shooting_type?.trim()) body.shooting_type = createForm.shooting_type.trim()
    if (createForm.estimated_end_time) body.estimated_end_time = createForm.estimated_end_time
    if (createForm.description) body.description = createForm.description
    if (createForm.description.trim()) body.description = createForm.description.trim()

    await request.post('/api/v1/projects', body)
    ElMessage.success('项目创建成功')
    showCreate.value = false
    Object.assign(createForm, { name: '', client_id: null, template_id: null, shooting_type: '', estimated_end_time: null, description: '' })
    await fetchProjects()
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    creating.value = false
  }
}

onMounted(() => {
  fetchProjects()
  fetchClients()
})

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
</script>

<style scoped>
.create-project-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 18px;
  font-weight: 500;
  color: #1f2937;
  background: white;
  border: 1px solid #1f2937;
  border-radius: 16px;
  padding: 8px 20px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.create-project-btn:hover {
  background: #f9fafb;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.create-project-btn .btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  border: 1px solid #1f2937;
  border-radius: 50%;
  font-size: 16px;
  line-height: 1;
}

.create-project-btn .btn-text {
  line-height: 1;
}
</style>
