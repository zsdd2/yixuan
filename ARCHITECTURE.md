# 商业摄影项目跟进系统 — 架构与开发规范文档 V6.0

> **最后更新：** 2026-05-09  
> **V6.0 更新：** ProjectTarget 软删除支持 + 健康检查端点 + 前端容器化 + Alembic 数据库迁移系统

> **导航提示（2026-05-21）：** 本文件保留为架构全量文档。日常开发先从 [docs/README.md](docs/README.md) 进入；页面和业务流程查 [docs/PAGE_BUSINESS_FLOW.md](docs/PAGE_BUSINESS_FLOW.md)，规范分类查 [docs/STANDARDS.md](docs/STANDARDS.md)。

**V6.0 核心变更：**
1. **数据库迁移系统**：完整配置 Alembic，支持版本化迁移管理
2. **ProjectTarget 软删除**：添加 `deleted_at` 字段，删除操作改为软删除
3. **健康检查端点**：新增 `/health` 端点，支持容器健康监控
4. **前端容器化**：提供 Dockerfile 和 nginx 配置，支持生产环境部署
5. **环境变量文档**：完善 `.env.template`，包含所有必需变量说明
6. **查询逻辑优化**：所有 ProjectTarget 查询自动过滤已软删除记录

---

## 📋 Quick Index — 任务导向快速索引

> **使用说明：** 根据开发任务快速定位到对应章节，点击锚点直达详细文档。

