<template>
  <div class="project-detail">
    <!-- 三区段工作台视图 -->
    <TargetDetail
      v-if="activeTargetId !== null"
      :project-id="projectId"
      :target-id="activeTargetId"
      @back="activeTargetId = null; fetchTargets()"
      @open-shuttle="shuttleTargetId = activeTargetId"
    />

    <ProjectBilling
      v-else-if="showBilling"
      :project-id="Number(projectId)"
      @back="showBilling = false; fetchTargets()"
    />

    <!-- 最终交付图视图 -->
    <ProjectDelivery
      v-else-if="showDelivery"
      :project-id="projectId"
      @back="showDelivery = false"
    />

    <!-- 溯源看板视图 -->
    <LineageBoard
      v-else-if="lineageTargetId !== null"
      :project-id="projectId"
      @back="lineageTargetId = null"
      @open-shuttle="shuttleTargetId = lineageTargetId"
    />

    <!-- 目标卡片看板 -->
    <div v-else>
      <!-- 返回按钮 -->
      <div class="back-button-wrapper">
        <el-button @click="goBack" :icon="ArrowLeft" text>返回工作台</el-button>
      </div>

      <!-- 项目详情头部卡片 -->
      <div class="project-header-card">
        <!-- 左侧封面 -->
        <div class="header-cover">
          <el-image v-if="projectCoverImage" :src="`${API_BASE}/storage/${projectCoverImage}`" fit="cover" class="header-cover-img" />
          <div v-else class="header-cover-placeholder">
            <svg width="48" height="48" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="0.8" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" /></svg>
          </div>
        </div>

        <!-- 右侧信息区 -->
        <div class="header-info">
          <!-- 标题行 -->
          <div class="header-title-row">
            <div class="header-title-left">
              <h1 class="header-project-name">{{ projectName }}</h1>
              <span class="header-project-id">{{ projectDisplayId }}</span>
            </div>
            <div class="header-actions">
              <el-button class="action-btn" @click="goImport">
                📤 导入图片
              </el-button>
              <el-button class="action-btn" @click="showGroupManager = true">
                组合管理
              </el-button>
              <el-button class="action-btn action-btn-primary" @click="showShareReview = true">
                📤 分享审核
              </el-button>
              <el-button class="action-btn" @click="showBilling = true">
                账目明细
              </el-button>
              <el-button class="action-btn" :icon="Plus" @click="showCreateTarget = true">
                新增目标
              </el-button>
              <el-button
                class="action-btn"
                :type="isArchived ? 'info' : 'danger'"
                @click="onToggleArchive"
                plain
              >
                {{ isArchived ? '取消归档' : '项目归档' }}
              </el-button>
            </div>
          </div>

          <!-- 核心指标栅格 -->
          <div class="header-metrics">
            <!-- 客户信息 -->
            <div class="metric-block">
              <div class="metric-label">客户信息</div>
              <div class="metric-value">{{ projectClientName || '—' }}</div>
              <div class="metric-sub">{{ projectClientContact || '暂无联系方式' }}</div>
            </div>

            <!-- 时间节点 -->
            <div class="metric-block">
              <div class="metric-label">时间节点</div>
              <div class="metric-value">{{ projectEstimatedEnd ? formatDate(projectEstimatedEnd) : '未设置截止' }}</div>
              <div class="metric-sub">{{ remainingDaysText }}</div>
            </div>

            <!-- 进度快报 -->
            <div class="metric-block">
              <div class="metric-label">进度快报</div>
              <div class="metric-value">{{ progressQuickValue }}</div>
              <div class="metric-sub">{{ progressQuickSub }}</div>
            </div>
          </div>

          <!-- 项目描述（如果有） -->
          <div v-if="projectDescription" class="header-description">
            {{ projectDescription }}
          </div>
        </div>
      </div>

      <!-- 归档状态提示条 -->
      <div v-if="isArchived && archivedAt" class="archive-banner">
        <el-icon><WarningFilled /></el-icon>
        <span>
          本项目已于 {{ formatDate(archivedAt) }} 归档，回收站照片将于
          <b>{{ formatDate(cleanupDueAt) }}</b> 自动清理
        </span>
      </div>

      <!-- 看板主体 -->
      <div v-loading="loading" class="kanban-container">

        <!-- 最终交付图入口卡片 -->
        <div v-if="finalPhotoCount > 0" class="delivery-entry-card" @click="showDelivery = true">
          <div class="delivery-cover">
            <el-image v-if="deliveryCoverUrl" :src="deliveryCoverUrl" fit="cover" class="delivery-cover-img" />
            <div v-else class="delivery-cover-placeholder">📸</div>
          </div>
          <div class="delivery-entry-info">
            <h3 class="delivery-entry-title">最终交付图</h3>
            <span class="delivery-entry-count">{{ finalPhotoCount }} 张成片</span>
          </div>
        </div>

        <template v-if="projectGroups.length > 0">
          <div v-for="section in groupedTargetSections" :key="section.key" class="kanban-section group-kanban-section">
            <div class="section-header">
              <h3 class="section-title">{{ section.name }}</h3>
              <span class="section-count">{{ section.targets.length }} 个目标</span>
            </div>
            <div class="kanban-subtitle">场景图</div>
            <div class="kanban-grid">
              <TargetCard
                v-for="t in section.scene"
                :key="t.id"
                :target="t"
                @navigate-to-lineage="onNavigateToLineage"
                @open-shuttle="onOpenShuttle"
                @drill="onDrill"
                @complete="onComplete"
                @edit="onEdit"
                @delete="onDelete"
                @set-status="onSetStatus"
              />
              <div v-if="section.scene.length === 0" class="empty-hint">暂无场景图目标</div>
            </div>
            <div class="kanban-subtitle">白图</div>
            <div class="kanban-grid">
              <TargetCard
                v-for="t in section.white"
                :key="t.id"
                :target="t"
                @navigate-to-lineage="onNavigateToLineage"
                @open-shuttle="onOpenShuttle"
                @drill="onDrill"
                @complete="onComplete"
                @edit="onEdit"
                @delete="onDelete"
                @set-status="onSetStatus"
              />
              <div v-if="section.white.length === 0" class="empty-hint">暂无白图目标</div>
            </div>
          </div>
        </template>

        <template v-else>
        <!-- 场景图区 -->
        <div class="kanban-section">
          <div class="section-header">
            <h3 class="section-title">场景图</h3>
            <span class="section-count">{{ sceneTargets.length }} 个目标</span>
          </div>
          <div class="kanban-grid">
            <TargetCard
              v-for="t in sceneTargets"
              :key="t.id"
              :target="t"
              @navigate-to-lineage="onNavigateToLineage"
              @open-shuttle="onOpenShuttle"
              @drill="onDrill"
              @complete="onComplete"
              @edit="onEdit"
              @delete="onDelete"
              @set-status="onSetStatus"
            />
            <div v-if="sceneTargets.length === 0" class="empty-hint">
              暂无场景图目标
            </div>
          </div>
        </div>

        <!-- 白图区 -->
        <div class="kanban-section">
          <div class="section-header">
            <h3 class="section-title">白图</h3>
            <span class="section-count">{{ whiteTargets.length }} 个目标</span>
          </div>
          <div class="kanban-grid">
            <TargetCard
              v-for="t in whiteTargets"
              :key="t.id"
              :target="t"
              @navigate-to-lineage="onNavigateToLineage"
              @open-shuttle="onOpenShuttle"
              @drill="onDrill"
              @complete="onComplete"
              @edit="onEdit"
              @delete="onDelete"
              @set-status="onSetStatus"
            />
            <div v-if="whiteTargets.length === 0" class="empty-hint">
              暂无白图目标，点击右上角「新增目标」创建
            </div>
          </div>
        </div>
        </template>
      </div>
    </div>

    <!-- 照片穿梭分拣弹窗 -->
    <ShuttleModalWrapper :visible="shuttleTargetId !== null" @close="shuttleTargetId = null; fetchTargets()">
      <PhotoShuttle
        v-if="shuttleTargetId !== null"
        :project-id="projectId"
        :target-id="shuttleTargetId"
        @close="shuttleTargetId = null; fetchTargets()"
        @import="goImport"
      />
    </ShuttleModalWrapper>

    <!-- 新增目标弹窗 -->
    <el-dialog v-model="showCreateTarget" title="新增目标" width="600px" destroy-on-close @open="fetchAvailableTargets">
      <el-form :model="newTarget" label-width="80px">
        <el-form-item label="目标名称">
          <el-select
            v-model="newTarget.name"
            filterable
            placeholder="搜索或选择目标名称"
            style="width:100%"
            @change="onTargetNameSelected"
          >
            <el-option
              v-for="item in availableTargets"
              :key="item.name"
              :label="item.name"
              :value="item.name"
              :disabled="item.used"
            >
              <span>{{ item.name }}</span>
              <span style="float:right;font-size:11px;color:#909399">
                {{ item.category_type === 'white' ? '白图' : '场景' }}
                <span v-if="item.source === 'global'" style="color:#4080ff">· 通用</span>
                <span v-else style="color:#e6a23c">· 模板</span>
              </span>
            </el-option>
            <template #footer>
              <div v-if="!showInlineNewEntry" class="select-footer-add" @click="showInlineNewEntry = true">
                + 新建字典词条
              </div>
              <div v-else class="select-footer-form">
                <input
                  ref="inlineEntryInputRef"
                  v-model="inlineEntryName"
                  class="inline-entry-input"
                  placeholder="新词条名称"
                  @keydown.enter.stop="submitInlineEntry"
                  @keydown.stop
                />
                <select v-model="inlineEntryCat" class="inline-entry-cat">
                  <option value="white">白图</option>
                  <option value="scene">场景</option>
                </select>
                <button class="inline-entry-btn" @click="submitInlineEntry">添加</button>
                <button class="inline-entry-btn inline-entry-cancel" @click="showInlineNewEntry = false">取消</button>
              </div>
            </template>
          </el-select>
        </el-form-item>
        <el-form-item label="所属大类">
          <el-radio-group v-model="newTarget.category_type">
            <el-radio value="white">白图</el-radio>
            <el-radio value="scene">场景图</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="组合">
          <el-select v-model="newTarget.group_id" placeholder="未分组" clearable filterable style="width:100%">
            <el-option v-for="g in projectGroups" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="拍摄要求">
          <el-input v-model="newTarget.requirement_desc" type="textarea" :rows="3" placeholder="可选，填写拍摄要求" />
        </el-form-item>
        <el-form-item label="样图">
          <div class="sample-picker">
            <div v-if="newTarget.sample_path" class="current-sample">
              <el-image
                :src="getSampleUrl(newTarget.sample_path)"
                fit="cover"
                class="sample-preview"
              />
              <el-button size="small" text type="danger" @click="newTarget.sample_path = null">移除</el-button>
            </div>
            <el-button size="small" @click="samplePickerTarget = 'create'; showImagePicker = true">选择图片</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateTarget = false">取消</el-button>
        <el-button type="primary" @click="createTarget" :loading="creating">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑目标弹窗 -->
    <el-dialog v-model="showEditTarget" title="编辑目标" width="600px" destroy-on-close @open="fetchAvailableTargets">
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="目标名称">
          <el-select
            v-model="editForm.name"
            filterable
            placeholder="搜索或选择目标名称"
            style="width:100%"
            @change="onEditTargetNameChange"
          >
            <el-option
              v-for="item in availableTargets"
              :key="item.name"
              :label="item.name"
              :value="item.name"
            >
              <span>{{ item.name }}</span>
              <span style="float:right;font-size:11px;color:#909399">
                {{ item.category_type === 'white' ? '白图' : '场景' }}
                <span v-if="item.source === 'global'" style="color:#4080ff">· 通用</span>
                <span v-else style="color:#e6a23c">· 模板</span>
              </span>
            </el-option>
            <template #footer>
              <div v-if="!showInlineNewEntry" class="select-footer-add" @click="showInlineNewEntry = true">
                + 新建字典词条
              </div>
              <div v-else class="select-footer-form">
                <input
                  ref="inlineEntryInputRef"
                  v-model="inlineEntryName"
                  class="inline-entry-input"
                  placeholder="新词条名称"
                  @keydown.enter.stop="submitInlineEntryForEdit"
                  @keydown.stop
                />
                <select v-model="inlineEntryCat" class="inline-entry-cat">
                  <option value="white">白图</option>
                  <option value="scene">场景</option>
                </select>
                <button class="inline-entry-btn" @click="submitInlineEntryForEdit">添加</button>
                <button class="inline-entry-btn inline-entry-cancel" @click="showInlineNewEntry = false">取消</button>
              </div>
            </template>
          </el-select>
        </el-form-item>
        <el-form-item label="所属大类">
          <el-radio-group v-model="editForm.category_type">
            <el-radio value="white">白图</el-radio>
            <el-radio value="scene">场景图</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="组合">
          <el-select v-model="editForm.group_id" placeholder="未分组" clearable filterable style="width:100%">
            <el-option v-for="g in projectGroups" :key="g.id" :label="g.name" :value="g.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="拍摄要求">
          <el-input v-model="editForm.requirement_desc" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="样图">
          <div class="sample-picker">
            <div v-if="editForm.sample_path" class="current-sample">
              <el-image
                :src="getSampleUrl(editForm.sample_path)"
                fit="cover"
                class="sample-preview"
              />
              <el-button size="small" text type="danger" @click="editForm.sample_path = null">移除</el-button>
            </div>
            <el-button size="small" @click="samplePickerTarget = 'edit'; showImagePicker = true">选择图片</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditTarget = false">取消</el-button>
        <el-button type="primary" @click="submitEdit" :loading="editing">保存</el-button>
      </template>
    </el-dialog>

    <!-- 图片选择器 -->
    <el-dialog v-model="showGroupManager" title="项目组合管理" width="680px">
      <div class="group-manager">
        <div class="group-create-row">
          <el-input v-model="newGroupName" placeholder="输入组合/批次/商品组名称" clearable @keyup.enter="createGroup" />
          <el-button type="primary" :loading="savingGroup" @click="createGroup">新增组合</el-button>
        </div>
        <el-table :data="projectGroups" border style="width: 100%">
          <el-table-column prop="name" label="组合名称" min-width="180" />
          <el-table-column prop="target_count" label="目标数" width="90" align="center" />
          <el-table-column prop="photo_count" label="照片数" width="90" align="center" />
          <el-table-column label="操作" width="170" align="center">
            <template #default="{ row }">
              <el-button size="small" text type="primary" @click="renameGroup(row)">改名</el-button>
              <el-button size="small" text type="danger" @click="deleteGroup(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="group-manager-tip">删除组合只会取消组合归属，不会删除目标和照片。</div>
      </div>
    </el-dialog>

    <ImagePicker
      v-model:visible="showImagePicker"
      category="sample"
      :project-id="Number(projectId)"
      @confirm="onImagePicked"
    />

    <!-- 分享审核弹窗 -->
    <ShareReviewModal
      v-model:visible="showShareReview"
      :project-id="Number(projectId)"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  Plus,
  WarningFilled,
  PictureFilled,
} from '@element-plus/icons-vue'
import TargetCard from '../components/TargetCard.vue'
import TargetDetail from '../components/TargetDetail.vue'
import ImagePicker from '../components/ImagePicker.vue'
import ShuttleModalWrapper from '../components/ShuttleModalWrapper.vue'
import PhotoShuttle from '../components/PhotoShuttle.vue'
import ProjectDelivery from '../components/ProjectDelivery.vue'
import ProjectBilling from '../components/ProjectBilling.vue'
import LineageBoard from '../components/LineageBoard.vue'
import ShareReviewModal from '../components/ShareReviewModal.vue'
import type { TargetItem } from '../components/TargetCard.vue'
import request from '../api/request'

