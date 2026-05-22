# 图片显示问题修复规范

## 问题根源
每次修改代码后图片无法显示(显示FAILED或403错误),原因是:
1. **路径存储**: 照片路径必须存储为 **NAS相对路径**(相对于 `NAS_ROOT`)
2. **路径编码**: 前端 `encodeURIComponent` 会将 `/` 编码为 `%2F`,导致后端路径解析错误
3. **后端验证**: 后端 `serve_file` 使用 `is_relative_to()` 检查路径安全性,绝对路径会失败

## 修复规范(强制执行)

### 后端规范
1. **所有照片路径存储为NAS相对路径**:
   ```python
   # ✅ 正确
   nas_resolved = NAS_ROOT.resolve()
   rel_path = file_path.resolve().relative_to(nas_resolved)
   photo.original_path = str(rel_path)  # 存储: "1/raw/xxx.jpg"
   
   # ❌ 错误
   photo.original_path = str(file_path.resolve())  # 存储: "F:\mnt\nas_data\1\raw\xxx.jpg"
   ```

2. **后端 serve_file 处理相对路径**:
   ```python
   @app.get("/storage/{file_path:path}")
   async def serve_file(file_path: str):
       decoded = urllib.parse.unquote(file_path)
       # 拼接为绝对路径
       target = (NAS_ROOT / decoded).resolve()
       # 安全检查
       if not target.is_relative_to(NAS_ROOT.resolve()):
           raise HTTPException(403)
       if not target.is_file():
           raise HTTPException(404)
       return FileResponse(target)
   ```

### 前端规范
1. **不要使用 encodeURIComponent**:
   ```typescript
   // ✅ 正确 - 相对路径直接拼接
   function thumbUrl(photo: PhotoItem): string {
     const path = photo.thumbnail_path || photo.original_path
     return `/storage/${path}`  // 直接使用,不编码
   }
   
   // ❌ 错误
   return `/storage/${encodeURIComponent(path)}`  // 会把 / 编码成 %2F
   ```

2. **所有使用图片路径的地方统一检查**:
   - `ProjectCard.vue` - 项目封面
   - `ConfirmedRawSection.vue` - 确认原图
   - `RetouchedSection.vue` - 精修图
   - `FinalSection.vue` - 完成图
   - `PhotoShuttle.vue` - 分拣台
   - `ProjectDelivery.vue` - 交付视图
   - `PortfolioCenter.vue` - 作品中心
   - `LineageBoard.vue` - 血缘视图

### 检查清单(每次修改代码后必查)
- [ ] 后端所有 `Photo` 创建处是否存储相对路径
- [ ] 前端所有 `thumbUrl` / `getStorageUrl` 函数是否移除了 `encodeURIComponent`
- [ ] 后端 `serve_file` 是否正确拼接 `NAS_ROOT / file_path`
- [ ] 测试: 打开浏览器开发者工具,检查图片请求URL格式是否为 `/storage/1/thumb/xxx.webp`

## 当前修复
后端 `photos.py` 已修复为存储相对路径(line 138-141)。
现在需要修复所有前端组件,移除 `encodeURIComponent`。
