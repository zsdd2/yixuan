<template>
  <el-dialog
    title="选择 NAS 文件夹"
    v-model="visible"
    width="560px"
    :close-on-click-modal="false"
    @open="browse('.')"
  >
    <!-- 面包屑导航 -->
    <div class="breadcrumb-bar">
      <el-breadcrumb separator="/">
        <el-breadcrumb-item @click="browse('.')">
          <span class="crumb-link">NAS 根目录</span>
        </el-breadcrumb-item>
        <el-breadcrumb-item
          v-for="(seg, idx) in pathSegments"
          :key="idx"
          @click="browse(pathSegments.slice(0, idx + 1).join('/'))"
        >
          <span class="crumb-link">{{ seg }}</span>
        </el-breadcrumb-item>
      </el-breadcrumb>
    </div>

    <!-- 文件夹列表 -->
    <div v-loading="loading" class="folder-list">
      <div
        v-if="parentPath !== null"
        class="folder-item folder-back"
        @dblclick="browse(parentPath!)"
      >
        <el-icon><Back /></el-icon>
        <span>.. 返回上一级</span>
      </div>
      <div
        v-for="folder in folders"
        :key="folder"
        class="folder-item"
        @dblclick="browse(currentPath === '.' ? folder : currentPath + '/' + folder)"
      >
        <el-icon><Folder /></el-icon>
        <span>{{ folder }}</span>
      </div>
      <el-empty v-if="!loading && folders.length === 0 && parentPath === null" description="空目录" :image-size="48" />
    </div>

    <!-- 当前选中路径 -->
    <div class="selected-path">
      <span>当前路径：</span>
      <el-tag type="info">{{ currentPath === '.' ? '/' : '/' + currentPath }}</el-tag>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" @click="confirm">确认选择</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Folder, Back } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  'update:modelValue': [val: boolean]
  'select': [path: string]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const loading = ref(false)
const currentPath = ref('.')
const parentPath = ref<string | null>(null)
const folders = ref<string[]>([])

const pathSegments = computed(() =>
  currentPath.value === '.' ? [] : currentPath.value.split('/')
)

async function browse(path: string) {
  loading.value = true
  try {
    const json = await request.get('/api/v1/system/browse-nas', { path })
    const data = json.data
    currentPath.value = data.current_path
    parentPath.value = data.parent_path
    folders.value = data.folders
  } catch (e: any) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function confirm() {
  emit('select', currentPath.value)
  visible.value = false
}
</script>

<style scoped>
.breadcrumb-bar {
  margin-bottom: 12px;
  padding: 8px 12px;
  background: var(--el-fill-color-lighter);
  border-radius: 6px;
}
.crumb-link {
  cursor: pointer;
  color: var(--el-color-primary);
}
.crumb-link:hover {
  text-decoration: underline;
}
.folder-list {
  min-height: 240px;
  max-height: 360px;
  overflow-y: auto;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 6px;
  padding: 4px;
}
.folder-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 4px;
  cursor: pointer;
  user-select: none;
}
.folder-item:hover {
  background: var(--el-fill-color-light);
}
.folder-back {
  color: var(--el-text-color-secondary);
}
.selected-path {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
</style>