const API_BASE = ''
const route = useRoute()
const router = useRouter()

const projectId = computed(() => route.params.id as string)
const loading = ref(false)
const targets = ref<TargetItem[]>([])
interface ProjectGroup { id: number; project_id: number; name: string; description?: string | null; sort_order: number; target_count: number; photo_count: number }
const projectGroups = ref<ProjectGroup[]>([])
const showGroupManager = ref(false)
const newGroupName = ref('')
const savingGroup = ref(false)
const activeTargetId = ref<number | null>(null)
const lineageTargetId = ref<number | null>(null)
const shuttleTargetId = ref<number | null>(null)
const showDelivery = ref(false)
const showBilling = ref(false)
const archivedAt = ref<string | null>(null)
const projectName = ref('')
const projectDisplayId = ref('')
const projectCoverImage = ref<string | null>(null)
const projectDescription = ref<string | null>(null)
const projectClientName = ref<string | null>(null)
const projectClientContact = ref<string | null>(null)
const projectEstimatedEnd = ref<string | null>(null)
const projectCreatedAt = ref<string | null>(null)
const totalPhotoCount = ref(0)
const selectedPhotoCount = ref(0)
const retouchedPhotoCount = ref(0)
const showCreateTarget = ref(false)
const creating = ref(false)
const finalPhotoCount = ref(0)
const deliveryCoverUrl = ref<string | null>(null)
const showShareReview = ref(false)

