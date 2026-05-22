<template>
  <div class="settings-center">
    <div class="page-header">
      <h1 class="page-title">设置中心</h1>
    </div>

    <el-tabs v-model="activeTab" type="border-card">
      <!-- ═══ Tab0: 基础设置 ═══ -->
      <el-tab-pane label="基础设置" name="basic">
        <div class="basic-settings">
          <el-form label-width="120px" style="max-width: 600px;">
            <el-form-item label="外网分享链接">
              <el-input
                v-model="externalShareUrl"
                placeholder="https://example.com"
                clearable
              >
                <template #append>
                  <el-button @click="saveExternalUrl" :loading="savingConfig">保存</el-button>
                </template>
              </el-input>
              <div style="font-size: 12px; color: #909399; margin-top: 4px;">
                配置后，生成的审核分享链接将使用此域名。留空则使用当前域名。
              </div>
            </el-form-item>
          </el-form>
        </div>
      </el-tab-pane>

      <!-- ═══ Tab1: 系统图库 ═══ -->
      <el-tab-pane label="系统图库" name="images">
        <div class="tab-toolbar">
          <el-select v-model="imgCategory" size="default" style="width:140px" @change="fetchImages">
            <el-option label="全部分类" value="" />
            <el-option label="封面图" value="cover" />
            <el-option label="样图" value="sample" />
            <el-option label="头像" value="avatar" />
            <el-option label="其他" value="other" />
          </el-select>
          <el-upload :action="`/api/v1/system/images/upload`" name="file" :data="{ category: uploadCategory }" :show-file-list="false" :on-success="onImgUploaded" accept=".jpg,.jpeg,.png,.webp">
            <el-button type="primary" size="default">上传图片</el-button>
          </el-upload>
          <el-select v-model="uploadCategory" size="default" style="width:120px" placeholder="上传分类">
            <el-option label="封面图" value="cover" />
            <el-option label="样图" value="sample" />
            <el-option label="头像" value="avatar" />
            <el-option label="其他" value="other" />
          </el-select>
          <span class="tab-count">共 {{ sysImages.length }} 张</span>
        </div>
        <div class="img-grid" v-loading="loadingImages">
          <div v-for="img in sysImages" :key="img.id" class="img-card">
            <el-image :src="getStorageUrl(img.thumbnail_path || img.original_path)" fit="cover" lazy class="img-thumb">
              <template #error><div class="img-err">ERR</div></template>
            </el-image>
            <div class="img-info">
              <span class="img-name">{{ img.name }}</span>
              <span class="img-cat">{{ catLabel[img.category] || img.category }}</span>
            </div>
            <el-button class="img-del" type="danger" size="small" text @click.stop="deleteImage(img.id)">删除</el-button>
          </div>
          <el-empty v-if="!loadingImages && sysImages.length === 0" description="暂无图片" :image-size="60" />
        </div>
      </el-tab-pane>

      <!-- ═══ Tab2: 项目模板 ═══ -->
      <el-tab-pane label="项目模板" name="templates">
        <div class="tab-toolbar">
          <el-button type="primary" @click="openCreateTpl">+ 新建模板</el-button>
        </div>
        <el-table :data="templates" v-loading="loadingTpls" stripe border>
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
              <el-button type="danger" link :disabled="row.is_builtin" @click="deleteTpl(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- ═══ Tab3: 用户管理 ═══ -->
      <el-tab-pane label="用户管理" name="users">
        <div class="tab-toolbar">
          <el-button type="primary" @click="openCreateUser">+ 新建用户</el-button>
        </div>
        <el-table :data="users" v-loading="loadingUsers" stripe border>
          <el-table-column type="index" label="#" width="50" />
          <el-table-column prop="username" label="用户名" width="140" />
          <el-table-column prop="display_name" label="显示名" width="140">
            <template #default="{ row }">{{ row.display_name || '—' }}</template>
          </el-table-column>
          <el-table-column prop="role" label="角色" width="100">
            <template #default="{ row }">
              <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">{{ roleLabel[row.role] || row.role }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="is_active" label="状态" width="80" align="center">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'" size="small">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="170">
            <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200" align="center">
            <template #default="{ row }">
              <el-button type="primary" link @click="editUser(row)">编辑</el-button>
              <el-button link @click="editAccess(row)">权限</el-button>
              <el-button type="danger" link @click="deleteUser(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- ═══ 模板编辑弹窗 ═══ -->
    <el-dialog v-model="showTplDialog" :title="tplIsEdit ? '编辑模板' : '新建模板'" width="700px" destroy-on-close>
      <el-form :model="tplForm" label-width="90px">
        <el-form-item label="模板名称"><el-input v-model="tplForm.name" maxlength="64" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="tplForm.description" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <h4 style="margin:12px 0 8px;font-weight:600;">目标列表</h4>
      <div class="tpl-targets">
        <div v-for="(t, i) in tplForm.targets" :key="i" class="tpl-target-row">
          <el-input v-model="t.name" placeholder="目标名称" size="small" style="width:180px" />
          <el-select v-model="t.category_type" size="small" style="width:100px">
            <el-option label="白图" value="white" /><el-option label="场景" value="scene" />
          </el-select>
          <el-input v-model="t.requirement_desc" placeholder="要求描述" size="small" style="flex:1" />
          <el-button size="small" type="danger" text @click="tplForm.targets.splice(i, 1)">删除</el-button>
        </div>
        <el-button size="small" @click="tplForm.targets.push({ name: '', category_type: 'white', requirement_desc: '', sort_order: tplForm.targets.length })">+ 添加目标</el-button>
      </div>
      <template #footer>
        <el-button @click="showTplDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingTpl" @click="submitTpl">保存</el-button>
      </template>
    </el-dialog>

    <!-- ═══ 用户编辑弹窗 ═══ -->
    <el-dialog v-model="showUserDialog" :title="userIsEdit ? '编辑用户' : '新建用户'" width="450px" destroy-on-close>
      <el-form :model="userForm" label-width="90px">
        <el-form-item label="用户名"><el-input v-model="userForm.username" :disabled="userIsEdit" maxlength="64" /></el-form-item>
        <el-form-item label="显示名"><el-input v-model="userForm.display_name" placeholder="选填" maxlength="64" /></el-form-item>
        <el-form-item label="密码">
          <el-input v-model="userForm.password" type="password" placeholder="暂未启用认证" />
          <div style="font-size:11px;color:#909399;margin-top:2px;">⚠️ 密码功能暂未启用，仅存储</div>
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="userForm.role" style="width:100%">
            <el-option label="员工" value="staff" /><el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUserDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingUser" @click="submitUser">保存</el-button>
      </template>
    </el-dialog>

    <!-- ═══ 权限弹窗 ═══ -->
    <el-dialog v-model="showAccessDialog" title="项目权限设置" width="600px" destroy-on-close>
      <p style="font-size:13px;color:#606266;margin-bottom:12px;">
        为用户 <b>{{ accessUser?.username }}</b> 设置可见项目。空 = 可看所有项目。
      </p>
      <div style="margin-bottom:8px;">
        <span style="font-size:12px;color:#909399;">按客户筛选：</span>
        <el-select v-model="accessClientFilter" size="small" clearable placeholder="全部客户" style="width:200px" @change="filterAccessProjects">
          <el-option v-for="c in accessClients" :key="c.id" :label="c.name" :value="c.id" />
        </el-select>
      </div>
      <el-checkbox-group v-model="accessProjectIds">
        <div v-for="p in filteredAccessProjects" :key="p.id" style="padding:4px 0;">
          <el-checkbox :value="p.id">{{ p.name }} ({{ p.display_id }})</el-checkbox>
        </div>
      </el-checkbox-group>
      <el-empty v-if="filteredAccessProjects.length === 0" description="无项目" :image-size="40" />
      <template #footer>
        <el-button @click="showAccessDialog = false">取消</el-button>
        <el-button @click="accessProjectIds = []">清空（可看全部）</el-button>
        <el-button type="primary" :loading="savingAccess" @click="submitAccess">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'

