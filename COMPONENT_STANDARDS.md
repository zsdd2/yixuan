# 标准组件库规范 v1.0

> **最后更新：** 2026-04-23  
> **版本：** 1.0

---

## 1. 概述

为避免重复开发和维护成本，本文档定义系统中的标准组件库。所有开发人员**必须优先复用**标准组件，禁止单独开发功能相似的组件。

---

## 2. 标准组件清单

### 2.1 大图查看器（Lightbox）

**标准实现：** `frontend_admin/src/views/PortfolioCenter.vue`（第 279-612 行）

**功能特性：**
- ✅ 拍立得相框风格（白色边框 + 底部信息区）
- ✅ 原图/缩略图切换（🔍 放大镜按钮）
- ✅ 下载原图（⬇ 下载按钮）
- ✅ 键盘导航（← → Esc）
- ✅ 动态比例呼应按钮（按钮尺寸与图片比例一致）
- ✅ 响应式适配（移动端自动调整）

**环境隔离：**

| 使用场景 | 配置 | 功能 |
|---------|------|------|
| **内部工作台** | `isInternal: true` | 显示原图切换、下载按钮 |
| **外部客户页** | `isInternal: false` | 仅显示缩略图，隐藏所有操作按钮 |

**复用方式：**

```vue
<!-- 方式一：完整复用（推荐） -->
<template>
  <!-- 复制 PortfolioCenter.vue 第 279-612 行的 Lightbox 代码 -->
  <Transition name="fade">
    <div v-if="previewVisible" class="preview-mask" @click.self="closePreview">
      <!-- 拍立得相框 + 按钮组 -->
    </div>
  </Transition>
</template>

<script setup lang="ts">
// 复制相关状态和方法
const previewVisible = ref(false)
const previewIdx = ref(0)
const showOriginal = ref(true) // 内部工作台默认 true，客户页强制 false
// ...
</script>
```

**已应用场景：**
- ✅ 作品中心（PortfolioCenter.vue）
- ✅ 最终交付图（ProjectDelivery.vue）
- ⚠️ 客户审核页（ReviewPage.vue）— 功能阉割版（添加确认/留言）
- ⚠️ 客户交付页（DeliveryPage.vue）— 简化版（Element Plus 原生）

**升级策略：**
- 标准件升级后，所有使用该组件的页面**自动继承**新功能
- 如需特殊定制，通过 props 参数控制，而非修改源码

---

### 2.2 照片分拣器（PhotoShuttle）

**标准实现：** `frontend_admin/src/components/PhotoShuttle.vue`

**功能特性：**
- ✅ 左右分栏穿梭式分拣（左侧照片池 + 右侧目标槽位）
- ✅ 批量移入/移出操作
- ✅ 状态修改（pending/selected/deleted）
- ✅ 处理阶段修改（raw/retouched/final）
- ✅ 分页展示（8×5 网格，每页 40 张）
- ✅ 多维筛选（状态/阶段/标签/日期）

**复用方式：**

```vue
<template>
  <PhotoShuttle
    :project-id="projectId"
    :target-id="targetId"
    @updated="handlePhotosUpdated"
  />
</template>

<script setup lang="ts">
import PhotoShuttle from '@/components/PhotoShuttle.vue'
</script>
```

**已应用场景：**
- ✅ 导入中心（ImportCenter.vue）
- ✅ 项目详情（ProjectDetail.vue）

---

### 2.3 照片下载器（usePhotoDownload）

**标准实现：** `frontend_admin/src/composables/usePhotoDownload.ts`

**功能特性：**
- ✅ 单张照片下载
- ✅ 批量照片下载（ZIP）
- ✅ 自动文件名生成（display_id + original_filename）
- ✅ 错误处理和用户提示

**复用方式：**

```typescript
import { usePhotoDownload } from '@/composables/usePhotoDownload'

const { downloadOriginal } = usePhotoDownload()

// 下载单张照片
downloadOriginal(photo)
```

**已应用场景：**
- ✅ 确认原图区（ConfirmedRawSection.vue）
- ✅ 精修图区（RetouchedSection.vue）
- ✅ 完成图区（FinalSection.vue）
- ✅ 作品中心（PortfolioCenter.vue）

---

## 3. 开发规范

### 3.1 优先复用原则

**强制要求：**
1. 开发新功能前，**必须先检查**标准组件库
2. 如果标准组件满足 80% 以上需求，**必须复用**
3. 如需定制，通过 **props 参数**控制，禁止修改源码
4. 禁止单独开发功能相似的组件

**违规示例：**
```vue
<!-- ❌ 错误：单独开发新的大图查看器 -->
<template>
  <div class="my-custom-lightbox">
    <!-- 自己实现的预览逻辑 -->
  </div>
</template>
```

**正确示例：**
```vue
<!-- ✅ 正确：复用标准组件 -->
<template>
  <!-- 复制 PortfolioCenter.vue 的 Lightbox 代码 -->
</template>
```

---

### 3.2 组件升级流程

**标准件升级：**
1. 在标准实现位置（如 PortfolioCenter.vue）修改代码
2. 测试验证新功能
3. 更新本文档（COMPONENT_STANDARDS.md）
4. 通知所有使用该组件的开发人员
5. 逐个页面同步升级（复制最新代码）

**升级通知模板：**
```
【标准组件升级通知】
组件名称：大图查看器（Lightbox）
升级内容：新增原图/缩略图切换功能
影响范围：PortfolioCenter、ProjectDelivery、ReviewPage
升级方式：复制 PortfolioCenter.vue 第 279-612 行最新代码
升级期限：2026-04-30
```

---

### 3.3 特殊定制规范

**允许的定制方式：**

1. **通过 props 控制功能**
   ```typescript
   interface LightboxProps {
     isInternal?: boolean  // 内部/外部环境
     showDownload?: boolean  // 是否显示下载按钮
     showToggle?: boolean  // 是否显示切换按钮
   }
   ```

2. **通过插槽扩展内容**
   ```vue
   <template>
     <Lightbox>
       <template #actions>
         <!-- 自定义操作按钮 -->
       </template>
     </Lightbox>
   </template>
   ```

3. **通过事件监听交互**
   ```vue
   <Lightbox
     @download="handleDownload"
     @toggle="handleToggle"
   />
   ```

**禁止的定制方式：**
- ❌ 直接修改标准组件源码
- ❌ 复制后大幅修改样式和逻辑
- ❌ 创建功能相似的新组件

---

## 4. 待提取标准组件

以下组件存在重复实现，计划提取为标准件：

| 组件名称 | 重复位置 | 优先级 | 计划版本 |
|---------|---------|-------|---------|
| 项目卡片（ProjectCard） | Dashboard.vue, ProjectCenter.vue | 高 | v4.7 |
| 目标卡片（TargetCard） | ProjectDetail.vue | 中 | v4.7 |
| 标签选择器（TagSelector） | 多处 | 中 | v4.8 |
| 日期筛选器（DateFilter） | 多处 | 低 | v4.8 |

---

## 5. 变更记录

| 日期 | 版本 | 变更内容 |
|------|------|---------|
| 2026-04-23 | 1.0 | 首次创建，定义大图查看器、照片分拣器、照片下载器为标准组件 |