const newTarget = reactive({
  name: '',
  group_id: null as number | null,
  category_type: 'white' as 'white' | 'scene',
  requirement_desc: '',
  sample_path: null as string | null,
})

// ── 字典选择器 ──
const availableTargets = ref<{ name: string; category_type: string; source: string; used: boolean }[]>([])
const showInlineNewEntry = ref(false)
const inlineEntryName = ref('')
const inlineEntryCat = ref('white')
const inlineEntryInputRef = ref<HTMLInputElement>()

async function fetchAvailableTargets() {
  try {
    const d = await request.get(`/api/v1/projects/${projectId.value}/available-targets`)
    availableTargets.value = d.items
  } catch {}
}

function onTargetNameSelected(name: string) {
  const entry = availableTargets.value.find(e => e.name === name)
  if (entry) {
    newTarget.category_type = entry.category_type as 'white' | 'scene'
  }
}

async function submitInlineEntry() {
  const name = inlineEntryName.value.trim()
  if (!name) return
  try {
    await request.post(`/api/v1/projects/${projectId.value}/dictionary-entry`, {
      name,
      category_type: inlineEntryCat.value
    })
    ElMessage.success(`词条「${name}」已添加`)
    showInlineNewEntry.value = false
    inlineEntryName.value = ''
    await fetchAvailableTargets()
    newTarget.name = name
    newTarget.category_type = inlineEntryCat.value as 'white' | 'scene'
  } catch (e: any) { ElMessage.error(e.message) }
}

