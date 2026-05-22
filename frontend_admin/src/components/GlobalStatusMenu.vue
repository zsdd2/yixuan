<template>
  <el-dropdown-menu class="ctx-menu">
    <slot name="before" />

    <el-dropdown-item disabled divided class="menu-group-title">项目状态</el-dropdown-item>
    <el-dropdown-item
      command="status:not_started"
      :class="{ 'is-current': currentStatus === 'not_started' }"
    >
      <span class="mi"><span class="sd" style="background:#c0c4cc" /> 未开始</span>
    </el-dropdown-item>
    <el-dropdown-item
      command="status:shooting"
      :class="{ 'is-current': currentStatus === 'shooting' }"
    >
      <span class="mi"><span class="sd" style="background:#409eff" /> 拍摄中</span>
    </el-dropdown-item>
    <el-dropdown-item
      command="status:retouching"
      :class="{ 'is-current': currentStatus === 'retouching' }"
    >
      <span class="mi"><span class="sd" style="background:#e6a23c" /> 修图中</span>
    </el-dropdown-item>
    <el-dropdown-item
      command="status:completed"
      :class="{ 'is-current': currentStatus === 'completed' }"
    >
      <span class="mi"><span class="sd" style="background:#67c23a" /> 已完成</span>
    </el-dropdown-item>

    <slot name="after" />
  </el-dropdown-menu>
</template>

<script setup lang="ts">
defineProps<{
  currentStatus?: string
}>()
</script>

<style scoped>
.menu-group-title {
  font-size: 11px;
  color: #909399;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  cursor: default !important;
  padding: 4px 16px;
}

.mi {
  display: flex;
  align-items: center;
  gap: 8px;
}

.mi-danger {
  color: #f56c6c;
}

.sd {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.is-current {
  background-color: #f0f9ff;
  color: #409eff;
  font-weight: 500;
}
</style>
