# API 接口台账 (API Registry)

> **维护规则（铁律）：** 每次新增、修改或删除任何接口前，必须先读取本文件与 `ARCHITECTURE.md` 进行逻辑校验；完成代码编写后，必须同步更新本文件，保持文档与代码严格一致。
>
> **最后更新：** 2026-05-09  
> **版本：** 6.0

> **导航提示（2026-05-21）：** 本文件保留完整接口台账。快速查接口分组、废弃路径、页面对应 API 时，先读 [docs/API_NAVIGATION.md](docs/API_NAVIGATION.md) 与 [docs/PAGE_BUSINESS_FLOW.md](docs/PAGE_BUSINESS_FLOW.md)。

**V6.0 更新内容：**
- 添加 ProjectTarget 软删除支持（deleted_at 字段）
- 添加 /health 健康检查端点
- 完善环境变量文档
- 前端容器化支持（Dockerfile + nginx 配置）
- 数据库迁移系统（Alembic）完整配置
- 2026-05-22：新增精修分类字段 `retouch_quality`（`generated` / `generated_4k` / `high_res`）、最终图上传接口 `POST /api/v1/photos/upload-final`、精修图直转完成图接口 `POST /api/v1/photos/{photo_id}/promote-final`、场景参考图接口 `GET/POST /api/v1/projects/{project_id}/targets/{target_id}/references`；`scene_goal` 支持多张并存，`empty_scene` 保持版本迭代；目标列表 `sample_path` 支持未手动设置时自动回退展示图；素材中心复用系统图库并新增 `material_categories` 配置。

---

## 📋 Quick Index — 任务导向快速索引

> **使用说明：** 根据开发任务快速定位到对应接口，点击锚点直达详细文档。