// 编辑弹窗专用：添加词条后赋值给 editForm
async function submitInlineEntryForEdit() {
  const name = inlineEntryName.value.trim()
  if (!name) return
  try {
    await request.post(`/api/v1/projects/${projectId.value}/dictionary-entry`, {
      name,
      category_type: inlineEntryCat.value
    })
    ElMessage.success(`词条「${name}」已添加`)
    showInlineNewEntry.value = false
    inlineEntryName.value = ''
    await fetchAvailableTargets()
    editForm.name = name
    editForm.category_type = inlineEntryCat.value
  } catch (e: any) { ElMessage.error(e.message) }
}

// 编辑弹窗：选择目标名称时同步 category_type
function onEditTargetNameChange(name: string) {
  const entry = availableTargets.value.find(e => e.name === name)
  if (entry) {
    editForm.category_type = entry.category_type
  }
}

const isArchived = computed(() => !!archivedAt.value)
const cleanupDueAt = computed(() => {
  if (!archivedAt.value) return ''
  const d = new Date(archivedAt.value)
  d.setDate(d.getDate() + 15)
  return d.toISOString()
})

const remainingDaysText = computed(() => {
  if (!projectEstimatedEnd.value) {
    const createdText = projectCreatedAt.value ? formatDate(projectCreatedAt.value) : '—'
    return '创建于 ' + createdText
  }
  const now = new Date()
  const deadline = new Date(projectEstimatedEnd.value)
  const diffTime = deadline.getTime() - now.getTime()
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24))
  if (diffDays < 0) return `已逾期 ${Math.abs(diffDays)} 天`
  if (diffDays === 0) return '今日截止'
  return `剩余 ${diffDays} 天`
})

