<template>
  <div class="settings-templates">
    <div class="page-header">
      <h1 class="page-title">项目模板</h1>
    </div>

    <!-- 通用目标词条管理 -->
    <div class="dict-section">
      <div class="dict-header">
        <span class="dict-title">通用目标词条</span>
        <span class="dict-hint">系统级名称规范，适用于所有模板</span>
      </div>
      <div class="dict-tags">
        <span
          v-for="entry in globalDict"
          :key="entry.id"
          class="dict-tag"
          :class="{ 'dict-tag-system': entry.is_system }"
        >
          {{ entry.name }}
          <span class="dict-tag-cat">{{ entry.category_type === 'white' ? '白' : '景' }}</span>
          <span v-if="!entry.is_system" class="dict-tag-close" @click="removeGlobalEntry(entry)">×</span>
        </span>
        <span v-if="showGlobalInput" class="dict-input-wrap">
          <input
            ref="globalInputRef"
            v-model="globalInputVal"
            class="dict-input"
            placeholder="输入名称，回车添加"
            @keydown.enter="addGlobalEntry"
            @blur="showGlobalInput = false"
          />
          <select v-model="globalInputCat" class="dict-cat-select">
            <option value="white">白图</option>
            <option value="scene">场景</option>
          </select>
        </span>
        <span v-else class="dict-tag dict-tag-add" @click="startGlobalInput">+ 添加</span>
      </div>
    </div>

    <div class="action-bar">
      <el-button type="primary" @click="openCreate">+ 新建模板</el-button>
    </div>

    <el-table :data="templates" v-loading="loading" stripe style="width:100%">
      <el-table-column type="index" label="#" width="50" />
      <el-table-column prop="name" label="模板名称" min-width="150">
        <template #default="{ row }">
          {{ row.name }}
          <el-tag v-if="row.is_builtin" size="small" type="info" style="margin-left:6px">内置</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.description || '—' }}</template>
      </el-table-column>
      <el-table-column prop="target_count" label="目标数" width="90" align="center" />
      <el-table-column prop="created_at" label="创建时间" width="170">
        <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="center">
        <template #default="{ row }">
          <el-button type="primary" link @click="editTpl(row)">编辑</el-button>
          <el-button type="danger" link @click="deleteTpl(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 模板编辑弹窗 -->
    <el-dialog v-model="showDialog" :title="isEdit ? '编辑模板' : '新建模板'" width="780px" destroy-on-close>
      <el-form :model="form" label-width="90px">
        <el-form-item label="模板名称"><el-input v-model="form.name" maxlength="64" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>

      <!-- 模板专属字典 -->
      <h4 style="margin:16px 0 8px;font-weight:600;">可用目标字典 <span style="font-weight:400;font-size:12px;color:#909399;">（模板专属词条）</span></h4>
      <div class="dict-tags">
        <span
          v-for="(d, i) in form.target_dictionary"
          :key="i"
          class="dict-tag"
        >
          {{ d.name }}
          <span class="dict-tag-cat">{{ d.category_type === 'white' ? '白' : '景' }}</span>
          <span class="dict-tag-close" @click="form.target_dictionary.splice(i, 1)">×</span>
        </span>
        <span v-if="showTplDictInput" class="dict-input-wrap">
          <input
            ref="tplDictInputRef"
            v-model="tplDictInputVal"
            class="dict-input"
            placeholder="输入名称，回车添加"
            @keydown.enter="addTplDictEntry"
            @blur="showTplDictInput = false"
          />
          <select v-model="tplDictInputCat" class="dict-cat-select">
            <option value="white">白图</option>
            <option value="scene">场景</option>
          </select>
        </span>
        <span v-else class="dict-tag dict-tag-add" @click="startTplDictInput">+ 添加</span>
      </div>

      <h4 style="margin:16px 0 8px;font-weight:600;">目标列表</h4>
      <div class="tpl-targets">
        <div v-for="(t, i) in form.targets" :key="i" class="tpl-target-row">
          <el-select v-model="t.name" filterable placeholder="搜索目标名称" size="small" style="width:180px" @change="(v: string) => onTplTargetNameChange(i, v)">
            <el-option v-for="opt in allTargetNameOptions" :key="opt.name" :label="opt.name" :value="opt.name">
              <span>{{ opt.name }}</span>
              <span style="float:right;font-size:11px;color:#909399">{{ opt.category_type === 'white' ? '白图' : '场景' }}</span>
            </el-option>
          </el-select>
          <el-select v-model="t.category_type" size="small" style="width:90px">
            <el-option label="白图" value="white" /><el-option label="场景" value="scene" />
          </el-select>
          <div class="sample-picker" @click="openImagePicker(i)">
            <img v-if="t.sample_thumbnail" :src="getStorageUrl(t.sample_thumbnail)" class="sample-thumb" />
            <span v-else class="sample-placeholder">选择样图</span>
          </div>
          <el-input v-model="t.requirement_desc" placeholder="要求描述" size="small" style="flex:1" />
          <el-button size="small" type="danger" text @click="form.targets.splice(i, 1)">删除</el-button>
        </div>
        <el-button size="small" @click="form.targets.push({ name: '', category_type: 'white', requirement_desc: '', sort_order: form.targets.length, sample_image_id: null, sample_thumbnail: null })">+ 添加目标</el-button>
      </div>
      <template #footer>
        <el-button @click="showDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitTpl">保存</el-button>
      </template>
    </el-dialog>

    <!-- ImagePicker -->
    <ImagePicker v-model:visible="showImagePicker" category="sample" @confirm="onImagePicked" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import ImagePicker from '../components/ImagePicker.vue'
