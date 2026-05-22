<template>
  <div class="settings-basic">
    <div class="page-header">
      <h1 class="page-title">基础设置</h1>
    </div>

    <div class="settings-content">
      <el-form label-width="140px" style="max-width: 700px;">
        <el-form-item label="机构名称">
          <el-input
            v-model="studioName"
            placeholder="请输入工作室/机构名称"
            clearable
          >
            <template #append>
              <el-button @click="saveStudioName" :loading="savingStudioName">保存</el-button>
            </template>
          </el-input>
          <div style="font-size: 12px; color: #909399; margin-top: 8px;">
            用于客户交付 ZIP 文件命名，格式：{机构名称}_{项目名称}_{归档日期}.zip
          </div>
        </el-form-item>

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
          <div style="font-size: 12px; color: #909399; margin-top: 8px;">
            配置后，生成的审核分享链接将使用此域名。留空则使用当前域名。
          </div>
        </el-form-item>

        <el-form-item label="素材分类">
          <div class="material-config">
            <div v-for="(cat, idx) in materialCategories" :key="idx" class="material-cat-row">
              <el-input v-model="cat.name" placeholder="一级分类" style="width: 140px" />
              <el-select v-model="cat.children" multiple filterable allow-create default-first-option placeholder="二级分类" style="flex: 1">
                <el-option v-for="item in cat.children" :key="item" :label="item" :value="item" />
              </el-select>
              <el-button text type="danger" @click="materialCategories.splice(idx, 1)">删除</el-button>
            </div>
            <div class="material-config-actions">
              <el-button @click="materialCategories.push({ name: '', children: [] })">新增一级分类</el-button>
              <el-button type="primary" :loading="savingMaterialCategories" @click="saveMaterialCategories">保存素材分类</el-button>
            </div>
          </div>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'

const studioName = ref('')
const savingStudioName = ref(false)
const externalShareUrl = ref('')
const savingConfig = ref(false)
const savingMaterialCategories = ref(false)
const materialCategories = ref<{ name: string; children: string[] }[]>([
  { name: '场景', children: ['庄园', '海边', '泳池', '庭院'] },
  { name: '饮料', children: ['红酒杯', '柠檬水'] },
])

onMounted(() => {
  loadStudioName()
  loadExternalUrl()
  loadMaterialCategories()
})

async function loadStudioName() {
  try {
    const result = await request.get('/api/v1/system/configs/studio_name', {
      headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
    })
    if (result.code === 200 && result.data) {
      studioName.value = result.data.config_value || ''
    }
  } catch (e) {
    console.error('加载机构名称配置失败:', e)
  }
}

async function saveStudioName() {
  savingStudioName.value = true
  try {
    const result = await request.put('/api/v1/system/configs/studio_name', {
      config_value: studioName.value || ''
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
    savingStudioName.value = false
  }
}

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

async function loadMaterialCategories() {
  try {
    const result = await request.get('/api/v1/system/configs/material_categories')
    if (result.code === 200 && result.data?.config_value) {
      materialCategories.value = JSON.parse(result.data.config_value)
    }
  } catch (e) {
    console.error('加载素材分类失败:', e)
  }
}

async function saveMaterialCategories() {
  savingMaterialCategories.value = true
  try {
    const clean = materialCategories.value
      .map(cat => ({ name: cat.name.trim(), children: cat.children.filter(Boolean) }))
      .filter(cat => cat.name)
    const result = await request.put('/api/v1/system/configs/material_categories', {
      config_value: JSON.stringify(clean),
    })
    if (result.code === 200) {
      materialCategories.value = clean
      ElMessage.success('素材分类已保存')
    } else {
      ElMessage.error(result.msg || '保存失败')
    }
  } catch {
    ElMessage.error('保存失败')
  } finally {
    savingMaterialCategories.value = false
  }
}
</script>

<style scoped>
.settings-basic {
  padding: 20px 28px;
  min-height: 100%;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: #2c3e50;
}

.settings-content {
  background: white;
  border-radius: 8px;
  padding: 32px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.material-config {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.material-cat-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.material-config-actions {
  display: flex;
  gap: 8px;
}
</style>
