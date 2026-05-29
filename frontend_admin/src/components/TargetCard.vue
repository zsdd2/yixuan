<template>
  <div class="target-card" :class="'status-' + target.target_status" @click="$emit('drill', target.id)">
    <!-- 已完成角标 -->
    <div v-if="target.target_status === 'completed'" class="completed-ribbon">已完成</div>

    <!-- 状态徽标 + 三点菜单 -->
    <div class="card-header" style="position: relative; z-index: 2;">
      <span class="card-title">{{ target.name }}</span>
      <span v-if="target.target_status !== 'completed'" class="status-badge" :class="'badge-' + target.target_status">
        {{ statusLabel[target.target_status] || target.target_status }}
      </span>
      <div class="header-spacer" />
      <el-dropdown trigger="click" @command="onMenuCommand" @click.stop>
        <el-button class="more-btn" size="small" text @click.stop>
          <el-icon><MoreFilled /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu class="ctx-menu">
            <el-dropdown-item command="edit"><span class="mi">✏️ 编辑</span></el-dropdown-item>
            <el-dropdown-item disabled divided class="menu-group-title">修改状态</el-dropdown-item>
            <el-dropdown-item command="status:not_started" :class="{ 'is-current': target.target_status === 'not_started' }">
              <span class="mi"><span class="sd" style="background:#c0c4cc" /> 未拍摄</span>
            </el-dropdown-item>
            <el-dropdown-item command="status:shooting" :class="{ 'is-current': target.target_status === 'shooting' }">
              <span class="mi"><span class="sd" style="background:#409eff" /> 拍摄中</span>
            </el-dropdown-item>
            <el-dropdown-item command="status:retouching" :class="{ 'is-current': target.target_status === 'retouching' }">
              <span class="mi"><span class="sd" style="background:#e6a23c" /> 精修中</span>
            </el-dropdown-item>
            <el-dropdown-item command="status:client_review" :class="{ 'is-current': target.target_status === 'client_review' }">
              <span class="mi"><span class="sd" style="background:#9b59b6" /> 客户确认中</span>
            </el-dropdown-item>
            <el-dropdown-item command="status:completed" :class="{ 'is-current': target.target_status === 'completed' }">
              <span class="mi"><span class="sd" style="background:#67c23a" /> 已完成</span>
            </el-dropdown-item>
            <el-dropdown-item command="delete" divided><span class="mi mi-danger">🗑️ 删除</span></el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <!-- 样图预览 -->
    <div class="card-preview">
      <el-image
        v-if="target.sample_path"
        :src="getThumbnailUrl(target.sample_path)"
        fit="cover"
        class="sample-img"
      >
        <template #error>
          <div class="sample-placeholder"><el-icon><PictureFilled /></el-icon></div>
        </template>
      </el-image>
      <div v-else class="sample-placeholder">
        <el-icon><PictureFilled /></el-icon>
        <span>暂无样图</span>
      </div>
    </div>

    <!-- 三级进度统计 -->
    <div class="card-stats">
      <div class="stat-row">
        <div class="stat-item">
          <span class="stat-label">原图</span>
          <span class="stat-value raw">{{ target.raw_count }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">精修</span>
          <span class="stat-value retouched">{{ target.retouched_count }}</span>
        </div>
        <div class="stat-item">
          <span class="stat-label">完成</span>
          <span class="stat-value final">{{ target.final_count }}</span>
        </div>
      </div>
      <!-- 进度条 -->
      <div class="progress-bar">
        <div
          class="progress-segment seg-raw"
          :style="{ width: segWidth('raw') }"
        />
        <div
          class="progress-segment seg-retouched"
          :style="{ width: segWidth('retouched') }"
        />
        <div
          class="progress-segment seg-final"
          :style="{ width: segWidth('final') }"
        />
      </div>
    </div>

    <!-- 底部：描述 + 操作按钮 -->
    <div class="card-footer">
      <div v-if="target.requirement_desc" class="card-desc">
        {{ target.requirement_desc }}
      </div>
      <div class="card-actions">
        <el-button
          type="primary"
          size="small"
          plain
          @click.stop="$emit('open-shuttle', target.id)"
        >
          📷 照片整理
        </el-button>
        <el-button
          v-if="target.target_status !== 'completed'"
          type="success"
          size="small"
          plain
          class="complete-btn"
          @click.stop="$emit('complete', target.id)"
        >
          标记完成
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { PictureFilled, MoreFilled } from '@element-plus/icons-vue'

const API_BASE = ''

export interface TargetItem {
  id: number
  project_id: number
  group_id?: number | null
  group_name?: string | null
  name: string
  category_type: 'white' | 'scene'
  target_status: string
  is_manual: boolean
  sample_path: string | null
  requirement_desc: string | null
  sort_order: number
  photo_count: number
  raw_count: number
  confirmed_count: number
  retouched_count: number
  final_count: number
  created_at: string
}

const props = defineProps<{ target: TargetItem }>()
const emit = defineEmits<{
  'navigate-to-lineage': [id: number]
  'open-shuttle': [id: number]
  drill: [id: number]
  complete: [id: number]
  edit: [target: TargetItem]
  delete: [id: number]
  'set-status': [id: number, status: string]
}>()

const statusLabel: Record<string, string> = {
  not_started: '未拍摄',
  shooting: '拍摄中',
  retouching: '精修中',
  client_review: '客户确认中',
  completed: '已完成',
}

function getThumbnailUrl(path: string): string {
  return `${API_BASE}/storage/${path}`
}

function segWidth(type: 'raw' | 'retouched' | 'final'): string {
  const total = props.target.photo_count
  if (total === 0) return '0%'
  const count = type === 'raw' ? props.target.raw_count
    : type === 'retouched' ? props.target.retouched_count
    : props.target.final_count
  return `${(count / total) * 100}%`
}

function onMenuCommand(cmd: string) {
  if (cmd === 'edit') {
    emit('edit', props.target)
  } else if (cmd === 'delete') {
    emit('delete', props.target.id)
  } else if (cmd.startsWith('status:')) {
    emit('set-status', props.target.id, cmd.replace('status:', ''))
  }
}
</script>

<style scoped>
.target-card {
  position: relative;
  background: white;
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
  border: 2px solid #ebeef5;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}

.target-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

.target-card.status-completed {
  border-color: #67c23a;
}

/* 已完成角标 */
.completed-ribbon {
  position: absolute;
  top: 16px;
  right: -30px;
  background: #67c23a;
  color: white;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 36px;
  transform: rotate(45deg);
  z-index: 1;
  box-shadow: 0 2px 4px rgba(0,0,0,0.15);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: #2c3e50;
}

.header-spacer {
  flex: 1;
}

.more-btn {
  padding: 4px;
  font-size: 16px;
  color: #909399;
}

.more-btn:hover {
  color: #409eff;
}

.status-badge {
  font-size: 11px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 10px;
  white-space: nowrap;
}

.badge-not_started { background: #f0f2f5; color: #909399; }
.badge-shooting    { background: #ecf5ff; color: #409eff; }
.badge-retouching     { background: #fdf6ec; color: #e6a23c; }
.badge-client_review  { background: #f5f0ff; color: #9b59b6; }
.badge-completed      { background: #f0f9eb; color: #67c23a; }

.card-preview {
  height: 120px;
  border-radius: 8px;
  overflow: hidden;
  background: #f5f7fa;
}

.sample-img {
  width: 100%;
  height: 100%;
}

.sample-img :deep(img) {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.sample-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  color: #c0c4cc;
  font-size: 13px;
}

.card-stats {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stat-row {
  display: flex;
  justify-content: space-around;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.stat-label {
  font-size: 11px;
  color: #909399;
}

.stat-value {
  font-size: 16px;
  font-weight: 700;
}

.stat-value.raw       { color: #909399; }
.stat-value.retouched { color: #e6a23c; }
.stat-value.final     { color: #67c23a; }

.progress-bar {
  height: 6px;
  border-radius: 3px;
  background: #f0f2f5;
  display: flex;
  overflow: hidden;
}

.progress-segment {
  height: 100%;
  transition: width 0.3s;
}

.seg-raw       { background: #c0c4cc; }
.seg-retouched { background: #e6a23c; }
.seg-final     { background: #67c23a; }

.card-actions { display: flex; gap: 6px; flex-wrap: wrap; }

.card-footer {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-desc {
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.complete-btn {
  align-self: flex-end;
}
.menu-group-title :deep(.el-dropdown-menu__item) { font-size: 12px; color: #909399; cursor: default; }

/* Unified context menu */
.ctx-menu { min-width: 160px; padding: 4px 0; }
.mi { display: flex; align-items: center; gap: 6px; font-size: 13px; }
.mi-danger { color: #f56c6c; }
.sd { display: inline-block; width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.is-current { background: #f0f7ff; }
.is-current :deep(.el-dropdown-menu__item) { font-weight: 600; color: #2563eb; }
</style>