const statusOrder: Record<string, number> = {
  not_started: 0,
  shooting: 1,
  retouching: 2,
  completed: 3,
}

const whiteTargets = computed(() =>
  targets.value
    .filter(t => t.category_type === 'white')
    .sort((a, b) => (statusOrder[a.target_status] ?? 99) - (statusOrder[b.target_status] ?? 99))
)
const sceneTargets = computed(() =>
  targets.value
    .filter(t => t.category_type === 'scene')
    .sort((a, b) => (statusOrder[a.target_status] ?? 99) - (statusOrder[b.target_status] ?? 99))
)
const groupedTargetSections = computed(() => {
  const sections = [
    ...projectGroups.value.map(g => ({
      key: `group-${g.id}`,
      name: g.name,
      targets: targets.value.filter(t => t.group_id === g.id),
    })),
    {
      key: 'ungrouped',
      name: '未分组',
      targets: targets.value.filter(t => !t.group_id),
    },
  ].filter(section => section.targets.length > 0)
  return sections.map(section => ({
    ...section,
    scene: section.targets.filter(t => t.category_type === 'scene'),
    white: section.targets.filter(t => t.category_type === 'white'),
  }))
})
const progressQuickValue = computed(() => {
  const whiteDone = whiteTargets.value.filter(t => t.target_status === 'completed').length
  const sceneDone = sceneTargets.value.filter(t => t.target_status === 'completed').length
  return `白图 ${whiteDone}/${whiteTargets.value.length} · 场景 ${sceneDone}/${sceneTargets.value.length}`
})
const progressQuickSub = computed(() => {
  const confirmed = targets.value.reduce((sum, t) => sum + (t.confirmed_count || 0), 0)
  const retouched = targets.value.reduce((sum, t) => sum + (t.retouched_count || 0), 0)
  const final = targets.value.reduce((sum, t) => sum + (t.final_count || 0), 0)
  return `原图确认 ${confirmed} · 精修 ${retouched} · 成片 ${final}`
})

// ── 编辑相关 ─────────────────────────────────────────
const showEditTarget = ref(false)
const editing = ref(false)
const editingTargetId = ref<number | null>(null)
const editForm = reactive({
  name: '',
  group_id: null as number | null,
  category_type: 'white' as string,
  requirement_desc: '' as string | null,
  sample_path: null as string | null,
})

const showSamplePicker = ref(false)
const showImagePicker = ref(false)
const samplePickerTarget = ref<'create' | 'edit'>('edit')
const projectPhotos = ref<any[]>([])
const loadingPhotos = ref(false)

function onImagePicked(image: { url: string; id?: number; source: 'system' | 'project' }) {
  if (samplePickerTarget.value === 'create') {
    newTarget.sample_path = image.url
  } else {
    editForm.sample_path = image.url
  }
}