| 🎯 开发任务 | 📍 定位章节 | 🔑 关键词 |
|-----------|-----------|---------|
| **修改照片分拣逻辑** | [§4.3 照片管理](#43-照片管理-photos) | 穿梭式分拣、bulk-update、PhotoShuttle |
| **调整项目状态流转** | [§4.1 项目管理](#41-项目管理-projects) | project_status、生命周期、状态自动计算 |
| **新增目标槽位功能** | [§4.2 目标槽位](#42-目标槽位-targets) | Target、软删除、目标名称字典 |
| **修改客户审核页面** | [§4.8 客户审核系统](#48-客户审核系统-reviews) | ReviewSession、分享链接、反馈链路 |
| **调整交付打包逻辑** | [§4.10 客户交付系统](#410-客户交付系统) | ZIP 打包、脏数据监听、定时任务 |
| **修改大图预览样式** | [§6.4 设计规范](#64-设计规范) | 拍立得风格、Lightbox、比例呼应按钮 |
| **新增 API 接口** | [§3.1 模块化路由架构](#31-模块化路由架构) | 路由注册、APIRouter、路由顺序 |
| **修改数据库模型** | [§7.8 数据库迁移](#78-数据库迁移) | Alembic、迁移脚本、ORM Model |
| **排查图片 404 问题** | [§7.5 存储安全校验](#75-存储安全校验) | 静态文件代理、路径穿越防护、排查清单 |
| **配置前端开发环境** | [§7.7 前端开发服务器配置](#77-前端开发服务器配置规范) | Vite、端口冲突、strictPort |
| **复用标准 UI 组件** | [§7.0 UI 组件复用规范](#70-ui-组件复用规范) | Lightbox、PhotoShuttle、标准组件库 |
| **修改异步任务逻辑** | [§7.4 异步/同步边界](#74-异步同步边界) | BackgroundTasks、run_in_threadpool |
| **排查路由冲突 404** | [§7.6 路由注册规范](#76-路由注册规范) | 路由定义顺序、通配路由、具体路径 |
| **修改 Docker 配置** | [§2.1 Docker 容器化架构](#21-docker-容器化架构) | docker-compose、健康检查、entrypoint |
| **查看枚举定义** | [§8 枚举定义](#8-枚举定义) | ProcessState、PhotoStatus、ProjectStatus |

---

## 🏗️ Core Standards — 核心技术标准

### 技术栈总览

| 层级 | 技术选型 | 版本/说明 |
|------|---------|---------|
| **后端框架** | FastAPI | Python 3.11+, 全异步 |
| **数据库** | PostgreSQL + SQLAlchemy 2.0 | asyncpg 异步驱动 |
| **前端框架** | Vue 3 + TypeScript + Vite | Composition API + `<script setup>` |
| **UI 组件库** | Element Plus | 全局注册 |
| **CSS 框架** | Tailwind CSS v4 | CSS-first 配置，`@theme` 自定义主题 |
| **图片处理** | Pillow | 缩略图生成、EXIF 解析 |
| **容器化** | Docker + Docker Compose | 健康检查、自动迁移 |
| **数据库迁移** | Alembic | 版本化迁移管理 |

### 核心开发铁律

> **⚠️ 纲领性要求 — AI 编程助手核心指令集**  
> 当 AI 接收到开发新功能、修复 Bug 或重构代码的指令时，必须严格遵守以下准则。

#### 🚫 禁止行为

| 禁止项 | 说明 | 违规后果 |
|--------|------|---------|
| **猜测需求** | 1% 不确定必须询问用户 | 无效交付 |
| **打补丁** | 发现逻辑矛盾必须指出，禁止在错误逻辑上打补丁 | 技术债累积 |
| **破坏异步边界** | CPU 密集型任务必须用 BackgroundTasks/run_in_threadpool | 阻塞事件循环 |
| **硬编码路径** | 必须使用环境变量 `NAS_MOUNT_PATH` | 路径穿越风险 |
| **暴露原图路径** | 客户页面仅传递 `thumbnail_path` | 资产泄露 |
| **跳过依赖注入** | 必须通过 `Depends()` 注入 db/user | 代码耦合 |
| **违反路由顺序** | 具体路径在前，通配路由在后 | 404 错误 |
| **擅自引入依赖** | 优先使用标准库和已有依赖 | 依赖膨胀 |

#### ✅ 强制要求

| 要求项 | 实施细节 |
|--------|---------|
| **主动暴露权衡** | 多方案时列出优缺点，等待用户确认 |
| **强制依赖注入** | 所有 Router 函数通过 `Depends()` 注入 db/user |
| **异步边界隔离** | IO 密集型用 `await`，CPU 密集型用 `BackgroundTasks` |
| **路由注册规范** | `APIRouter(prefix="/api/v1/xxx", tags=["xxx"])` + `app.include_router()` |
| **数据模型分离** | ORM Model (`models.py`) + Pydantic Schema (`schemas/`) |
| **API 响应格式** | 操作类返回 `{code, msg, data}`，查询类返回 Schema |
| **软删除优先** | 项目/照片/客户/目标均支持软删除（`deleted_at`） |
| **路径安全校验** | 静态文件代理必须校验 `is_relative_to(NAS_MOUNT)` |

---

## 1. 系统概述

商业摄影项目跟进系统是一套面向摄影工作室的全流程数字化管理平台，覆盖从客户建档、项目创建、照片导入分拣到客户预览交付的完整工作链路。系统 v2.0 采用 **Target 看板模型**取代 v1.0 的 Category 分类体系，引入客户管理、模板系统、设置中心等模块化功能。

**核心业务流程：**

```
客户建档 → 项目创建（模板生成 Targets）→ 照片导入（上传/NAS 扫描）
    ↓
穿梭式分拣（PhotoShuttle）→ 确认原图 → 精修版本管理 → 成片交付
    ↓
客户审核（分享链接）→ 客户反馈 → ZIP 打包 → 客户下载
```

---

## 2. 部署与网络规范

### 2.1 Docker 容器化架构

**启动流程（自动化自愈机制）：**

1. **数据库健康检查**：PostgreSQL 容器启动后执行 `pg_isready` 检测（10s 间隔，5 次重试）
2. **后端依赖等待**：Web 容器通过 `depends_on: service_healthy` 确保数据库完全就绪
3. **自动化迁移**：`entrypoint.sh` 执行 Alembic 迁移（`alembic upgrade head`）+ 种子数据注入
4. **服务启动**：FastAPI 应用启动，执行 lifespan 初始化（幂等设计）
5. **健康检查**：Web 容器通过 `/health` 端点进行健康监控（30s 间隔，10s 超时，3 次重试）

**关键文件：**
- [docker-compose.yml](docker-compose.yml) - 服务编排配置（含健康检查）
- [app/entrypoint.sh](app/entrypoint.sh) - 容器启动脚本（执行 Alembic 迁移）
- [app/alembic/](app/alembic/) - 数据库迁移脚本目录
- [app/alembic.ini](app/alembic.ini) - Alembic 配置文件
- [frontend_admin/Dockerfile](frontend_admin/Dockerfile) - 前端容器化配置（多阶段构建）
- [frontend_admin/nginx.conf](frontend_admin/nginx.conf) - Nginx 生产环境配置

### 2.2 端口规划

| 服务 | 容器端口 | 宿主机端口 | Docker 网络别名 |
|------|---------|-----------|----------------|
| PostgreSQL | 15432 | 5432 | `db` |
| FastAPI 后端 | 8000 | 8000 | `web` |
| Vue3 前端 (Vite 开发) | 15173 | 15173 | — |
| Vue3 前端 (Nginx 生产) | 80 | 15173 | — |

### 2.3 存储路径与 Volume 挂载

| 用途 | 路径 | 权限 | 说明 |
|------|------|------|------|
| 数据库持久化 | `postgres_data:/var/lib/postgresql/data` | rw | **Docker 命名卷**（避免 WSL2 文件锁） |
| NAS 外部存储 | 宿主机 NAS → 容器 `/mnt/nas_data` | **只读 :ro** | 客户原始资产安全保障 |

> **⚠️ 路径硬编码禁令：** 环境变量 `NAS_MOUNT_PATH` 控制 NAS 挂载点，**严禁在代码中硬编码绝对路径**。

---

## 3. 系统架构

### 3.1 模块化路由架构

```
FastAPI App (main.py)
├── /                           → 健康检查（根路径）
├── /health                     → 健康检查端点（容器监控）
├── /storage/{path}             → 静态文件代理（含路径穿越防护）
│
├── Admin 模块（需认证）
│   ├── /api/v1/projects        → projects.py   项目 CRUD & Target 管理 & 项目级照片
│   ├── /api/v1/photos          → photos.py     照片批量操作 & 作品中心 & 精修版本管理
│   ├── /api/v1/projects/*/tags → tags.py       标签 CRUD
│   ├── /api/v1/clients         → clients.py    客户管理
│   ├── /api/v1/system          → system.py     NAS 浏览 & 清理工具 & 系统配置
│   └── /api/v1/system/*        → settings.py   设置中心（模板/用户/图库/标签/字典）
│
├── Guest 模块（无需认证）
│   ├── /api/v1/guest           → guest.py      客户照片预览
│   ├── /api/v1/reviews         → reviews.py    客户审核系统
│   └── /api/v1/deliveries      → deliveries.py 客户交付系统
│
└── 后台服务
    ├── cleanup_service.py      → 归档项目 15 天自动清理
    └── delivery_scheduler.py   → ZIP 打包定时任务（APScheduler，每 5 分钟检查脏数据）
```

> **⚠️ 路由定义顺序铁律（CRITICAL）：**  
> FastAPI 按照路由定义的**物理顺序**进行匹配，第一个匹配成功的路由会被执行。
> 
> **正确顺序：**
> 1. **具体路径路由** → 放在前面（如 `/project/{id}/sessions`）
> 2. **通配路由（路径参数）** → 放在后面（如 `/{token}`）

### 3.2 核心数据流

```
客户建档 → 项目创建（模板生成 Targets）→ 照片导入（上传/NAS 扫描）
    ↓
穿梭式分拣（PhotoShuttle）→ 确认原图 → 精修版本管理 → 成片交付
    ↓
客户审核（分享链接）→ 客户反馈 → ZIP 打包 → 客户下载
```

**照片完整生命周期：**

1. **导入阶段** → `process_state=raw`, `is_confirmed=false`
2. **确认原图** → `is_confirmed=true` (通过 `/confirm-raw` 接口)
3. **精修关联** → 上传精修图时指定 `parent_id`，系统自动分配 `version` 递增
4. **版本迭代** → 同一 `parent_id` 可关联多个精修版本，按 `version DESC` 排序
5. **成片交付** → `process_state=final`，进入作品中心和客户预览
6. **客户审核** → 通过审核系统生成分享链接，客户无需登录即可查看并反馈

### 3.3 数据库 ER 关系

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

---

## 4. 核心功能模块详解

### 4.1 项目管理 (Projects)

**生命周期：** 创建 → 活跃 → 归档（15天清理倒计时）→ 自动清理 / 软删除 → 恢复

**项目状态自动计算（`project_status`）：**

| 条件 | 状态 |
|------|------|
| 无任何照片 | `not_started` |
| 仅有 raw 照片 | `shooting` |
| 有 retouched 或 final 照片 | `retouching` |
| 手动归档 | `completed`（仅手动设置） |

**Display ID 生成规则：**
- 格式：`{客户前缀}{6位补零序号}`，如 `XD000001`
- `serial_number` 在 `projects` 表中按 `client_prefix` 自增
- 客户前缀来自 `clients.prefix`（A-Z 大写，唯一）

### 4.2 目标槽位 (Targets)

Target 是 v2.0 的核心看板单元，取代 v1.0 的 Category 体系。

**分类体系：**

| `category_type` | 含义 | 典型目标 |
|-----------------|------|---------|
| `white` | 白底图 | 正面全身、侧面半身 |
| `scene` | 场景图 | 街拍氛围、室内特写 |

**软删除支持（V6.0 新增）：**

- `deleted_at` 字段：NULL 表示正常，非 NULL 表示已删除
- 删除操作：设置 `deleted_at` 为当前 UTC 时间戳，不物理删除记录
- 查询过滤：所有查询自动添加 `deleted_at IS NULL` 条件
- 恢复机制：可通过清空 `deleted_at` 字段恢复误删的目标

**目标名称数据字典：**

| 级别 | 存储位置 | 管理权限 | 说明 |
|------|---------|---------|------|
| 通用词条 | `system_target_dictionary` 表 | 仅管理员 | 系统级标准名称 |
| 模板专属 | `project_templates.target_dictionary` JSON | 模板编辑者 | 特定模板的专属目标名称 |

### 4.3 照片管理 (Photos)

**双通道入库：**

| 通道 | 方式 | 特点 |
|------|------|------|
| 手动上传 | `multipart/form-data` | 单张上传，适合少量补拍 |
| NAS 扫描 | 异步后台任务 | 批量扫描 NAS 目录，按 `file_hash` 去重 |

**三态处理阶段 (ProcessState)：**

| 阶段 | 含义 |
|------|------|
| `raw` | 原片，刚导入 |
| `retouched` | 精修中 |
| `final` | 成片，可交付 |

**精修版本管理：**
- `parent_id` 指向确认原图（FK → photos.id, ON DELETE SET NULL）
- `version` 整数字段，同一 parent_id 下自动递增（从 1 开始）
- 支持两种来源：上传新文件 或 关联已有照片（`existing_photo_id`）
- 取消确认校验：已关联精修图的原图无法取消确认

**穿梭式分拣：** 通过 `PATCH /api/v1/photos/bulk-update` 接口实现照片在 Target 间的批量移入/移出。

### 4.4 标签系统 (Tags)

- 标签按项目隔离（`project_id` 外键）
- 照片与标签为多对多关系（`photo_tags` 关联表）
- 支持自定义颜色和排序
- 批量标签操作：`bulk-add-tags`、`bulk-remove-tags`

### 4.5 客户管理 (Clients)

- 每个客户拥有唯一的 `prefix`（A-Z 大写），用于生成项目 Display ID
- 支持软删除（`deleted_at` 字段）

### 4.6 设置中心 (Settings)

| 子模块 | 功能 |
|--------|------|
| 基础设置 | 系统级配置管理（外网分享链接域名等） |
| 系统图库 | 上传/管理样片等系统级图片资源 |
| 目标名称字典 | 管理通用目标词条 |
| 项目模板 | 管理内置及自定义项目模板 |
| 标签管理 | 管理全局标签库 |
| 用户管理 | 用户 CRUD、角色分配、项目级权限控制 |

### 4.7 客户预览 (Guest)

- 独立路由模块，**无需认证**
- 仅暴露照片查看接口，自动过滤已删除照片


### 4.8 客户审核系统 (Reviews)

**核心功能：**
- Admin 端生成分享链接，选择特定照片（原图/精修）供客户审核
- 客户通过链接无需登录即可查看照片并提交反馈（确认/修改意见）
- Admin 端查询客户反馈，集成到项目工作台

**数据模型：**
- `ReviewSession`：审核会话，存储 token、过期时间、选中照片 JSON、创建人、作废状态
  - `is_disabled` 布尔字段：作废开关，作废后客户访问返回 403
  - `created_by` 外键：记录创建人（FK → users.id）
- `ReviewFeedback`：客户反馈，记录确认状态和修改意见

**安全机制：**
- Token 使用 UUID4，防止猜测攻击
- 过期时间校验（1-30 天可配置）
- 首次访问自动标记 `is_viewed` 和 `viewed_at`
- 作废机制：管理员可随时作废链接
- **资产保护机制**：
  - 客户审核页面仅传递 `thumbnail_path`，严禁传递 `original_path`
  - 前端严格过滤原图路径，防止通过开发者工具获取
  - Lightbox 组件强制使用缩略图，移除原图回退逻辑

**反馈链路打通：**
- **会话唯一性约束**：每个项目同时只能有一个活跃审核会话（未过期）
- **照片锁定机制**：
  - Photo 表新增 `is_locked` 布尔字段（默认 false）
  - 客户确认精修图或成片时，自动设置 `is_locked=true`
  - 锁定后的照片在 Admin 端显示 🔒 图标，防止误删
- **Admin 端反馈显示**：
  - TargetDetail 组件集成反馈轮询：每 30 秒请求一次反馈接口
  - 照片缩略图叠加层：
    - 红色「客户已确认」标签（右上角）
    - 💬 留言气泡（右下角，hover 显示完整留言）
    - 🔒 锁定图标（左下角）

### 4.9 回收站与自动清理

**软删除机制：**
- 项目、照片、客户、目标槽位（V6.0 新增）均支持软删除（`deleted_at` 时间戳）
- 软删除后可通过 `restore` 接口恢复

**物理删除（Hard Delete）：**
- 删除数据库记录的同时物理删除原图和缩略图文件
- 返回 `deleted`、`files_deleted`、`files_missing`、`errors` 详细统计

**自动清理服务 (`cleanup_service.py`)：**
- 项目归档后开始 15 天倒计时
- 倒计时结束后自动清理关联数据
- 支持通过 `/trigger-cleanup` 手动触发（测试用途）

### 4.10 客户交付系统

**核心功能：**
- 自动打包项目成片为 ZIP 文件，按目标分组
- 脏数据监听机制，成片变化时自动标记需要重建
- 定时任务自动处理脏数据，重新生成 ZIP 包
- 生成分享链接，客户可访问专属页面下载成片

**数据模型：**
- **Project 表扩展**：
  - `zip_path`：ZIP 文件存储路径（相对于 `UPLOAD_DIR`）
  - `zip_status`：打包状态（`pending`/`processing`/`completed`/`failed`）
  - `zip_generated_at`：ZIP 生成时间
- **DeliverySession 表**：
  - `token`：UUID4 分享令牌（唯一索引）
  - `project_id`：关联项目
  - `created_by`：创建人（User ID）
  - `expired_at`：过期时间

**ZIP 打包逻辑：**
- **触发条件**：项目状态为 `completed` 且存在最终交付图
- **文件组织**：按 `target_name` 分组，每个目标创建独立文件夹
- **文件命名规则**：`{display_id}_{target_name}_{version}.{ext}`
- **ZIP 命名规则**：`{机构名称}_{项目名称}_{归档日期}.zip`
- **存储位置**：`{UPLOAD_DIR}/deliveries/{project_id}/delivery.zip`

**脏数据监听机制：**
- **监听范围**：所有 `process_state=final` 的照片增删改操作
- **触发接口**：
  - `POST /api/v1/photos/upload-final`：上传成片
  - `PUT /api/v1/photos/bulk-update`：批量更新照片
  - `DELETE /api/v1/photos/bulk-delete`：批量软删除照片
  - `POST /api/v1/photos/bulk-restore`：批量恢复照片
  - `POST /api/v1/reviews/{token}/feedback`：客户反馈（确认成片）
- **标记逻辑**：调用 `mark_zip_dirty(project_id)` 将 `zip_status` 设置为 `pending`

**定时任务：**
- **调度器**：APScheduler（BackgroundScheduler）
- **执行频率**：每 5 分钟执行一次
- **任务逻辑**：
  1. 查询所有 `project_status=completed` 且 `zip_status=pending/failed` 的项目
  2. 逐个调用 `generate_delivery_zip(project_id)` 重建 ZIP
  3. 更新 `zip_status` 为 `completed` 或 `failed`
  4. 记录 `zip_generated_at` 时间戳
- **启动集成**：在 `main.py` 的 `lifespan` 中启动调度器

**安全机制：**
- Token 使用 UUID4，防止猜测攻击
- 过期时间校验（1-30 天可配置）
- ZIP 状态校验（仅 `completed` 状态可下载）
- 项目完成状态校验（仅 `completed` 项目可创建分享）

---

## 5. 后端工程目录结构

```text
/app
├── main.py                 # FastAPI 应用入口、生命周期、CORS、路由注册、静态文件代理、健康检查
├── database.py             # SQLAlchemy 异步引擎 & AsyncSessionLocal
├── models.py               # 全部 ORM 模型 & 枚举定义（单文件）
├── deps.py                 # 依赖注入：get_db、CurrentUser
├── init_db.py              # 数据库初始化 & 种子数据（管理员、内置模板）
├── cleanup_service.py      # 归档项目自动清理后台服务
├── alembic.ini             # Alembic 配置文件
├── alembic/
│   ├── env.py              # Alembic 环境配置（异步引擎支持）
│   └── versions/           # 数据库迁移脚本目录
│       ├── 733dc07bf814_add_soft_delete_to_project_targets.py
│       └── ...
├── logic/
│   └── status_manager.py   # 项目/目标状态自动计算逻辑封装
├── routers/
│   ├── projects.py         # 项目 CRUD + Target CRUD + 项目级照片接口
│   ├── photos.py           # 照片批量操作（上传/扫描/更新/删除/标签）
│   ├── tags.py             # 项目标签 CRUD
│   ├── clients.py          # 客户管理 CRUD
│   ├── system.py           # NAS 目录浏览 & 清理触发
│   ├── settings.py         # 设置中心（模板/用户/图库）
│   ├── guest.py            # 客户预览接口（无认证）
│   ├── reviews.py          # 客户审核系统（分享链接/反馈）
│   ├── deliveries.py       # 客户交付系统（ZIP 打包/分享）
│   ├── auth.py             # 认证接口（登录/获取当前用户/修改密码）
│   └── users.py            # 用户管理 CRUD
├── schemas/
│   ├── __init__.py
│   ├── project_schema.py   # 项目相关 Schema
│   ├── photo_schema.py     # 照片相关 Schema
│   ├── target_schema.py    # 目标槽位 Schema
│   ├── tag_schema.py       # 标签 Schema
│   ├── client_schema.py    # 客户 Schema
│   └── settings_schema.py  # 设置中心 Schema（模板/用户/图库）
└── services/
    └── delivery_zip_service.py  # 交付 ZIP 打包服务
```

---

## 6. 前端工程架构

### 6.1 技术栈

| 技术 | 版本/说明 |
|------|---------|
| Vue 3 | Composition API + `<script setup>` |
| TypeScript | 类型安全 |
| Vite | 开发服务器 + 构建工具 |
| Element Plus | 全局注册（`app.use(ElementPlus)`） |
| Tailwind CSS v4 | CSS-first 配置，`@theme` 自定义主题 |
| Vue Router 4 | `createWebHistory` 模式 |

### 6.2 目录结构

```text
/frontend_admin
├── index.html
├── package.json            # 脚本配置（dev 命令自动清理 15173 端口）
├── vite.config.ts          # Vite 配置（API 代理 /api → localhost:8000，strictPort: true）
├── Dockerfile              # 前端容器化配置（多阶段构建：Node.js 构建 + Nginx 运行）
├── nginx.conf              # Nginx 生产环境配置（SPA 路由支持、API 代理、静态资源缓存）
├── src/
│   ├── main.ts             # 应用入口
│   ├── App.vue             # 根组件
│   ├── assets/main.css     # Tailwind 入口 + 全局主题
│   ├── router/index.ts     # 路由定义
│   ├── components/
│   │   ├── Layout.vue      # 主布局（左侧 240px 深色侧边栏 + 右侧内容区）
│   │   ├── ProjectCard.vue # 项目卡片（统计 + 进度 + project_status 徽章）
│   │   ├── TargetCard.vue  # 目标槽位卡片（5态状态）
│   │   ├── TargetDetail.vue# 子项目工作台（三区段：确认原图/精修/完成）
│   │   ├── ConfirmedRawSection.vue # 确认原图区段
│   │   ├── RetouchedSection.vue    # 精修图区段（版本管理）
│   │   ├── FinalSection.vue        # 完成图区段
│   │   ├── PhotoShuttle.vue   # 照片穿梭分拣台（8列网格，每页40张）
│   │   ├── ProjectDelivery.vue# 最终交付图视图（按白图/场景图分组）
│   │   ├── LineageBoard.vue# 血缘溯源视图（parent_id 链路）
│   │   ├── GlobalStatusMenu.vue # 项目状态菜单组件（可复用）
│   │   └── ShareReviewModal.vue # 审核分享弹窗（左侧分级菜单 + 右侧预览）
│   └── views/
│       ├── Dashboard.vue       # 项目工作台
│       ├── ProjectCenter.vue   # 项目中心
│       ├── PortfolioCenter.vue # 作品中心
│       ├── ProjectDetail.vue   # 项目详情 & 分拣台
│       ├── ImportCenter.vue    # 导入中心
│       ├── ClientCenter.vue    # 客户管理
│       ├── AdminUserPanel.vue  # 独立用户管理入口
│       ├── SettingsBasic.vue   # 基础设置（外网分享链接配置）
│       ├── SettingsImages.vue  # 系统图库
│       ├── SettingsTemplates.vue # 项目模板
│       ├── SettingsTags.vue    # 标签管理
│       ├── SettingsUsers.vue   # 设置中心用户管理
│       ├── ReviewPage.vue      # 客户审核页面（/share/{token}，无需登录）
│       └── DeliveryPage.vue    # 客户交付页面（/delivery/{token}，无需登录）
```

### 6.3 路由规划

| 路径 | 名称 | 组件 | 说明 |
|------|------|------|------|
| `/` | Dashboard | Dashboard.vue | 项目工作台，网格展示项目卡片 |
| `/projects` | ProjectCenter | ProjectCenter.vue | 项目中心，表格筛选、归档、回收站 |
| `/portfolio` | PortfolioCenter | PortfolioCenter.vue | 作品中心，瀑布流展示跨项目成片 |
| `/project/:id` | ProjectDetail | ProjectDetail.vue | 项目详情：目标看板 + 照片溯源双视图 |
| `/project/:id/import` | ImportCenter | ImportCenter.vue | 导入中心（上传/NAS/标签/底片池/穿梭分拣） |
| `/clients` | ClientCenter | ClientCenter.vue | 客户管理 |
| `/admin/users` | AdminUserPanel | AdminUserPanel.vue | 管理员独立用户管理入口 |
| `/settings` | — | — | 重定向至 `/settings/basic` |
| `/settings/basic` | SettingsBasic | SettingsBasic.vue | 基础设置（外网分享链接配置） |
| `/settings/images` | SettingsImages | SettingsImages.vue | 系统图库 |
| `/settings/templates` | SettingsTemplates | SettingsTemplates.vue | 项目模板 |
| `/settings/tags` | SettingsTags | SettingsTags.vue | 全局标签 |
| `/settings/users` | SettingsUsers | SettingsUsers.vue | 设置中心用户管理 |
| `/share/:token` | ReviewPage | ReviewPage.vue | 客户审核页面（无需登录，公开访问） |
| `/delivery/:token` | DeliveryPage | DeliveryPage.vue | 客户交付页面（无需登录，公开访问） |

> **遗留说明：** `SettingsCenter.vue` 当前未挂载到路由，且包含旧接口路径。新增设置页功能时应使用上表中的拆分页面，不再恢复 `SettingsCenter.vue`。

### 6.4 设计规范

**设计风格：** 扁平化卡片式，主色 `#3498db`，辅色 `#2ecc71`

**Element Plus 核心组件：** `el-upload`、`el-tabs`、`el-image`、`el-pagination`、`el-empty`、`el-button`、`el-dialog`

**响应式分拣：** 前端调用 `bulk-update` 后直接修改本地数据，Vue 响应式驱动 UI 自动更新，无需重新请求

#### 拍立得画廊风格规范

**适用组件：** `ProjectDelivery.vue`（最终交付图）、`PortfolioCenter.vue`（作品中心）

**缩略图卡片设计：**
- **对齐方式：** 所有文字信息居中对齐（`text-align: center`）
- **信息层级（四行布局）：**
  - 第一行：子项目名称 / 目标名称，纯黑特粗 `font-weight: 800; color: #000; font-size: 18px`
  - 第二行：项目编号（如 `#007`），中灰色 `color: #6b7280; font-size: 14px; font-family: 'Courier New'`
  - 第三行：图片原始文件名（`original_filename`），深灰色 `color: #374151; font-size: 11-12px`
  - 第四行：所属项目名称，浅灰色 `color: #9ca3af; font-size: 10-11px`
- **视觉优化：** 卡片背景纯白，圆角 `14-16px`，阴影 `0 2px 10px rgba(0,0,0,0.08)`，hover 时上浮 `-3px` 并加深阴影

**大图预览（Lightbox）设计：**
- **拍立得相框效果：**
  - 白色容器包裹图片，模拟相纸效果（`background: white; padding: 16px 16px 0 16px; border-radius: 8px`）
  - 底部加宽白边区域（`padding: 20px 16px 24px`），展示四行信息（子项目、文件名、编号、项目名），居中对齐
  - 相框边框 `border: 1px solid rgba(0,0,0,0.05)`（Ultra-Minimalist 2.0 风格）
- **按钮布局（视线聚焦优化 + 比例呼应设计）：**
  - **下载按钮比例呼应**：
    - 形状：长方形，宽高比与主照片画框比例完全一致（通过 JS 动态计算 `img.naturalWidth / img.naturalHeight`）
    - 尺寸：高度固定 `58px`（桌面端）/ `48px`（移动端），宽度根据比例自动计算
    - 定位：外置吸附于相框右上角外边缘，对齐图片上边缘（`position: absolute; top: 16px; left: 100%`）
    - 视觉：纯白色背景 `#ffffff`，灰色图标 `#6b7280`，极细浅灰描边 `1px solid rgba(0,0,0,0.08)`，圆角 `8px`
  - **导航按钮护航式布局**：左右箭头按钮贴近图片容器（`left: -70px` / `right: -70px`），半透明白底毛玻璃效果
  - **关闭按钮**：固定在屏幕右上角（`position: fixed; top: 20px; right: 20px`）

**环境隔离：**
- **内部工作台**（ProjectDelivery、PortfolioCenter）：默认显示缩略图，点击放大镜按钮按需加载原图，支持下载原图
- **外部客户页**（ReviewPage、DeliveryPage）：仅显示缩略图，严禁暴露原图路径，保护资产安全

---

## 7. 开发规范

### 7.0 UI 组件复用规范

#### 标准组件库

为避免重复开发和维护成本，以下组件已提取为标准件，后续开发**必须优先复用**：

| 组件名称 | 标准实现位置 | 功能描述 | 复用场景 |
|---------|------------|---------|---------|
| **大图查看器（Lightbox）** | `PortfolioCenter.vue` | 拍立得风格大图预览，支持原图/缩略图切换、下载、键盘导航 | 所有需要查看大图的场景 |
| **照片分拣器（PhotoShuttle）** | `PhotoShuttle.vue` | 左右分栏穿梭式分拣，支持批量移入/移出、状态修改 | 照片批量操作场景 |
| **照片下载器** | `usePhotoDownload.ts` | 统一的照片下载逻辑（单张/批量/ZIP） | 所有下载场景 |

**禁止行为：**
- ❌ 禁止单独开发新的大图查看器
- ❌ 禁止修改标准件的核心样式（相框、按钮布局）
- ❌ 禁止在客户页面暴露原图路径

### 7.1 API 响应格式

- **操作类接口**（创建/更新/删除/归档）：统一返回 `{ "code": 200, "msg": "...", "data": ... | null }`
- **查询/列表类接口**：直接返回结构化 Pydantic Schema
- **错误**：通过 `HTTPException` 抛出，FastAPI 自动格式化

### 7.2 数据模型分离

| 层 | 目录 | 职责 |
|----|------|------|
| ORM Model | `models.py` | 数据库表结构、外键关系、枚举定义 |
| Pydantic Schema | `schemas/` | API 输入校验 & 输出序列化 |

**命名规则：** `XxxCreate`（创建请求）、`XxxUpdate`（更新请求）、`XxxResponse`（单条响应）、`XxxListResponse`（列表响应）。所有响应 Schema 必须配置 `model_config = {"from_attributes": True}`。

### 7.3 依赖注入

所有 Router 函数通过 `fastapi.Depends()` 注入：
- `db: AsyncSession` — 数据库会话
- `current_user: User` — 当前认证用户（Guest 模块除外）

**严禁在函数体内直接实例化数据库连接或认证逻辑。**

### 7.4 异步/同步边界

| 操作类型 | 处理方式 |
|---------|---------|
| IO 密集型（数据库） | `await db.execute(...)` 全异步 |
| CPU 密集型（缩略图生成） | `BackgroundTasks` 或 `run_in_threadpool` |
| NAS 批量扫描 | `BackgroundTasks` 异步执行，通过 `task_id` 轮询进度 |

### 7.5 存储安全校验

**静态文件代理路径穿越防护：**
- 白名单目录：仅允许 `/mnt/nas_data` 下的文件
- 使用 `Path.resolve()` + `is_relative_to()` 校验
- 非白名单路径返回 403 Forbidden

**NAS 扫描路径安全：**
- 扫描路径必须在 NAS 挂载点范围内
- `file_hash` 去重，同项目内不重复入库

**图片路径 404 问题排查清单：**

当图片无法加载时，按以下步骤排查：

1. **验证后端静态文件服务**
   ```bash
   curl -I http://localhost:8000/storage/1/raw/example.jpg
   # 预期：200 OK（文件存在）或 404 Not Found（文件不存在）
   ```

2. **验证前端代理配置**
   ```bash
   curl -I http://localhost:15173/storage/1/raw/example.jpg
   # 预期：与后端直连结果一致
   ```

3. **检查数据库路径与实际文件一致性**
   ```sql
   SELECT id, original_path, thumbnail_path 
   FROM photos 
   WHERE project_id = 1 
   LIMIT 5;
   ```

4. **检查 Docker 卷挂载配置**
   ```yaml
   services:
     web:
       volumes:
         - ./nas_mock_data:/mnt/nas_data
   ```

5. **前端图片路径格式**
   ```typescript
   // ✅ 正确：相对路径，自动代理到后端
   const imageUrl = `/storage/${photo.original_path}`
   
   // ❌ 错误：硬编码端口或域名
   const imageUrl = `http://localhost:8000/storage/${photo.original_path}`
   ```

### 7.6 路由注册规范

所有 Router 文件遵循 `APIRouter(prefix="/api/v1/xxx", tags=["xxx"])` 格式，在 `main.py` 中统一通过 `app.include_router()` 注册。

**路由定义顺序规则（CRITICAL）：**

FastAPI 按照路由定义的**物理顺序**进行匹配，第一个匹配成功的路由会被执行。因此必须遵循以下顺序：

1. **具体路径路由** → 放在前面
2. **通配路由（路径参数）** → 放在后面

**错误示例（会导致 404）：**
```python
# ❌ 错误：通配路由在前，会拦截所有请求
@router.get("/{token}")  # 通配路由
async def get_review_by_token(token: str): ...

@router.get("/project/{project_id}/sessions")  # 具体路由
async def get_project_sessions(project_id: int): ...
```

**正确示例：**
```python
# ✅ 正确：具体路由在前
@router.get("/project/{project_id}/sessions")  # 具体路由
async def get_project_sessions(project_id: int): ...

@router.get("/{token}")  # 通配路由
async def get_review_by_token(token: str): ...
```

### 7.7 前端开发服务器配置规范

#### 端口冲突防护（CRITICAL）

为避免多进程冲突导致端口漂移（15173 → 15174 → 15175...），**必须配置以下两项**：

**1. package.json 自动清理端口**
```json
{
  "scripts": {
    "dev": "npx kill-port 15173 && vite"
  }
}
```

**2. vite.config.ts 严格端口模式**
```typescript
export default defineConfig({
  server: {
    port: 15173,
    strictPort: true,  // 防止端口被占用时自动跳转到 15174
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/storage': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
```

### 7.8 数据库迁移

**使用 Alembic 进行数据库迁移（V6.0 新增）：**

```bash
# 1. 生成迁移脚本（自动检测模型变更）
docker-compose exec web alembic revision --autogenerate -m "描述变更内容"

# 2. 执行迁移（升级到最新版本）
docker-compose exec web alembic upgrade head

# 3. 回滚迁移（降级到上一个版本）
docker-compose exec web alembic downgrade -1

# 4. 查看迁移历史
docker-compose exec web alembic history

# 5. 查看当前版本
docker-compose exec web alembic current
```

**迁移脚本位置：** `app/alembic/versions/`

**自动迁移集成：** 容器启动时 `entrypoint.sh` 自动执行 `alembic upgrade head`

### 7.9 自动化执行规范

**前端组件更新后：**
```bash
npx kill-port 15173
cd frontend_admin && npm run dev
```

**数据库模型修改后：**
```bash
# 方法一：使用 Alembic 迁移（推荐）
docker-compose exec web alembic revision --autogenerate -m "描述"
docker-compose exec web alembic upgrade head
docker-compose restart web

# 方法二：使用快捷脚本（推荐）
restart_with_db.bat  # 自动清理端口 + 重置数据库 + 重启服务
```

**测试策略：**
- **默认：不主动测试服务**，除非用户明确提出问题或要求验证
- 修改完成后直接报告完成状态，由用户自行验证
- 如果用户报告问题，再进行排查和修复

---

## 8. 枚举定义

### ProcessState（照片处理阶段）

| 值 | 含义 |
|----|------|
| `raw` | 原片，刚导入 |
| `retouched` | 精修中 |
| `final` | 成片，可交付 |

### PhotoStatus（照片状态）

| 值 | 含义 |
|----|------|
| `pending` | 待选片 |
| `selected` | 已选片 |
| `deleted` | 回收站 |

### ProjectStatus（项目状态）

| 值 | 含义 |
|----|------|
| `not_started` | 未开始 |
| `shooting` | 拍摄中 |
| `retouching` | 精修中 |
| `client_review` | 客户审核中 |
| `completed` | 已完成 |

### TargetStatus（目标槽位状态）

| 值 | 含义 |
|----|------|
| `not_started` | 未开始 |
| `shooting` | 拍摄中 |
| `retouching` | 精修中 |
| `client_review` | 客户审核中 |
| `completed` | 已完成 |

### CategoryType（目标分类）

| 值 | 含义 |
|----|------|
| `white` | 白底图 |
| `scene` | 场景图 |

### ZipStatus（ZIP 打包状态）

| 值 | 含义 |
|----|------|
| `pending` | 待打包 |
| `processing` | 打包中 |
| `completed` | 已完成 |
| `failed` | 打包失败 |

---

## 9. 变更记录

### V6.0 (2026-05-09)

**核心变更：**
1. **数据库迁移系统**：完整配置 Alembic，支持版本化迁移管理
2. **ProjectTarget 软删除**：添加 `deleted_at` 字段，删除操作改为软删除
3. **健康检查端点**：新增 `/health` 端点，支持容器健康监控
4. **前端容器化**：提供 Dockerfile 和 nginx 配置，支持生产环境部署
5. **环境变量文档**：完善 `.env.template`，包含所有必需变量说明
6. **查询逻辑优化**：所有 ProjectTarget 查询自动过滤已软删除记录

**影响范围：**
- 目标列表查询
- 项目统计（目标计数、白图/场景图统计）
- 字典词条使用状态检查
- 照片导入的路径自动关联
- 最终交付图下载
- 作品中心筛选项

### V5.0 (2026-05-08)

**核心变更：**
1. **客户交付系统**：ZIP 打包、脏数据监听、定时任务
2. **分享链接管理**：审核会话历史、作废/恢复机制
3. **外网链接配置**：支持配置外网分享域名

### V4.6 (2026-05-07)

**核心变更：**
1. **UI 组件复用规范**：标准化 Lightbox、PhotoShuttle 组件
2. **资产保护机制**：客户页面严禁暴露原图路径
3. **环境隔离**：内部工作台支持原图查看，外部客户页仅显示缩略图

### V4.5 (2026-05-06)

**核心变更：**
1. **客户审核系统**：分享链接、客户反馈、照片锁定机制
2. **反馈链路打通**：Admin 端实时显示客户反馈

### V4.0 (2026-05-05)

**核心变更：**
1. **精修版本管理**：parent_id 链路、version 递增
2. **确认原图机制**：is_confirmed 字段、取消确认校验

### V3.0 (2026-05-04)

**核心变更：**
1. **Target 看板模型**：取代 Category 分类体系
2. **目标名称数据字典**：通用词条 + 模板专属词条
3. **项目模板系统**：内置模板、自定义模板

### V2.0 (2026-05-03)

**核心变更：**
1. **客户管理模块**：客户建档、prefix 生成 Display ID
2. **设置中心**：系统图库、全局标签、用户管理

### V1.0 (2026-05-01)

**初始版本：**
1. 项目管理基础功能
2. 照片上传/NAS 扫描
3. 照片分拣（Category 分类体系）

---

## 📚 附录：快速排查清单

### 数据不稳定问题

```bash
# 快速修复（推荐）
restart_dev.bat          # 仅重启服务（保留数据）
restart_with_db.bat      # 重启服务 + 重置数据库（清空数据）
```

### 图片路径 404 问题

1. 验证后端静态文件服务：`curl -I http://localhost:8000/storage/1/raw/example.jpg`
2. 验证前端代理配置：`curl -I http://localhost:15173/storage/1/raw/example.jpg`
3. 检查数据库路径与实际文件一致性
4. 检查 Docker 卷挂载配置

### 路由冲突 404 问题

1. 检查路由定义顺序（具体路径在前，通配路由在后）
2. 验证路由前缀是否正确
3. 确认前端请求路径与后端路由前缀一致

---

**文档版本：** V6.0  
**生成日期：** 2026-05-09  
**维护者：** 开发团队