const API_BASE = ''
const activeTab = ref('basic')

const catLabel: Record<string, string> = { cover: '封面图', sample: '样图', avatar: '头像', other: '其他' }
const roleLabel: Record<string, string> = { staff: '员工', admin: '管理员', client: '客户' }

function getStorageUrl(path: string): string {
  return `${API_BASE}/storage/${path}`
}
function fmtDate(iso: string): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

// ═══ 基础设置 ═══
const externalShareUrl = ref('')
const savingConfig = ref(false)

async function loadExternalUrl() {
  try {
    const result = await request.get('/api/v1/system/configs/external_share_url', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
    if (result.code === 200 && result.data) {
      externalShareUrl.value = result.data.config_value || ''
    }
  } catch (e) {
    console.error('加载外网链接配置失败:', e)
  }
}

async function saveExternalUrl() {
  savingConfig.value = true
  try {
    const result = await request.put('/api/v1/system/configs/external_share_url', {
      config_value: externalShareUrl.value || ''
    }, {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    })
    if (result.code === 200) {
      ElMessage.success('保存成功')
    } else {
      ElMessage.error(result.msg || '保存失败')
    }
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    savingConfig.value = false
  }
}

// ═══ 系统图库 ═══
const sysImages = ref<any[]>([])
const loadingImages = ref(false)
const imgCategory = ref('')
const uploadCategory = ref('sample')

async function fetchImages() {
  loadingImages.value = true
  try {
    const q = imgCategory.value ? `?category=${imgCategory.value}` : ''
    const d = await request.get(`/api/v1/system/images${q}`)
    sysImages.value = d.items
  } catch {} finally { loadingImages.value = false }
}
function onImgUploaded() { ElMessage.success('图片已上传'); fetchImages() }
async function deleteImage(id: number) {
  try { await ElMessageBox.confirm('删除此图片？', '确认', { type: 'warning' }) } catch { return }
  await request.delete(`/api/v1/system/images/${id}`); fetchImages()
}

// ═══ 模板 ═══
const templates = ref<any[]>([])
const loadingTpls = ref(false)
const showTplDialog = ref(false)
const tplIsEdit = ref(false)
const tplEditId = ref<number | null>(null)
const savingTpl = ref(false)
const tplForm = reactive({ name: '', description: '', targets: [] as any[] })

async function fetchTemplates() {
  loadingTpls.value = true
  try {
    const d = await request.get('/api/v1/settings/templates')
    templates.value = d.items
  } catch {} finally { loadingTpls.value = false }
}
function openCreateTpl() {
  tplIsEdit.value = false; tplEditId.value = null
  tplForm.name = ''; tplForm.description = ''; tplForm.targets = []
  showTplDialog.value = true
}
async function editTpl(row: any) {
  tplIsEdit.value = true; tplEditId.value = row.id
  const d = await request.get(`/api/v1/settings/templates/${row.id}`)
  tplForm.name = d.name; tplForm.description = d.description || ''
  tplForm.targets = d.targets.map((t: any) => ({
    id: t.id, name: t.name, category_type: t.category_type,
    requirement_desc: t.requirement_desc || '', sort_order: t.sort_order,
  }))
  showTplDialog.value = true
}
async function submitTpl() {
  if (!tplForm.name.trim()) { ElMessage.warning('请输入模板名称'); return }
  savingTpl.value = true
  try {
    if (tplIsEdit.value) {
      await request.patch(`/api/v1/settings/templates/${tplEditId.value}`, {
        name: tplForm.name,
        description: tplForm.description || null
      })
      // sync targets: delete removed, add new
      const detail = await request.get(`/api/v1/settings/templates/${tplEditId.value}`)
      const existingIds = new Set(tplForm.targets.filter((t: any) => t.id).map((t: any) => t.id))
      for (const old of detail.targets) {
        if (!existingIds.has(old.id)) {
          await request.delete(`/api/v1/settings/templates/${tplEditId.value}/targets/${old.id}`)
        }
      }
      for (const t of tplForm.targets) {
        if (!t.id) {
          await request.post(`/api/v1/settings/templates/${tplEditId.value}/targets`, {
            name: t.name,
            category_type: t.category_type,
            requirement_desc: t.requirement_desc || null,
            sort_order: t.sort_order
          })
        }
      }
      ElMessage.success('模板已更新')
    } else {
      await request.post('/api/v1/settings/templates', {
        name: tplForm.name,
        description: tplForm.description || null,
        targets: tplForm.targets
      })
      ElMessage.success('模板已创建')
    }
    showTplDialog.value = false; await fetchTemplates()
  } catch (e: any) { ElMessage.error(e.message) }
  finally { savingTpl.value = false }
}
async function deleteTpl(row: any) {
  try { await ElMessageBox.confirm(`删除模板「${row.name}」？`, '确认', { type: 'warning' }) } catch { return }
  await request.delete(`/api/v1/settings/templates/${row.id}`); fetchTemplates()
}

// ═══ 用户 ═══
const users = ref<any[]>([])
const loadingUsers = ref(false)
const showUserDialog = ref(false)
const userIsEdit = ref(false)
const userEditId = ref<number | null>(null)
const savingUser = ref(false)
const userForm = reactive({ username: '', display_name: '', password: '', role: 'staff' })

async function fetchUsers() {
  loadingUsers.value = true
  try {
    const d = await request.get('/api/v1/system/users')
    users.value = d.items
  } catch {} finally { loadingUsers.value = false }
}
function openCreateUser() {
  userIsEdit.value = false; userEditId.value = null
  Object.assign(userForm, { username: '', display_name: '', password: '', role: 'staff' })
  showUserDialog.value = true
}
function editUser(row: any) {
  userIsEdit.value = true; userEditId.value = row.id
  Object.assign(userForm, { username: row.username, display_name: row.display_name || '', password: '', role: row.role })
  showUserDialog.value = true
}
async function submitUser() {
  if (!userForm.username.trim()) { ElMessage.warning('请输入用户名'); return }
  savingUser.value = true
  try {
    if (userIsEdit.value) {
      const body: any = { display_name: userForm.display_name || null, role: userForm.role }
      if (userForm.password) body.password = userForm.password
      await request.patch(`/api/v1/system/users/${userEditId.value}`, body)
      ElMessage.success('用户已更新')
    } else {
      await request.post('/api/v1/system/users', {
        username: userForm.username,
        display_name: userForm.display_name || null,
        password: userForm.password || null,
        role: userForm.role
      })
      ElMessage.success('用户已创建')
    }
    showUserDialog.value = false; await fetchUsers()
  } catch (e: any) { ElMessage.error(e.message) }
  finally { savingUser.value = false }
}
async function deleteUser(row: any) {
  try { await ElMessageBox.confirm(`删除用户「${row.username}」？`, '确认', { type: 'warning' }) } catch { return }
  await request.delete(`/api/v1/system/users/${row.id}`); fetchUsers()
}

// ═══ 权限 ═══
const showAccessDialog = ref(false)
const accessUser = ref<any>(null)
const accessProjectIds = ref<number[]>([])
const savingAccess = ref(false)
const accessClients = ref<any[]>([])
const allAccessProjects = ref<any[]>([])
const accessClientFilter = ref<number | null>(null)

const filteredAccessProjects = computed(() => {
  if (!accessClientFilter.value) return allAccessProjects.value
  return allAccessProjects.value.filter(p => p.client_id === accessClientFilter.value)
})
function filterAccessProjects() {}

async function editAccess(row: any) {
  accessUser.value = row
  const [aRes, pRes, cRes] = await Promise.all([
    request.get(`/api/v1/system/users/${row.id}/access`),
    request.get('/api/v1/projects?limit=100&include_completed=true'),
    request.get('/api/v1/clients'),
  ])
  accessProjectIds.value = aRes.project_ids
  allAccessProjects.value = pRes.items
  accessClients.value = cRes.items
  accessClientFilter.value = null
  showAccessDialog.value = true
}
async function submitAccess() {
  savingAccess.value = true
  try {
    await request.put(`/api/v1/system/users/${accessUser.value.id}/access`, {
      project_ids: accessProjectIds.value
    })
    ElMessage.success('权限已保存')
    showAccessDialog.value = false
  } catch { ElMessage.error('保存失败') }
  finally { savingAccess.value = false }
}

// ═══ Init ═══
watch(activeTab, (tab) => {
  if (tab === 'basic') loadExternalUrl()
  else if (tab === 'images') fetchImages()
  else if (tab === 'templates') fetchTemplates()
  else if (tab === 'users') fetchUsers()
})
onMounted(() => loadExternalUrl())
</script>

<style scoped>
.settings-center { padding: 20px 28px; min-height: 100%; }
.page-header { margin-bottom: 16px; }
.page-title { font-size: 24px; font-weight: 700; color: #2c3e50; }
.tab-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.tab-count { font-size: 13px; color: #909399; }

.basic-settings { padding: 20px 0; }

.img-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
.img-card { position: relative; border-radius: 10px; overflow: hidden; border: 1px solid #ebeef5; background: white; }
.img-thumb { width: 100%; aspect-ratio: 1; display: block; }
.img-thumb :deep(img) { width: 100%; height: 100%; object-fit: cover; }
.img-err { width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; background: #f5f7fa; color: #c0c4cc; font-size: 12px; }
.img-info { padding: 6px 8px; }
.img-name { font-size: 12px; color: #2c3e50; display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.img-cat { font-size: 10px; color: #909399; }
.img-del { position: absolute; top: 4px; right: 4px; background: rgba(255,255,255,0.9); border-radius: 4px; }

.tpl-targets { display: flex; flex-direction: column; gap: 8px; }
.tpl-target-row { display: flex; align-items: center; gap: 8px; }
</style>
