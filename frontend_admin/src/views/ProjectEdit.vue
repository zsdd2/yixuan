<template>
  <div class="project-edit-page">
    <div class="edit-shell">
      <div class="edit-header">
        <el-button @click="goBack">返回</el-button>
        <div>
          <h1>编辑项目</h1>
          <p>{{ projectDisplayId || '-' }}</p>
        </div>
      </div>

      <el-card v-loading="loading" class="edit-card" shadow="never">
        <el-form label-width="92px">
          <el-form-item label="项目名称">
            <el-input v-model="form.name" maxlength="128" show-word-limit />
          </el-form-item>
          <el-form-item label="产品编码">
            <el-input v-model="form.customer_product_code" maxlength="128" show-word-limit placeholder="客户侧产品编码/货号，可中英文" />
          </el-form-item>
          <el-form-item label="截止时间">
            <el-date-picker v-model="form.estimated_end_time" type="datetime" style="width: 100%" placeholder="选择预估结束时间" />
          </el-form-item>
          <el-form-item label="项目说明">
            <el-input v-model="form.description" type="textarea" :rows="5" maxlength="500" show-word-limit />
          </el-form-item>
        </el-form>

        <div class="edit-actions">
          <el-button @click="goBack">取消</el-button>
          <el-button type="primary" :loading="saving" @click="saveProject">保存</el-button>
        </div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import request from '../api/request'

const route = useRoute()
const router = useRouter()
const projectId = Number(route.params.id)
const loading = ref(false)
const saving = ref(false)
const projectDisplayId = ref('')

const form = reactive({
  name: '',
  customer_product_code: '',
  estimated_end_time: null as string | null,
  description: '',
})

function goBack() {
  router.push(`/project/${projectId}`)
}

async function fetchProject() {
  loading.value = true
  try {
    const data = await request.get(`/api/v1/projects/${projectId}`)
    projectDisplayId.value = data.display_id || ''
    form.name = data.name || ''
    form.customer_product_code = data.customer_product_code || ''
    form.estimated_end_time = data.estimated_end_time || null
    form.description = data.description || ''
  } catch (e: any) {
    ElMessage.error(e.message || '获取项目失败')
  } finally {
    loading.value = false
  }
}

async function saveProject() {
  if (!form.name.trim()) {
    ElMessage.warning('请输入项目名称')
    return
  }
  saving.value = true
  try {
    await request.patch(`/api/v1/projects/${projectId}`, {
      name: form.name.trim(),
      customer_product_code: form.customer_product_code.trim(),
      estimated_end_time: form.estimated_end_time || null,
      description: form.description.trim() || null,
    })
    ElMessage.success('项目已保存')
    goBack()
  } catch (e: any) {
    ElMessage.error(e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(fetchProject)
</script>

<style scoped>
.project-edit-page {
  min-height: 100%;
  padding: 32px;
  background: #f5f7fb;
}

.edit-shell {
  max-width: 760px;
  margin: 0 auto;
}

.edit-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.edit-header h1 {
  margin: 0;
  font-size: 24px;
  color: #111827;
}

.edit-header p {
  margin: 4px 0 0;
  color: #6b7280;
  font-size: 13px;
}

.edit-card {
  border-radius: 10px;
}

.edit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