import request from '../api/request'

const templates = ref<any[]>([])
const loading = ref(false)
const showDialog = ref(false)
const isEdit = ref(false)
const editId = ref<number | null>(null)
const saving = ref(false)
const form = reactive({
  name: '', description: '',
  targets: [] as any[],
  target_dictionary: [] as { name: string; category_type: string }[],
})

const showImagePicker = ref(false)
const pickerTargetIndex = ref(-1)

// ── 通用字典 ──
const globalDict = ref<any[]>([])
const showGlobalInput = ref(false)
const globalInputVal = ref('')
const globalInputCat = ref('white')
const globalInputRef = ref<HTMLInputElement>()

async function fetchGlobalDict() {
  try {
    const d = await request.get('/api/v1/settings/target-dictionary')
    globalDict.value = d.items
  } catch {}
}

function startGlobalInput() {
  showGlobalInput.value = true; globalInputVal.value = ''
  nextTick(() => globalInputRef.value?.focus())
}

async function addGlobalEntry() {
  const name = globalInputVal.value.trim()
  if (!name) return
  try {
    await request.post('/api/v1/settings/target-dictionary', {
      name,
      category_type: globalInputCat.value
    })
    ElMessage.success(`词条「${name}」已添加`)
    globalInputVal.value = ''; showGlobalInput.value = false
    await fetchGlobalDict()
  } catch (e: any) { ElMessage.error(e.message) }
}

async function removeGlobalEntry(entry: any) {
  try { await ElMessageBox.confirm(`删除通用词条「${entry.name}」？`, '确认', { type: 'warning' }) } catch { return }
  await request.delete(`/api/v1/settings/target-dictionary/${entry.id}`)
  await fetchGlobalDict()
}

// ── 模板专属字典输入 ──
const showTplDictInput = ref(false)
const tplDictInputVal = ref('')
const tplDictInputCat = ref('white')
const tplDictInputRef = ref<HTMLInputElement>()

function startTplDictInput() {
  showTplDictInput.value = true; tplDictInputVal.value = ''
  nextTick(() => tplDictInputRef.value?.focus())
}

function addTplDictEntry() {
  const name = tplDictInputVal.value.trim()
  if (!name) return
  if (form.target_dictionary.some(d => d.name === name)) {
    ElMessage.warning('该词条已存在'); return
  }
  form.target_dictionary.push({ name, category_type: tplDictInputCat.value })
  tplDictInputVal.value = ''; showTplDictInput.value = false
}

// ── 目标名称选项池（通用词条 + 模板专属合并） ──
const allTargetNameOptions = computed(() => {
  const seen = new Set<string>()
  const options: { name: string; category_type: string }[] = []
  for (const e of globalDict.value) {
    if (!seen.has(e.name)) { options.push({ name: e.name, category_type: e.category_type }); seen.add(e.name) }
  }
  for (const d of form.target_dictionary) {
    if (!seen.has(d.name)) { options.push({ name: d.name, category_type: d.category_type }); seen.add(d.name) }
  }
  return options
})

function onTplTargetNameChange(index: number, name: string) {
  const entry = allTargetNameOptions.value.find(o => o.name === name)
  if (entry) form.targets[index].category_type = entry.category_type
}

// ── 通用逻辑 ──
function getStorageUrl(path: string): string {
  return `/storage/${path}`
}