| 🎯 开发任务 | 📍 定位接口 | 🔑 关键词 |
|-----------|-----------|---------|
| **查询项目列表** | [GET /api/v1/projects](#1-get-apiv1projects--项目列表) | 分页、搜索、状态筛选 |
| **创建新项目** | [POST /api/v1/projects](#2-post-apiv1projects--创建项目) | 模板生成、Display ID |
| **管理目标槽位** | [GET /api/v1/projects/{id}/targets](#9-get-apiv1projectsidtargets--目标列表) | Target、软删除、字典 |
| **上传照片** | [POST /api/v1/photos/upload](#17-post-apiv1photosupload--通用上传) | multipart/form-data、缩略图 |
| **NAS 扫描入库** | [POST /api/v1/photos/scan-nas](#18-post-apiv1photosscan-nas--nas-扫描入库) | 异步任务、file_hash 去重 |
| **批量分拣照片** | [PATCH /api/v1/photos/bulk-update](#20-patch-apiv1photosbulk-update--批量更新属性) | 穿梭式分拣、Target 移入移出 |
| **确认原图** | [POST /api/v1/photos/confirm-raw](#25c-post-apiv1photosconfirm-raw--确认原图) | is_confirmed、精修前置条件 |
| **上传精修图** | [POST /api/v1/photos/upload-retouched](#25d-post-apiv1photosupload-retouched--上传精修图) | parent_id、version、关联已有照片 |
| **作品中心查询** | [GET /api/v1/photos/portfolio](#25a-get-apiv1photosportfolio--作品中心列表) | 跨项目、多维筛选 |
| **创建审核分享** | [POST /api/v1/reviews/create](#55-post-apiv1reviewscreate--创建审核会话) | token、过期时间、选中照片 |
| **客户提交反馈** | [POST /api/v1/reviews/{token}/feedback](#61-post-apiv1reviewstokenfeedback--提交客户反馈) | 无需认证、确认/留言 |
| **创建交付分享** | [POST /api/v1/deliveries/create](#62-post-apiv1deliveriescreate--创建交付会话) | ZIP 打包、分享链接 |
| **下载交付 ZIP** | [GET /api/v1/deliveries/{token}/download](#67-get-apiv1deliveriestokendownload--下载-zip) | 无需认证、文件流 |
| **管理客户** | [GET /api/v1/clients](#30-get-apiv1clients--客户列表) | prefix、Display ID 生成 |
| **系统配置** | [GET /api/v1/system/configs](#37a-get-apiv1systemconfigs--获取所有系统配置) | 外网分享域名、机构名称 |
| **项目模板** | [GET /api/v1/settings/templates](#41-get-apiv1settingstemplates--模板列表) | 内置模板、自定义模板 |
| **目标名称字典** | [GET /api/v1/settings/target-dictionary](#47a-get-apiv1settingstarget-dictionary--通用目标词条列表) | 通用词条、模板专属词条 |

---

## 🏗️ 统一规范

### 响应格式

**操作类接口**（创建、更新、删除、归档等）返回统一包装格式：

```json
{
  "code": 200,
  "msg": "操作描述",
  "data": { ... } | null
}
```

**查询/列表类接口**返回结构化 Schema（`*ListResponse`、`*DetailResponse`）：

```json
{
  "total": 42,
  "items": [ ... ]
}
```

**错误响应**统一通过 `HTTPException` 抛出：

```json
{
  "detail": "具体错误原因"
}
```

### 认证机制

**需要认证的接口：**
- 请求头携带：`Authorization: Bearer <token>`
- Token 通过 `/api/v1/auth/login` 获取
- Token 过期时间：24 小时

**无需认证的接口：**
- Guest 模块：`/api/v1/guest/*`
- 审核系统（客户端）：`GET /api/v1/reviews/{token}`、`POST /api/v1/reviews/{token}/feedback`
- 交付系统（客户端）：`GET /api/v1/deliveries/{token}`、`GET /api/v1/deliveries/{token}/download`

**权限级别：**

| 角色 | 权限范围 |
|------|---------|
| `super_admin` | 所有操作 |
| `admin` | 项目管理、用户管理、系统配置 |
| `staff` | 项目查看、照片操作（受项目权限控制） |
| `client` | 仅客户预览（Guest 模块） |

### 分页规范

所有列表接口支持分页参数：

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `skip` | int | 0 | 偏移量 |
| `limit` | int | 20 | 每页数量（1-100） |

响应体包含 `total` 字段（总记录数）。

### 软删除规范

支持软删除的资源：
- 项目（Projects）：`deleted_at` 字段
- 照片（Photos）：`status=deleted`
- 客户（Clients）：`deleted_at` 字段
- 目标槽位（ProjectTargets）：`deleted_at` 字段（V6.0 新增）

软删除后可通过 `restore` 接口恢复。

### 路由定义顺序（CRITICAL）

> **⚠️ FastAPI 路由匹配规则：** 按照路由定义的**物理顺序**进行匹配，第一个匹配成功的路由会被执行。

**正确顺序：**
1. **具体路径路由** → 放在前面（如 `/project/{id}/sessions`）
2. **通配路由（路径参数）** → 放在后面（如 `/{token}`）

**错误示例（会导致 404）：**
```python
@router.get("/{token}")  # ❌ 通配路由在前，会拦截所有请求
@router.get("/project/{id}/sessions")  # ❌ 永远不会被匹配
```

---

## 📊 接口总览

### Admin 模块 — 需要认证

| # | 模块 | Method | 路由路径 | 说明 |
|---|------|--------|---------|------|
| 0 | health | GET | `/` | 根路径健康检查 |
| 0-1 | health | GET | `/health` | 健康检查端点（容器监控） |
| 0a | auth | POST | `/api/v1/auth/login` | 用户登录 |
| 0b | auth | GET | `/api/v1/auth/me` | 获取当前用户信息 |
| 0c | auth | PUT | `/api/v1/auth/me/password` | 修改当前用户密码 |
| 1 | projects | GET | `/api/v1/projects` | 项目列表 |
| 2 | projects | POST | `/api/v1/projects` | 创建项目 |
| 3 | projects | GET | `/api/v1/projects/{id}` | 项目详情 |
| 4 | projects | PATCH | `/api/v1/projects/{id}` | 更新项目 |
| 5 | projects | POST | `/api/v1/projects/{id}/soft-delete` | 移入回收站 |
| 6 | projects | POST | `/api/v1/projects/{id}/restore` | 从回收站恢复 |
| 7 | projects | POST | `/api/v1/projects/{id}/archive` | 归档项目 |
| 8 | projects | POST | `/api/v1/projects/{id}/unarchive` | 取消归档 |
| 9 | targets | GET | `/api/v1/projects/{id}/targets` | 目标列表（自动过滤已软删除） |
| 10 | targets | POST | `/api/v1/projects/{id}/targets` | 创建目标 |
| 11 | targets | PATCH | `/api/v1/projects/{id}/targets/{tid}` | 更新目标 |
| 12 | targets | DELETE | `/api/v1/projects/{id}/targets/{tid}` | 删除目标（软删除） |
| 13a | targets | GET | `/api/v1/projects/{id}/available-targets` | 可用目标名称（字典合并） |
| 13b | targets | POST | `/api/v1/projects/{id}/dictionary-entry` | 快捷追加模板字典词条 |
| 14 | photos | GET | `/api/v1/projects/{id}/photos` | 项目照片列表 |
| 15 | photos | GET | `/api/v1/projects/{id}/photos/shot-dates` | 拍摄日期聚合 |
| 16 | photos | POST | `/api/v1/projects/{id}/photos/upload` | 项目级上传 |
| 16a | photos | GET | `/api/v1/projects/{id}/photos/download` | 下载选中照片 ZIP |
| 16b | photos | GET | `/api/v1/projects/{id}/download-final` | 下载最终交付图 ZIP |
| 17 | photos | POST | `/api/v1/photos/upload` | 通用上传 |
| 18 | photos | POST | `/api/v1/photos/scan-nas` | NAS 扫描入库 |
| 19 | photos | GET | `/api/v1/photos/scan-nas/{task_id}/status` | 扫描任务进度 |
| 20 | photos | PATCH | `/api/v1/photos/bulk-update` | 批量更新属性 |
| 21 | photos | POST | `/api/v1/photos/bulk-soft-delete` | 批量移入回收站 |
| 22 | photos | POST | `/api/v1/photos/bulk-restore` | 批量恢复 |
| 23 | photos | POST | `/api/v1/photos/bulk-hard-delete` | 物理删除 |
| 24 | photos | POST | `/api/v1/photos/bulk-add-tags` | 批量添加标签 |
| 25 | photos | POST | `/api/v1/photos/bulk-remove-tags` | 批量移除标签 |
| 25a | photos | GET | `/api/v1/photos/portfolio` | 作品中心列表（跨项目） |
| 25b | photos | GET | `/api/v1/photos/portfolio/filters` | 作品中心筛选项 |
| 25c | photos | POST | `/api/v1/photos/confirm-raw` | 确认原图 |
| 25c2 | photos | POST | `/api/v1/photos/unconfirm-raw` | 取消确认原图 |
| 25d | photos | POST | `/api/v1/photos/upload-retouched` | 上传精修图 |
| 25e | photos | PATCH | `/api/v1/photos/{id}/notes` | 更新照片备注 |
| 26 | tags | GET | `/api/v1/projects/{id}/tags` | 标签列表 |
| 27 | tags | POST | `/api/v1/projects/{id}/tags` | 创建标签 |
| 28 | tags | PATCH | `/api/v1/projects/{id}/tags/{tid}` | 更新标签 |
| 29 | tags | DELETE | `/api/v1/projects/{id}/tags/{tid}` | 删除标签 |
| 30 | clients | GET | `/api/v1/clients` | 客户列表 |
| 31 | clients | POST | `/api/v1/clients` | 创建客户 |
| 32 | clients | GET | `/api/v1/clients/{id}` | 客户详情 |
| 33 | clients | PATCH | `/api/v1/clients/{id}` | 更新客户 |
| 34 | clients | DELETE | `/api/v1/clients/{id}` | 删除客户 |
| 35 | system | GET | `/api/v1/system/directory-tree` | NAS 目录树 |
| 36 | system | GET | `/api/v1/system/browse-nas` | NAS 文件夹浏览 |
| 37 | system | POST | `/api/v1/system/trigger-cleanup` | 触发清理（测试用） |
| 37a | system | GET | `/api/v1/system/configs` | 获取所有系统配置 |
| 37b | system | GET | `/api/v1/system/configs/{key}` | 获取单个系统配置 |
| 37c | system | PUT | `/api/v1/system/configs/{key}` | 更新系统配置 |
| 38-53 | settings | — | `/api/v1/settings/*` | 设置中心（模板/用户/图库/标签/字典） |

### Guest 模块 — 无需认证

| # | 模块 | Method | 路由路径 | 说明 |
|---|------|--------|---------|------|
| 54 | guest | GET | `/api/v1/guest/photos` | 客户查看照片 |
| 55 | reviews | POST | `/api/v1/reviews/create` | 创建审核会话（需认证） |
| 56-59 | reviews | — | `/api/v1/reviews/project/*` | 审核会话管理（需认证） |
| 60 | reviews | GET | `/api/v1/reviews/{token}` | 获取审核页面数据（无需认证） |
| 61 | reviews | POST | `/api/v1/reviews/{token}/feedback` | 提交客户反馈（无需认证） |
| 62-65 | deliveries | — | `/api/v1/deliveries/*` | 交付会话管理（需认证） |
| 66 | deliveries | GET | `/api/v1/deliveries/{token}` | 获取交付页面数据（无需认证） |
| 67 | deliveries | GET | `/api/v1/deliveries/{token}/download` | 下载 ZIP（无需认证） |

### 基础设施

| # | 模块 | Method | 路由路径 | 说明 |
|---|------|--------|---------|------|
| 68 | health | GET | `/` | 健康检查 |
| 69 | static | GET | `/storage/{file_path:path}` | 静态文件代理 |

---

## 📖 接口详细文档

### 一、Projects 项目管理

路由前缀：`/api/v1/projects` · 文件：`app/routers/projects.py`

---

#### 1. GET `/api/v1/projects` — 项目列表

**查询参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `skip` | int | 0 | 偏移量 |
| `limit` | int | 20 | 每页数量（1-100） |
| `search` | str | None | 模糊搜索项目名称、编号或客户名称 |
| `sort_by` | str | `"deadline"` | 排序方式：`deadline`（按预估结束时间升序）/ `photo_count`（按照片数降序） |
| `status_filter` | str | None | 状态筛选：`active`（活跃）/ `archived`（已归档）/ `deleted`（已删除）/ `completed`（已完成） |
| `client_id` | int | None | 按客户ID筛选 |
| `template_id` | int | None | 按模板ID筛选 |
| `min_photo_count` | int | None | 最少图量（≥0） |
| `max_photo_count` | int | None | 最多图量（≥0） |
| `date_from` | str | None | 创建时间起（YYYY-MM-DD） |
| `date_to` | str | None | 创建时间止（YYYY-MM-DD） |

**响应体** `ProjectListResponse`：

```json
{
  "total": 42,
  "items": [
    {
      "id": 1,
      "name": "春季白图",
      "display_id": "XD000001",
      "cover_image": "/path/to/cover.jpg",
      "client_name": "张三",
      "template_name": "家具拍摄模板",
      "shooting_type": "家具",
      "project_status": "shooting",
      "photo_count": 120,
      "target_count": 8,
      "white_target_count": 5,
      "scene_target_count": 3,
      "created_at": "2026-05-01T10:00:00Z",
      "archived_at": null,
      "deleted_at": null
    }
  ]
}
```

---

#### 2. POST `/api/v1/projects` — 创建项目

**请求体** `ProjectCreate`：

```json
{
  "name": "春季白图",
  "client_id": 1,
  "template_id": 2,
  "shooting_type": "家具",
  "estimated_end_date": "2026-06-01",
  "notes": "备注信息"
}
```

**响应体：**

```json
{
  "code": 200,
  "msg": "项目创建成功",
  "data": {
    "id": 1,
    "display_id": "XD000001",
    "name": "春季白图"
  }
}
```

**业务逻辑：**
- 自动生成 `display_id`：`{客户前缀}{6位补零序号}`
- 如果指定 `template_id`，自动根据模板预设生成 Target 槽位
- `serial_number` 在 `projects` 表中按 `client_prefix` 自增

---

#### 9. GET `/api/v1/projects/{id}/targets` — 目标列表

**查询参数：** 无

**响应体** `TargetListResponse`：

```json
{
  "targets": [
    {
      "id": 1,
      "name": "正面全身",
      "category_type": "white",
      "status": "shooting",
      "is_manual": false,
      "raw_count": 10,
      "confirmed_count": 5,
      "retouched_count": 2,
      "final_count": 1,
      "deleted_at": null
    }
  ]
}
```

**业务逻辑：**
- 自动过滤已软删除的目标（`deleted_at IS NULL`）
- 返回每个 Target 的照片统计（raw/confirmed/retouched/final）

---

#### 12. DELETE `/api/v1/projects/{id}/targets/{tid}` — 删除目标（软删除）

**响应体：**

```json
{
  "code": 200,
  "msg": "目标已删除",
  "data": null
}
```

**业务逻辑：**
- 设置 `deleted_at` 为当前 UTC 时间戳，不物理删除记录
- 可通过清空 `deleted_at` 字段恢复误删的目标

---

### 二、Photos 照片管理

路由前缀：`/api/v1/photos` · 文件：`app/routers/photos.py`

---

#### 17. POST `/api/v1/photos/upload` — 通用上传

**请求体** `multipart/form-data`：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | ✅ | 照片文件 |
| `project_id` | int | ✅ | 项目ID |
| `target_id` | int | ❌ | 目标槽位ID |
| `process_state` | str | ❌ | 处理阶段：`raw`/`retouched`/`final`（默认 `raw`） |
| `tag_ids` | str | ❌ | 标签ID列表（逗号分隔，如 `"1,2,3"`） |
| `shot_date` | str | ❌ | 手动指定拍摄日期 `YYYY-MM-DD`；为空时自动读取 EXIF |

**响应体：**

```json
{
  "code": 200,
  "msg": "上传成功",
  "data": {
    "id": 123,
    "display_id": "A001",
    "original_filename": "IMG_0001.jpg",
    "thumbnail_path": "1/thumbnails/xxx.webp"
  }
}
```

**业务逻辑：**
- EXIF 方向校正
- WebP 缩略图生成（800×800, quality 85）
- EXIF 日期提取（shot_at）
- file_hash 去重校验
- 保存原始文件名（original_filename）

---

#### 18. POST `/api/v1/photos/scan-nas` — NAS 扫描入库

**请求体** `NasScanRequest`：

```json
{
  "project_id": 1,
  "nas_path": "/mnt/nas_data/2026/project_001",
  "target_id": 2,
  "process_state": "raw",
  "tag_ids": [1, 2],
  "shot_date": "2026-05-21"
}
```

**响应体：**

```json
{
  "code": 200,
  "msg": "扫描任务已启动",
  "data": {
    "task_id": "uuid-xxxx-xxxx"
  }
}
```

**业务逻辑：**
- 异步后台任务（BackgroundTasks）
- 批量扫描 NAS 目录，按 `file_hash` 去重
- `shot_date` 为空时自动读取 EXIF；选择日期后使用该日期作为照片 `shot_at`
- 通过 `GET /api/v1/photos/scan-nas/{task_id}/status` 轮询进度

---

#### 20. PATCH `/api/v1/photos/bulk-update` — 批量更新属性

**请求体** `BulkUpdateRequest`：

```json
{
  "photo_ids": [1, 2, 3],
  "target_id": 5,
  "status": "selected",
  "process_state": "retouched"
}
```

**响应体：**

```json
{
  "code": 200,
  "msg": "批量更新成功",
  "data": {
    "updated_count": 3
  }
}
```

**业务逻辑：**
- 穿梭式分拣核心接口
- 支持 `target_id`、`status`、`process_state` 的组合更新
- 前端调用后直接修改本地数据，Vue 响应式驱动 UI 自动更新

---

#### 25a. GET `/api/v1/photos/portfolio` — 作品中心列表

**查询参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `skip` | int | 0 | 偏移量 |
| `limit` | int | 20 | 每页数量 |
| `shooting_type` | str | None | 拍摄类型筛选 |
| `category_type` | str | None | 场景风格筛选：`white`/`scene` |
| `project_id` | int | None | 项目ID筛选 |
| `target_name` | str | None | 目标名称筛选 |
| `client_id` | int | None | 客户ID筛选 |

**响应体** `PortfolioListResponse`：

```json
{
  "total": 100,
  "items": [
    {
      "id": 1,
      "original_filename": "IMG_0001.jpg",
      "thumbnail_path": "1/thumbnails/xxx.webp",
      "original_path": "1/raw/xxx.jpg",
      "target_name": "正面全身",
      "project_name": "春季白图",
      "display_id": "A001",
      "version": 2
    }
  ]
}
```

**业务逻辑：**
- 跨项目查询所有 `process_state=final` 的照片
- 支持多维筛选（拍摄类型/场景风格/项目/目标/客户）

---

#### 25c. POST `/api/v1/photos/confirm-raw` — 确认原图

**请求体：**

```json
{
  "photo_ids": [1, 2, 3]
}
```

**响应体：**

```json
{
  "code": 200,
  "msg": "确认成功",
  "data": {
    "confirmed_count": 3
  }
}
```

**业务逻辑：**
- 设置 `is_confirmed=true`
- 只有 `process_state=raw` 的照片可被确认
- 确认后的原图才能关联精修版本

---

#### 25d. POST `/api/v1/photos/upload-retouched` — 上传精修图

**请求体** `multipart/form-data`：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | ❌ | 精修图文件（与 `existing_photo_id` 二选一） |
| `existing_photo_id` | int | ❌ | 已有照片ID（与 `file` 二选一） |
| `parent_id` | int | ✅ | 确认原图ID |
| `revision_notes` | str | ❌ | 修图师填写的修改说明 |

**响应体：**

```json
{
  "code": 200,
  "msg": "精修图上传成功",
  "data": {
    "id": 456,
    "parent_id": 123,
    "version": 2
  }
}
```

**业务逻辑：**
- `parent_id` 指向确认原图（FK → photos.id）
- `version` 整数字段，同一 parent_id 下自动递增（从 1 开始）
- 支持两种来源：
  - **上传新文件**：通过 `file` 参数上传精修图文件
  - **关联已有照片**：通过 `existing_photo_id` 参数将项目内已有照片转为精修版本

---

### 三、Reviews 客户审核系统

路由前缀：`/api/v1/reviews` · 文件：`app/routers/reviews.py`

---

#### 55. POST `/api/v1/reviews/create` — 创建审核会话

**请求体** `ReviewSessionCreate`：

```json
{
  "project_id": 1,
  "selected_photo_ids": [1, 2, 3, 4, 5],
  "expired_days": 7,
  "notes": "请客户确认这批原图"
}
```

**响应体：**

```json
{
  "code": 200,
  "msg": "审核会话创建成功",
  "data": {
    "session_id": 1,
    "token": "uuid-xxxx-xxxx",
    "share_url": "https://example.com/share/uuid-xxxx-xxxx",
    "expired_at": "2026-05-16T10:00:00Z"
  }
}
```

**业务逻辑：**
- Token 使用 UUID4，防止猜测攻击
- 过期时间校验（1-30 天可配置）
- 优先使用 `external_share_url` 配置（外网分享域名）

---

#### 60. GET `/api/v1/reviews/{token}` — 获取审核页面数据（无需认证）

**路径参数：**
- `token`：审核会话 token

**响应体** `ReviewPageData`：

```json
{
  "project_name": "春季白图",
  "client_name": "张三",
  "is_disabled": false,
  "expired_at": "2026-05-16T10:00:00Z",
  "targets": [
    {
      "target_name": "正面全身",
      "category_type": "white",
      "confirmed_count": 5,
      "total_count": 10,
      "photos": [
        {
          "id": 1,
          "thumbnail_path": "1/thumbnails/xxx.webp",
          "original_filename": "IMG_0001.jpg",
          "is_confirmed": false,
          "version": 1
        }
      ]
    }
  ]
}
```

**业务逻辑：**
- 无需认证，公开访问
- 首次访问自动标记 `is_viewed` 和 `viewed_at`
- 作废校验：`is_disabled=true` 时返回 403
- **资产保护**：仅传递 `thumbnail_path`，严禁传递 `original_path`

---

#### 61. POST `/api/v1/reviews/{token}/feedback` — 提交客户反馈（无需认证）

**请求体** `ReviewFeedbackCreate`：

```json
{
  "photo_id": 1,
  "is_confirmed": true,
  "comment": "这张很好，保持"
}
```

**响应体：**

```json
{
  "code": 200,
  "msg": "反馈提交成功",
  "data": null
}
```

**业务逻辑：**
- 无需认证，客户可直接提交
- 客户确认精修图或成片时，自动设置 `is_locked=true`
- Admin 端通过轮询接口（每 30 秒）获取最新反馈

---

### 四、Deliveries 客户交付系统

路由前缀：`/api/v1/deliveries` · 文件：`app/routers/deliveries.py`

---

#### 62. POST `/api/v1/deliveries/create` — 创建交付会话

**请求体** `DeliverySessionCreate`：

```json
{
  "project_id": 1,
  "expired_days": 7,
  "notes": "最终交付图"
}
```

**响应体：**

```json
{
  "code": 200,
  "msg": "交付会话创建成功",
  "data": {
    "session_id": 1,
    "token": "uuid-xxxx-xxxx",
    "share_url": "https://example.com/delivery/uuid-xxxx-xxxx",
    "expired_at": "2026-05-16T10:00:00Z"
  }
}
```

**业务逻辑：**
- 项目状态必须为 `completed`
- 项目必须至少存在一张 `process_state=final` 的最终交付图
- 如果 `zip_status != completed`，创建链接后会后台触发 ZIP 打包

---

#### 66. GET `/api/v1/deliveries/{token}` — 获取交付页面数据（无需认证）

**路径参数：**
- `token`：交付会话 token

**响应体** `DeliveryPageData`：

```json
{
  "project_name": "春季白图",
  "client_name": "张三",
  "organization_name": "XX摄影工作室",
  "is_disabled": false,
  "expired_at": "2026-05-16T10:00:00Z",
  "zip_status": "completed",
  "zip_generated_at": "2026-05-09T10:00:00Z",
  "zip_size": 1024000,
  "photos": [
    {
      "id": 1,
      "thumbnail_path": "1/thumbnails/xxx.webp",
      "target_name": "正面全身",
      "display_id": "A001",
      "version": 2
    }
  ]
}
```

**业务逻辑：**
- 无需认证，公开访问
- 作废校验：`is_disabled=true` 时返回 403
- 仅显示缩略图，保护资产安全

---

#### 67. GET `/api/v1/deliveries/{token}/download` — 下载 ZIP（无需认证）

**路径参数：**
- `token`：交付会话 token

**响应体：** 文件流（`Content-Disposition: attachment`）

**业务逻辑：**
- 无需认证，客户可直接下载
- ZIP 状态校验（仅 `completed` 状态可下载）
- 文件命名规则：`{机构名称}_{项目名称}_{归档日期}.zip`

---

## 📚 数据模型速查

### 核心模型关系

```
clients 1──N projects 1──N project_targets
                │                 │
                │ 1──N photos N───┘ (target_id nullable)
                │       │
                │       N──M project_tags (via photo_tags)
                │
                N──M users (via user_project_access)

project_templates 1──N template_targets
system_target_dictionary (独立表，通用目标名称词条)
```

### Project（项目）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 主键 |
| `name` | str | 项目名称 |
| `display_id` | str | 显示ID（如 `XD000001`） |
| `serial_number` | int | 序号（按 client_prefix 自增） |
| `client_id` | int | 客户ID（FK） |
| `template_id` | int | 模板ID（FK，nullable） |
| `shooting_type` | str | 拍摄类型 |
| `project_status` | str | 项目状态（not_started/shooting/retouching/client_review/completed） |
| `cover_image` | str | 封面图路径 |
| `estimated_end_date` | date | 预估结束时间 |
| `archived_at` | datetime | 归档时间（nullable） |
| `deleted_at` | datetime | 软删除时间（nullable） |
| `zip_path` | str | ZIP 文件路径（nullable） |
| `zip_status` | str | ZIP 状态（pending/processing/completed/failed） |
| `zip_generated_at` | datetime | ZIP 生成时间（nullable） |

### ProjectTarget（目标槽位）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 主键 |
| `project_id` | int | 项目ID（FK） |
| `name` | str | 目标名称 |
| `category_type` | str | 分类（white/scene） |
| `status` | str | 状态（not_started/shooting/retouching/client_review/completed） |
| `is_manual` | bool | 是否手动设置状态 |
| `deleted_at` | datetime | 软删除时间（nullable，V6.0 新增） |

### Photo（照片）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 主键 |
| `display_id` | str | 显示ID（项目内自增，如 `A001`） |
| `project_id` | int | 项目ID（FK） |
| `target_id` | int | 目标槽位ID（FK，nullable） |
| `original_filename` | str | 原始文件名 |
| `original_path` | str | 原图路径（NAS 相对路径） |
| `thumbnail_path` | str | 缩略图路径 |
| `file_hash` | str | 文件哈希（去重） |
| `process_state` | str | 处理阶段（raw/retouched/final） |
| `status` | str | 照片状态（pending/selected/deleted） |
| `is_confirmed` | bool | 是否确认原图 |
| `is_locked` | bool | 是否锁定（客户确认后自动锁定） |
| `parent_id` | int | 父照片ID（FK，nullable，精修版本管理） |
| `version` | int | 版本号（同一 parent_id 下自增） |
| `revision_notes` | str | 修图师备注 |
| `client_notes` | str | 客户备注 |
| `shot_at` | datetime | 拍摄时间（EXIF 提取） |

### ReviewSession（审核会话）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 主键 |
| `token` | str | UUID4 分享令牌（唯一索引） |
| `project_id` | int | 项目ID（FK） |
| `created_by` | int | 创建人ID（FK） |
| `selected_photo_ids` | JSON | 选中照片ID列表 |
| `expired_at` | datetime | 过期时间 |
| `is_disabled` | bool | 是否作废 |
| `is_viewed` | bool | 是否已查看 |
| `viewed_at` | datetime | 首次查看时间（nullable） |

### ReviewFeedback（审核反馈）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 主键 |
| `session_id` | int | 会话ID（FK） |
| `photo_id` | int | 照片ID（FK） |
| `is_confirmed` | bool | 是否确认 |
| `comment` | str | 留言内容（nullable） |
| `created_at` | datetime | 创建时间 |

### DeliverySession（交付会话）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 主键 |
| `token` | str | UUID4 分享令牌（唯一索引） |
| `project_id` | int | 项目ID（FK） |
| `created_by` | int | 创建人ID（FK） |
| `expired_at` | datetime | 过期时间 |
| `is_disabled` | bool | 是否作废 |

### Client（客户）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 主键 |
| `name` | str | 客户名称 |
| `prefix` | str | 前缀（A-Z 大写，唯一，用于生成 Display ID） |
| `phone` | str | 电话 |
| `company` | str | 公司 |
| `address` | str | 地址 |
| `id_number` | str | 证照号 |
| `avatar` | str | 头像路径 |
| `deleted_at` | datetime | 软删除时间（nullable） |

---

## 🔄 变更记录

### V6.0 (2026-05-09)

**核心变更：**
1. **ProjectTarget 软删除支持**：添加 `deleted_at` 字段，删除操作改为软删除
2. **健康检查端点**：新增 `/health` 端点，支持容器健康监控
3. **数据库迁移系统**：完整配置 Alembic，支持版本化迁移管理
4. **前端容器化**：提供 Dockerfile 和 nginx 配置，支持生产环境部署
5. **环境变量文档**：完善 `.env.template`，包含所有必需变量说明

**影响接口：**
- `GET /api/v1/projects/{id}/targets`：自动过滤已软删除记录
- `DELETE /api/v1/projects/{id}/targets/{tid}`：改为软删除（设置 deleted_at）

### V5.0 (2026-05-08)

**核心变更：**
1. **客户交付系统**：ZIP 打包、脏数据监听、定时任务
2. **分享链接管理**：审核会话历史、作废/恢复机制
3. **外网链接配置**：支持配置外网分享域名

**新增接口：**
- `POST /api/v1/deliveries/create`：创建交付会话
- `GET /api/v1/deliveries/project/{id}/sessions`：获取项目所有交付会话列表
- `PATCH /api/v1/deliveries/session/{id}/disable`：作废/恢复交付链接
- `DELETE /api/v1/deliveries/{session_id}`：删除交付会话
- `GET /api/v1/deliveries/{token}`：获取交付页面数据
- `GET /api/v1/deliveries/{token}/download`：下载交付 ZIP

### V4.6 (2026-05-07)

**核心变更：**
1. **资产保护机制**：客户审核页面严禁暴露原图路径
2. **环境隔离**：内部工作台支持原图查看，外部客户页仅显示缩略图

**影响接口：**
- `GET /api/v1/reviews/{token}`：响应体仅包含 `thumbnail_path`，移除 `original_path`

### V4.5 (2026-05-06)

**核心变更：**
1. **客户审核系统**：分享链接、客户反馈、照片锁定机制
2. **反馈链路打通**：Admin 端实时显示客户反馈

**新增接口：**
- `POST /api/v1/reviews/create`：创建审核会话
- `GET /api/v1/reviews/project/{id}/sessions`：获取项目所有审核会话列表
- `GET /api/v1/reviews/project/{id}/feedbacks`：获取项目所有反馈
- `GET /api/v1/reviews/session/{id}/feedbacks`：查询会话反馈
- `PATCH /api/v1/reviews/session/{id}/disable`：作废/恢复审核链接
- `GET /api/v1/reviews/{token}`：获取审核页面数据
- `POST /api/v1/reviews/{token}/feedback`：提交客户反馈

**新增字段：**
- `Photo.is_locked`：照片锁定标记

### V4.0 (2026-05-05)

**核心变更：**
1. **精修版本管理**：parent_id 链路、version 递增
2. **确认原图机制**：is_confirmed 字段、取消确认校验

**新增接口：**
- `POST /api/v1/photos/confirm-raw`：确认原图
- `POST /api/v1/photos/unconfirm-raw`：取消确认原图
- `POST /api/v1/photos/upload-retouched`：上传精修图

**新增字段：**
- `Photo.is_confirmed`：是否确认原图
- `Photo.parent_id`：父照片ID（精修版本管理）
- `Photo.version`：版本号
- `Photo.revision_notes`：修图师备注
- `Photo.client_notes`：客户备注

### V3.0 (2026-05-04)

**核心变更：**
1. **Target 看板模型**：取代 Category 分类体系
2. **目标名称数据字典**：通用词条 + 模板专属词条
3. **项目模板系统**：内置模板、自定义模板

**新增接口：**
- `GET /api/v1/projects/{id}/targets`：目标列表
- `POST /api/v1/projects/{id}/targets`：创建目标
- `PATCH /api/v1/projects/{id}/targets/{tid}`：更新目标
- `DELETE /api/v1/projects/{id}/targets/{tid}`：删除目标
- `GET /api/v1/projects/{id}/available-targets`：可用目标名称
- `POST /api/v1/projects/{id}/dictionary-entry`：快捷追加模板字典词条
- `GET /api/v1/settings/target-dictionary`：通用目标词条列表
- `POST /api/v1/settings/target-dictionary`：新增通用词条
- `DELETE /api/v1/settings/target-dictionary/{id}`：删除通用词条

**新增表：**
- `project_targets`：目标槽位表
- `system_target_dictionary`：通用目标名称词条表

### V2.0 (2026-05-03)

**核心变更：**
1. **客户管理模块**：客户建档、prefix 生成 Display ID
2. **设置中心**：系统图库、全局标签、用户管理

**新增接口：**
- `GET /api/v1/clients`：客户列表
- `POST /api/v1/clients`：创建客户
- `GET /api/v1/clients/{id}`：客户详情
- `PATCH /api/v1/clients/{id}`：更新客户
- `DELETE /api/v1/clients/{id}`：删除客户
- `GET /api/v1/settings/users`：用户列表
- `POST /api/v1/settings/users`：创建用户
- `PATCH /api/v1/settings/users/{id}`：更新用户
- `DELETE /api/v1/settings/users/{id}`：删除用户

**新增表：**
- `clients`：客户表
- `users`：用户表

### V1.0 (2026-05-01)

**初始版本：**
1. 项目管理基础功能
2. 照片上传/NAS 扫描
3. 照片分拣（Category 分类体系）

**核心接口：**
- `GET /api/v1/projects`：项目列表
- `POST /api/v1/projects`：创建项目
- `POST /api/v1/photos/upload`：通用上传
- `POST /api/v1/photos/scan-nas`：NAS 扫描入库
- `PATCH /api/v1/photos/bulk-update`：批量更新属性

---

**文档版本：** V6.0  
**生成日期：** 2026-05-09  
**维护者：** 开发团队

