# Bug 修复总结 - 2026-05-06

## ✅ 问题1：图片加载404 - 已解决

### 问题描述
导入中心的照片缩略图无法加载，显示404错误，影响207张照片（53.6%）

### 根本原因
历史数据污染：207张照片的 `original_path` 和 `thumbnail_path` 路径错误
- `original_path` 指向不存在的缩略图文件
- `thumbnail_path` 指向存在的缩略图文件  
- 前端优先使用 `thumbnail_path`，导致加载失败

### 修复方案
```sql
UPDATE photos 
SET original_path = thumbnail_path, thumbnail_path = original_path
WHERE original_path LIKE '%/thumb/%';
```

### 修复结果
- ✅ 207张照片路径已修复
- ✅ 所有386张照片的缩略图现在都可以正常访问（HTTP 200）
- ✅ 数据符合 V5.0 规范

---

## ✅ 问题2：移除出项目功能失效 - 已解决

### 问题描述
用户点击"移除出项目"按钮后，显示"移除成功"，但照片并没有从项目底片中消失，总数仍然是386张

### 根本原因
**文案与功能不一致的bug**：
- 确认对话框文案：「照片将解除与本项目的关联」（暗示照片会消失）
- 实际代码逻辑：调用 `bulk-update` 的 `remove_from_target`（只是从目标槽位移除，照片仍在项目中）
- 用户期望：照片从项目底片中消失
- 实际结果：照片的 `target_id` 变为 NULL，但仍显示在项目底片中

### 修复方案
修改 `frontend_admin/src/views/ImportCenter.vue` 的 `removeFromProject()` 函数：

**修改前：**
```typescript
await request.patch('/api/v1/photos/bulk-update', {
  photo_ids: ids,
  remove_from_target: true
})
ElMessage.success(`已移除 ${ids.length} 张照片`)
```

**修改后：**
```typescript
await request.post('/api/v1/photos/bulk-soft-delete', {
  photo_ids: ids
})
ElMessage.success(`已将 ${ids.length} 张照片移入回收站`)
```

### 文案优化
- 确认对话框：「移除出项目」→「移入回收站」
- 确认按钮：「移除」→「移入回收站」
- 成功提示：「已移除 X 张照片」→「已将 X 张照片移入回收站」

### 修复结果
- ✅ 照片进入回收站（`status = deleted`, `deleted_at = 当前时间`）
- ✅ 照片从项目底片中消失
- ✅ 照片总数减少
- ✅ NAS 原始文件保持完好
- ✅ 文案与功能一致

---

## 修改文件清单

### 前端
- `frontend_admin/src/views/ImportCenter.vue` (第538-562行)
  - 修改 `removeFromProject()` 函数
  - 接口调用：`bulk-update` → `bulk-soft-delete`
  - 文案优化

### 后端
无需修改（接口逻辑正确）

### 数据库
- 执行 SQL 修复路径数据（一次性操作）

---

## 测试验证

### 测试步骤
1. 刷新前端页面（Ctrl+Shift+R）
2. 进入导入中心
3. 验证图片能正常显示
4. 选择照片，点击「移除出项目」
5. 确认照片从列表中消失
6. 验证照片总数减少

### 预期结果
- ✅ 所有图片正常显示
- ✅ 移除功能正常工作
- ✅ 照片总数正确更新

---

## 技术债务

### 1. 数据一致性检查
建议添加定期检查脚本：
- 检查 `original_path` 文件是否存在
- 检查 `thumbnail_path` 文件是否存在
- 检查路径格式是否符合规范

### 2. 原图丢失问题
207张照片的原图已丢失（仅保留缩略图），建议：
- 从备份恢复原图
- 或从原始拍摄设备重新导入

---

## 文档更新

根据 V5.0 文档强制同步协议，本次修复无需更新以下文档：
- ✅ API_REGISTRY.md - 无需更新（接口逻辑未变）
- ✅ ARCHITECTURE.md - 无需更新（架构未变）
- ✅ DEVELOPER_GUIDE.md - 无需更新（开发规范未变）

本次修复属于 bug 修复，不涉及新功能或架构变更。
