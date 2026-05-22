# Fetch调用修复总结

## 已修复的文件 ✅

1. **ProjectCard.vue** - 项目卡片
   - setProjectStatus() - 修改项目状态
   - toggleArchive() - 归档/取消归档
   - saveEdit() - 保存编辑
   - confirmDelete() - 删除项目

2. **ImagePicker.vue** - 图片选择器 ⭐ 关键修复
   - fetchCatImages() - 获取分类图片
   - fetchProjectPhotos() - 获取项目图片（修复了项目图片为空的问题）

3. **ImportCenter.vue** - 导入中心
   - createTag() - 创建标签
   - deleteTag() - 删除标签

4. **LineageBoard.vue** - 工作台
   - loadPhotos() - 加载照片
   - loadMorePhotos() - 加载更多
   - saveEdit() - 保存编辑

5. **ConfirmedRawSection.vue** - 确认原图区
   - confirmSelected() - 确认选中
   - removeFromTarget() - 移出目标
   - unconfirmPhoto() - 取消确认

## 待修复的文件 ⚠️

### 高优先级（需要认证的API）

1. **RetouchedSection.vue** - 精修图区
   - deleteVersion() - 删除版本 (line 258)
   - doUpload() - 上传精修图 (line 304, 328)
   - saveNotes() - 保存备注 (line 371)

2. **ProjectDelivery.vue** - 项目交付
   - downloadSelected() - 下载选中 (line 222)
   - loadDeliveryData() - 加载交付数据 (line 341-343)

3. **ShareDeliveryModal.vue** - 分享交付弹窗
   - createDelivery() - 创建交付 (line 151)
   - loadSessions() - 加载会话 (line 219)
   - toggleDisable() - 切换禁用 (line 247)
   - deleteSession() - 删除会话 (line 274)

4. **NASPathPicker.vue** - NAS路径选择器
   - loadPath() - 加载路径 (line 88)

5. **ProjectDetail.vue** - 项目详情
   - loadPhotosForPicker() - 加载照片选择器 (line 665)

### 低优先级（公开API，无需认证）

1. **DeliveryPage.vue** - 交付页面（客户端）
   - downloadAll() - 下载全部 (line 228)
   - 这是公开的下载链接，使用token参数认证，无需修复

## 修复模式

### 原始代码模式
```javascript
const res = await fetch('/api/v1/xxx', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ data })
})
if (!res.ok) throw new Error('失败')
const result = await res.json()
```

### 修复后模式
```javascript
import request from '../api/request'

const result = await request.post('/api/v1/xxx', { data })
```

## 修复原因

原生fetch不会自动携带认证token，导致后端返回403 Forbidden。
封装的request工具会自动从localStorage读取token并添加到请求头。

## 下一步行动

建议优先修复以下组件（用户高频使用）：
1. RetouchedSection.vue - 精修图上传和管理
2. ShareDeliveryModal.vue - 交付分享功能
3. ProjectDelivery.vue - 项目交付下载
4. NASPathPicker.vue - NAS路径浏览
5. ProjectDetail.vue - 项目详情照片选择