function fmtDate(iso: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

async function fetchTemplates() {
  loading.value = true
  try {
    const d = await request.get('/api/v1/settings/templates')
    templates.value = d.items
  } catch {} finally { loading.value = false }
}

function openCreate() {
  isEdit.value = false; editId.value = null
  form.name = ''; form.description = ''; form.targets = []; form.target_dictionary = []
  showDialog.value = true
}

async function editTpl(row: any) {
  isEdit.value = true; editId.value = row.id
  const d = await request.get(`/api/v1/settings/templates/${row.id}`)
  form.name = d.name; form.description = d.description || ''
  form.targets = d.targets.map((t: any) => ({
    id: t.id, name: t.name, category_type: t.category_type,
    requirement_desc: t.requirement_desc || '', sort_order: t.sort_order,
    sample_image_id: t.sample_image_id, sample_thumbnail: t.sample_thumbnail,
  }))
  form.target_dictionary = (d.target_dictionary || []).map((d: any) => ({
    name: d.name, category_type: d.category_type || 'white',
  }))
  showDialog.value = true
}

function openImagePicker(index: number) {
  pickerTargetIndex.value = index
  showImagePicker.value = true
}

function onImagePicked(image: { url: string; id?: number }) {
  if (pickerTargetIndex.value >= 0 && pickerTargetIndex.value < form.targets.length) {
    form.targets[pickerTargetIndex.value].sample_image_id = image.id || null
    form.targets[pickerTargetIndex.value].sample_thumbnail = image.url
  }
}

async function submitTpl() {
  if (!form.name.trim()) { ElMessage.warning('请输入模板名称'); return }
  saving.value = true
  try {
    if (isEdit.value) {
      await request.patch(`/api/v1/settings/templates/${editId.value}`, {
        name: form.name,
        description: form.description || null,
        target_dictionary: form.target_dictionary,
      })
      const detail = await request.get(`/api/v1/settings/templates/${editId.value}`)
      const existingIds = new Set(form.targets.filter((t: any) => t.id).map((t: any) => t.id))
      for (const old of detail.targets) {
        if (!existingIds.has(old.id)) {
          await request.delete(`/api/v1/settings/templates/${editId.value}/targets/${old.id}`)
        }
      }
      for (const t of form.targets) {
        if (!t.id) {
          await request.post(`/api/v1/settings/templates/${editId.value}/targets`, {
            name: t.name,
            category_type: t.category_type,
            sample_image_id: t.sample_image_id || null,
            requirement_desc: t.requirement_desc || null,
            sort_order: t.sort_order
          })
        }
      }
      ElMessage.success('模板已更新')
    } else {
      const targets = form.targets.map(t => ({
        name: t.name, category_type: t.category_type,
        sample_image_id: t.sample_image_id || null,
        requirement_desc: t.requirement_desc || null, sort_order: t.sort_order,
      }))
      await request.post('/api/v1/settings/templates', {
        name: form.name,
        description: form.description || null,
        targets,
        target_dictionary: form.target_dictionary,
      })
      ElMessage.success('模板已创建')
    }
    showDialog.value = false; await fetchTemplates()
  } catch (e: any) { ElMessage.error(e.message) }
  finally { saving.value = false }
}

async function deleteTpl(row: any) {
  try { await ElMessageBox.confirm(`删除模板「${row.name}」？`, '确认', { type: 'warning' }) } catch { return }
  await request.delete(`/api/v1/settings/templates/${row.id}`); fetchTemplates()
}

onMounted(() => { fetchTemplates(); fetchGlobalDict() })
</script>

<style scoped>
.settings-templates { padding: 20px 28px; min-height: 100%; }
.page-header { margin-bottom: 16px; }
.page-title { font-size: 24px; font-weight: 700; color: #2c3e50; }
.action-bar { margin-bottom: 14px; }
.tpl-targets { display: flex; flex-direction: column; gap: 8px; }
.tpl-target-row { display: flex; align-items: center; gap: 8px; }
.sample-picker {
  width: 48px; height: 48px; border: 1px dashed #dcdfe6; border-radius: 4px;
  display: flex; align-items: center; justify-content: center; cursor: pointer;
  overflow: hidden; flex-shrink: 0;
}
.sample-picker:hover { border-color: #409eff; }
.sample-thumb { width: 100%; height: 100%; object-fit: cover; }
.sample-placeholder { font-size: 10px; color: #c0c4cc; text-align: center; line-height: 1.2; }

/* 字典区域 */
.dict-section { background: #fafafa; border-radius: 8px; padding: 16px 20px; margin-bottom: 16px; }
.dict-header { display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px; }
.dict-title { font-size: 14px; font-weight: 600; color: #303133; }
.dict-hint { font-size: 12px; color: #909399; }
.dict-tags { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.dict-tag {
  display: inline-flex; align-items: center; gap: 4px;
  padding: 4px 10px; background: #f0f1f3; border-radius: 4px;
  font-size: 13px; color: #606266; line-height: 1.4;
}
.dict-tag-system { background: #eef3ff; color: #4080ff; }
.dict-tag-cat { font-size: 10px; color: #909399; margin-left: 2px; }
.dict-tag-close {
  cursor: pointer; margin-left: 2px; font-size: 14px; color: #c0c4cc;
  line-height: 1; transition: color .15s;
}
.dict-tag-close:hover { color: #f56c6c; }
.dict-tag-add {
  cursor: pointer; color: #909399; border: 1px dashed #dcdfe6; background: transparent;
}
.dict-tag-add:hover { color: #409eff; border-color: #409eff; }
.dict-input-wrap { display: inline-flex; align-items: center; gap: 4px; }
.dict-input {
  width: 120px; padding: 3px 8px; border: 1px solid #dcdfe6; border-radius: 4px;
  font-size: 13px; outline: none; background: #fff;
}
.dict-input:focus { border-color: #409eff; }
.dict-cat-select {
  padding: 3px 4px; border: 1px solid #dcdfe6; border-radius: 4px;
  font-size: 12px; background: #fff; outline: none;
}
</style>
