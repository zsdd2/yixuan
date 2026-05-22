<template>
  <el-dialog :model-value="visible" @update:model-value="$emit('update:visible', $event)" title="选择图片" width="720px" destroy-on-close>
    <div class="picker-layout">
      <!-- 左侧分类 -->
      <div class="picker-sidebar">
        <div
          v-for="cat in allCategories"
          :key="cat.value"
          class="picker-cat"
          :class="{ active: activeCat === cat.value }"
          @click="activeCat = cat.value; fetchCatImages()"
        >
          <span>{{ cat.icon }} {{ cat.label }}</span>
        </div>
        <div v-if="projectId" class="picker-cat" :class="{ active: activeCat === '_project' }" @click="activeCat = '_project'; fetchProjectPhotos()">
          <span>📋 项目图片</span>
        </div>
      </div>

      <!-- 右侧内容 -->
      <div class="picker-main">
        <!-- 工具栏 -->
        <div class="picker-toolbar">
          <input
            v-model="searchQuery"
            class="picker-search"
            placeholder="搜索名称 / 标签"
            @input="onSearchDebounced"
          />
          <el-upload
            v-if="activeCat === '_project' && projectId"
            :action="`/api/v1/projects/${projectId}/photos/upload`"
            name="file"
            :show-file-list="false"
            :on-success="onUploaded"
            :on-error="() => {}"
            :before-upload="beforeUpload"
            accept=".jpg,.jpeg,.png,.webp"
          >
            <el-button size="small" type="primary" plain>上传图片</el-button>
          </el-upload>
          <span class="picker-count">{{ filteredList.length }} 张</span>
        </div>

        <!-- 图片网格 -->
        <div class="picker-grid-wrap" v-loading="loading">
          <div class="picker-grid">
            <div
              v-for="img in filteredList"
              :key="`${img.source}-${img.id}`"
              class="picker-item"
              :class="{ selected: selectedImage?.id === img.id && selectedImage?.source === img.source }"
              @click="selectedImage = img"
            >
              <img :src="img.thumbUrl" class="picker-thumb" />
              <span v-if="img.name" class="picker-label" :title="img.name">{{ img.name }}</span>
            </div>
          </div>
          <el-empty v-if="!loading && filteredList.length === 0" description="暂无图片" :image-size="50" />
        </div>
      </div>
    </div>

    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button type="primary" :disabled="!selectedImage" @click="confirmSelect">确认选择</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'

interface PickedImage {
  id: number
  url: string
  thumbUrl: string
  source: 'system' | 'project'
  name?: string
  tags?: string
}

const props = defineProps<{
  visible: boolean
  category?: string
  projectId?: number
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  confirm: [image: { url: string; id?: number; source: 'system' | 'project' }]
}>()

const allCategories = [
  { value: 'cover', label: '封面图', icon: '🖼️' },
  { value: 'sample', label: '样图', icon: '📸' },
  { value: 'avatar', label: '头像', icon: '👤' },
  { value: 'other', label: '其他', icon: '📎' },
]

const activeCat = ref('')
const loading = ref(false)
const imageList = ref<PickedImage[]>([])
const selectedImage = ref<PickedImage | null>(null)
const searchQuery = ref('')
let searchTimer: ReturnType<typeof setTimeout> | null = null

const filteredList = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return imageList.value
  return imageList.value.filter(img =>
    (img.name && img.name.toLowerCase().includes(q)) ||
    (img.tags && img.tags.toLowerCase().includes(q))
  )
})

function onSearchDebounced() {
  // For system images, also re-fetch from server to use server-side search
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    if (activeCat.value !== '_project') fetchCatImages()
  }, 300)
}

function getStorageUrl(path: string): string {
  return `/storage/${path}`
}

function beforeUpload(file: File) {
  const isImage = /\.(jpe?g|png|webp)$/i.test(file.name)
  if (!isImage) {
    ElMessage.warning('仅支持 jpg/png/webp 格式')
    return false
  }
  const isLt10M = file.size / 1024 / 1024 < 10
  if (!isLt10M) {
    ElMessage.warning('图片不能超过 10MB')
    return false
  }
  return true
}