function formatDate(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function getSampleUrl(path: string): string {
  return `${API_BASE}/storage/${path}`
}

function goBack() {
  router.push({ name: 'Dashboard' })
}

function onDrill(targetId: number) {
  activeTargetId.value = targetId
}

function onNavigateToLineage(targetId: number) {
  lineageTargetId.value = targetId
}

function onOpenShuttle(targetId: number) {
  shuttleTargetId.value = targetId
}

async function fetchTargets() {
  if (!projectId.value || projectId.value === 'undefined') {
    console.warn('[ProjectDetail] projectId 无效，跳过目标拉取')
    return
  }

  loading.value = true
  try {
    const [targetsData, projData] = await Promise.all([
      request.get(`/api/v1/projects/${projectId.value}/targets`),
      request.get(`/api/v1/projects/${projectId.value}`),
    ])
    targets.value = targetsData.items
    const totalFinal = targetsData.items.reduce((sum: number, t: any) => sum + (t.final_count || 0), 0)
    finalPhotoCount.value = totalFinal
    if (totalFinal > 0) {
      const withFinal = targetsData.items.filter((t: any) => t.final_count > 0 && t.sample_path)
      deliveryCoverUrl.value = withFinal.length > 0
        ? `/storage/${withFinal[0].sample_path}`
        : null
    }
    archivedAt.value = projData.archived_at ?? null
    projectName.value = projData.name ?? ''
    projectDisplayId.value = projData.display_id ?? ''
    projectCoverImage.value = projData.cover_image ?? null
    projectDescription.value = projData.description ?? null
    projectClientName.value = projData.client_name ?? null
    projectEstimatedEnd.value = projData.estimated_end_time ?? null
    projectCreatedAt.value = projData.created_at ?? null
    totalPhotoCount.value = projData.photo_count ?? 0
  } catch (e: any) {
    console.error('获取目标失败:', e)
  } finally {
    loading.value = false
  }
}

async function fetchGroups() {
  try {
    const data = await request.get(`/api/v1/projects/${projectId.value}/groups`)
    projectGroups.value = data.items || []
  } catch {
    projectGroups.value = []
  }
}

async function createGroup() {
  const name = newGroupName.value.trim()
  if (!name) {
    ElMessage.warning('请输入组合名称')
    return
  }
  savingGroup.value = true
  try {
    await request.post(`/api/v1/projects/${projectId.value}/groups`, {
      name,
      sort_order: projectGroups.value.length,
    })
    newGroupName.value = ''
    ElMessage.success('组合已创建')
    await fetchGroups()
  } catch (e: any) {
    ElMessage.error(e.message || '创建组合失败')
  } finally {
    savingGroup.value = false
  }
}

async function renameGroup(group: ProjectGroup) {
  try {
    const { value } = await ElMessageBox.prompt('请输入新的组合名称', '重命名组合', {
      inputValue: group.name,
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValidator: (value: string) => !!value.trim() || '名称不能为空',
    })
    await request.patch(`/api/v1/projects/${projectId.value}/groups/${group.id}`, {
      name: value.trim(),
    })
    ElMessage.success('组合已更新')
    await fetchGroups()
    await fetchTargets()
  } catch {}
}

async function deleteGroup(group: ProjectGroup) {
  try {
    await ElMessageBox.confirm(
      `删除「${group.name}」后，目标和照片会保留，但会变为未分组。确定继续？`,
      '删除组合',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch { return }
  try {
    await request.delete(`/api/v1/projects/${projectId.value}/groups/${group.id}`)
    ElMessage.success('组合已删除')
    await fetchGroups()
    await fetchTargets()
  } catch (e: any) {
    ElMessage.error(e.message || '删除组合失败')
  }
}

async function createTarget() {
  if (!newTarget.name) {
    ElMessage.warning('请选择目标名称')
    return
  }
  creating.value = true
  try {
    const data = await request.post(`/api/v1/projects/${projectId.value}/targets`, {
      name: newTarget.name.trim(),
      group_id: newTarget.group_id,
      category_type: newTarget.category_type,
      requirement_desc: newTarget.requirement_desc || null,
      sample_path: newTarget.sample_path || null,
      sort_order: targets.value.length,
    })
    targets.value.push(data)
    showCreateTarget.value = false
    newTarget.name = ''
    newTarget.group_id = null
    newTarget.requirement_desc = ''
    newTarget.sample_path = null
    ElMessage.success('目标已创建')
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    creating.value = false
  }
}

// ── 完成 ─────────────────────────────────────────────
async function onComplete(targetId: number) {
  try {
    await request.post(`/api/v1/projects/${projectId.value}/targets/${targetId}/complete`)
    ElMessage.success('已标记为完成')
    await fetchTargets()
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  }
}

// ── 编辑 ─────────────────────────────────────────────
function onEdit(target: TargetItem) {
  editingTargetId.value = target.id
  editForm.name = target.name
  editForm.group_id = target.group_id ?? null
  editForm.category_type = target.category_type
  editForm.requirement_desc = target.requirement_desc || ''
  editForm.sample_path = target.sample_path
  showEditTarget.value = true
}

async function fetchProjectPhotos() {
  loadingPhotos.value = true
  try {
    const data = await request.get(`/api/v1/projects/${projectId.value}/photos`, { skip: '0', limit: '200' })
    projectPhotos.value = data.items.filter((p: any) => p.status !== 'deleted')
  } finally {
    loadingPhotos.value = false
  }
}

function pickSample(photo: any) {
  const path = photo.thumbnail_path || photo.original_path
  if (samplePickerTarget.value === 'create') {
    newTarget.sample_path = path
  } else {
    editForm.sample_path = path
  }
  showSamplePicker.value = false
}

async function ensureProjectPhotos() {
  if (projectPhotos.value.length === 0) {
    await fetchProjectPhotos()
  }
  showSamplePicker.value = true
}

async function submitEdit() {
  if (!editForm.name.trim()) {
    ElMessage.warning('名称不能为空')
    return
  }
  editing.value = true
  try {
    await request.patch(`/api/v1/projects/${projectId.value}/targets/${editingTargetId.value}`, {
      name: editForm.name.trim(),
      group_id: editForm.group_id,
      category_type: editForm.category_type,
      requirement_desc: editForm.requirement_desc || null,
      sample_path: editForm.sample_path,
    })
    showEditTarget.value = false
    ElMessage.success('已更新')
    await fetchTargets()
  } catch (e: any) {
    ElMessage.error(e.message || '更新失败')
  } finally {
    editing.value = false
  }
}

// ── 删除 ─────────────────────────────────────────────
async function onDelete(targetId: number) {
  try {
    await ElMessageBox.confirm(
      '删除后，该目标下的照片将变为未分配状态。确定删除？',
      '删除确认',
      { type: 'warning', confirmButtonText: '确定删除', cancelButtonText: '取消' },
    )
  } catch { return }

  try {
    await request.delete(`/api/v1/projects/${projectId.value}/targets/${targetId}`)
    ElMessage.success('目标已删除')
    await fetchTargets()
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

// ── 手动设置状态 ──────────────────────────────────────
async function onSetStatus(targetId: number, newStatus: string) {
  try {
    await request.patch(`/api/v1/projects/${projectId.value}/targets/${targetId}`, {
      target_status: newStatus
    })
    ElMessage.success('状态已更新')
    await fetchTargets()
  } catch (e: any) {
    ElMessage.error(e.message || '修改失败')
  }
}

// ── 归档 ─────────────────────────────────────────────
async function onToggleArchive() {
  const action = isArchived.value ? 'unarchive' : 'archive'
  const confirmText = isArchived.value
    ? '取消归档后，回收站将不再被定时清理，确定继续？'
    : '归档后，15 天内未恢复的回收站照片将被物理删除，确定继续？'
  try {
    await ElMessageBox.confirm(confirmText, '操作确认', {
      type: 'warning',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
  } catch { return }

  try {
    const data = await request.post(`/api/v1/projects/${projectId.value}/${action}`)
    archivedAt.value = action === 'archive' ? data.archived_at : null
    ElMessage.success(data.message)
  } catch (e: any) {
    ElMessage.error(e.message || '操作失败')
  }
}

function goImport() {
  router.push({ name: 'ImportCenter', params: { id: projectId.value } })
}

onMounted(() => {
  fetchGroups()
  fetchTargets()
})
</script>

<style scoped>
.project-detail {
  padding: 24px 32px;
  min-height: 100%;
}

/* ── 返回按钮 ──────────────────────────────── */
.back-button-wrapper {
  margin-bottom: 16px;
}

/* ── 项目详情头部卡片 ──────────────────────── */
.project-header-card {
  display: flex;
  gap: 24px;
  background: white;
  border-radius: 16px;
  padding: 24px;
  margin-bottom: 24px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  max-height: 280px;
}

.header-cover {
  width: 240px;
  height: 100%;
  min-height: 180px;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
  background: #f5f7fa;
}

.header-cover-img {
  width: 100%;
  height: 100%;
}

.header-cover-img :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.header-cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #d1d5db;
}

.header-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}

/* 标题行 */
.header-title-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.header-title-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.header-project-name {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.header-project-id {
  font-size: 14px;
  color: #6b7280;
  background: #f3f4f6;
  padding: 4px 12px;
  border-radius: 6px;
  font-family: 'Courier New', monospace;
  flex-shrink: 0;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.action-btn {
  transition: all 0.2s ease;
  border-radius: 8px;
}

.action-btn:hover {
  transform: scale(1.05);
}

.action-btn-primary {
  background: #2563eb;
  border-color: #2563eb;
  color: white;
}

.action-btn-primary:hover {
  background: #1d4ed8;
  border-color: #1d4ed8;
}

/* 核心指标栅格 */
.header-metrics {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  padding: 16px 0;
}

.metric-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.metric-label {
  font-size: 12px;
  color: #6b7280;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.metric-sub {
  font-size: 13px;
  color: #9ca3af;
}

/* 项目描述 */
.header-description {
  font-size: 13px;
  color: #6b7280;
  line-height: 1.6;
  padding: 12px 16px;
  background: #f9fafb;
  border-radius: 8px;
  border-left: 3px solid #3b82f6;
}

.archive-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fef0f0;
  border: 1px solid #fbc4c4;
  color: #c45656;
  padding: 12px 16px;
  border-radius: 8px;
  font-size: 14px;
  margin-bottom: 24px;
}

/* ── 看板 ──────────────────────────────────── */
.kanban-container {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

.kanban-section {
  background: #f8f9fb;
  border-radius: 12px;
  padding: 20px 24px;
}

.group-kanban-section {
  border: 1px solid #eef2f7;
}

.kanban-subtitle {
  margin: 12px 0 8px;
  font-size: 13px;
  font-weight: 600;
  color: #606266;
}

.group-manager {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.group-create-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 10px;
}

.group-manager-tip {
  font-size: 12px;
  color: #909399;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #2c3e50;
  margin: 0;
}

.section-count {
  font-size: 13px;
  color: #909399;
  background: #e8e8e8;
  padding: 2px 8px;
  border-radius: 8px;
}

.kanban-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

.empty-hint {
  grid-column: 1 / -1;
  text-align: center;
  padding: 40px;
  color: #c0c4cc;
  font-size: 14px;
}

/* ── 编辑弹窗 ──────────────────────────────── */
.sample-picker {
  display: flex;
  align-items: center;
  gap: 12px;
}

.current-sample {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sample-preview {
  width: 60px;
  height: 60px;
  border-radius: 6px;
  overflow: hidden;
}

.sample-preview :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* ── 样图选择弹窗 ──────────────────────────── */
.sample-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 8px;
  max-height: 400px;
  overflow-y: auto;
}

.sample-option {
  position: relative;
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  border: 2px solid transparent;
  transition: border-color 0.15s;
}

.sample-option:hover {
  border-color: #409eff;
}

.sample-option-img {
  width: 100%;
  height: 100%;
}

.sample-option-img :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.sample-option-id {
  position: absolute;
  bottom: 2px;
  left: 2px;
  font-size: 10px;
  font-weight: 700;
  color: white;
  background: rgba(0,0,0,0.5);
  padding: 1px 4px;
  border-radius: 3px;
}

.thumb-error {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  color: #c0c4cc;
}

/* 最终交付图入口卡片 */
.delivery-entry-card {
  display: flex;
  gap: 20px;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  color: white;
}
.delivery-entry-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(102,126,234,0.4); }
.delivery-cover { width: 80px; height: 60px; border-radius: 8px; overflow: hidden; flex-shrink: 0; background: rgba(255,255,255,0.2); }
.delivery-cover-img { width: 100%; height: 100%; }
.delivery-cover-img :deep(img) { width: 100%; height: 100%; object-fit: cover; }
.delivery-cover-placeholder { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; font-size: 24px; }
.delivery-entry-info { flex: 1; }
.delivery-entry-title { font-size: 18px; font-weight: 700; margin: 0 0 4px; }
.delivery-entry-count { font-size: 13px; opacity: 0.85; }

/* 字典选择器扩展 */
.select-footer-add {
  padding: 8px 12px; cursor: pointer; color: #409eff; font-size: 13px;
  border-top: 1px solid #ebeef5; transition: background .15s;
}
.select-footer-add:hover { background: #f5f7fa; }
.select-footer-form {
  display: flex; align-items: center; gap: 6px; padding: 8px 12px;
  border-top: 1px solid #ebeef5;
}
.inline-entry-input {
  flex: 1; padding: 4px 8px; border: 1px solid #dcdfe6; border-radius: 4px;
  font-size: 13px; outline: none;
}
.inline-entry-input:focus { border-color: #409eff; }
.inline-entry-cat {
  padding: 4px; border: 1px solid #dcdfe6; border-radius: 4px;
  font-size: 12px; background: #fff;
}
.inline-entry-btn {
  padding: 4px 10px; border: none; border-radius: 4px;
  font-size: 12px; cursor: pointer; background: #409eff; color: #fff;
}
.inline-entry-btn:hover { background: #337ecc; }
.inline-entry-cancel { background: #f0f1f3; color: #606266; }
.inline-entry-cancel:hover { background: #e0e1e3; }
</style>