function onUploaded() {
  ElMessage.success('上传成功')
  if (activeCat.value === '_project') {
    fetchProjectPhotos()
  } else {
    fetchCatImages()
  }
}

async function fetchCatImages() {
  loading.value = true
  imageList.value = []
  selectedImage.value = null
  try {
    const params: Record<string, string> = { category: activeCat.value }
    if (searchQuery.value.trim()) params.search = searchQuery.value.trim()
    const d = await request.get('/api/v1/settings/images', params)
    imageList.value = d.items.map((img: any) => ({
      id: img.id,
      url: img.thumbnail_path || img.original_path,
      thumbUrl: getStorageUrl(img.thumbnail_path || img.original_path),
      source: 'system' as const,
      name: img.name,
      tags: img.tags,
    }))
  } catch {} finally { loading.value = false }
}

async function fetchProjectPhotos() {
  if (!props.projectId) return
  loading.value = true
  imageList.value = []
  selectedImage.value = null
  try {
    const items: any[] = []
    let skip = 0
    const limit = 500
    let total = 0
    do {
      const d = await request.get(`/api/v1/projects/${props.projectId}/photos`, {
        skip: String(skip),
        limit: String(limit),
        status: 'pending,selected',
      })
      items.push(...d.items)
      total = d.total
      skip += limit
    } while (skip < total)

    imageList.value = items.map((p: any) => ({
      id: p.id,
      url: p.thumbnail_path || p.original_path,
      thumbUrl: getStorageUrl(p.thumbnail_path || p.original_path),
      source: 'project' as const,
      name: p.original_filename || `#${String(p.display_id).padStart(3, '0')}`,
    }))
  } catch {} finally { loading.value = false }
}

function confirmSelect() {
  if (selectedImage.value) {
    emit('confirm', {
      url: selectedImage.value.url,
      id: selectedImage.value.id,
      source: selectedImage.value.source,
    })
    emit('update:visible', false)
  }
}

watch(() => props.visible, (v) => {
  if (v) {
    activeCat.value = props.category || allCategories[0].value
    selectedImage.value = null
    searchQuery.value = ''
    fetchCatImages()
  }
})
</script>

<style scoped>
.picker-layout { display: flex; gap: 12px; min-height: 420px; }

.picker-sidebar {
  width: 130px; min-width: 130px;
  display: flex; flex-direction: column; gap: 2px;
  border-right: 1px solid #f0f0f0;
  padding-right: 12px;
}
.picker-cat {
  padding: 10px 12px; border-radius: 6px; cursor: pointer;
  font-size: 13px; color: #4B5563; transition: all 0.15s;
}
.picker-cat:hover { background: #F9FAFB; }
.picker-cat.active { background: #EFF6FF; color: #2563EB; font-weight: 600; }

.picker-main { flex: 1; display: flex; flex-direction: column; }

.picker-toolbar {
  display: flex; align-items: center; gap: 10px;
  margin-bottom: 10px; flex-shrink: 0;
}
.picker-count { font-size: 12px; color: #909399; margin-left: auto; }

.picker-search {
  width: 160px; padding: 5px 10px; border: 1px solid #dcdfe6; border-radius: 6px;
  font-size: 12px; outline: none; transition: border-color .15s;
}
.picker-search:focus { border-color: #409eff; }
.picker-search::placeholder { color: #c0c4cc; }

.picker-grid-wrap { flex: 1; overflow-y: auto; max-height: 380px; }
.picker-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); gap: 8px;
}
.picker-item {
  position: relative; aspect-ratio: 1; border-radius: 6px; overflow: hidden;
  border: 2px solid transparent; cursor: pointer; transition: border 0.15s;
}
.picker-item:hover { border-color: #c0c4cc; }
.picker-item.selected { border-color: #409eff; box-shadow: 0 0 0 2px rgba(64,158,255,0.3); }
.picker-thumb { width: 100%; height: 100%; object-fit: cover; display: block; }
.picker-label {
  position: absolute; bottom: 0; left: 0; right: 0;
  font-size: 10px; color: #fff; background: rgba(0,0,0,0.5);
  padding: 2px 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
</style>
