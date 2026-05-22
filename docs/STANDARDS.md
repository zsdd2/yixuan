# 开发规范分类手册

最后更新：2026-05-21

本文件是 `kf01.md` 的分类版，目标是让开发者按任务快速定位规范，不再每次通读所有历史文档。

## 1. 开发前检查

| 检查项 | 必须动作 |
| --- | --- |
| 需求是否明确 | 不明确时先确认，不在业务逻辑上猜测 |
| 涉及哪个页面 | 查 `PAGE_BUSINESS_FLOW.md` |
| 涉及哪个接口 | 查 `API_NAVIGATION.md` 与 `API_REGISTRY.md` |
| 涉及哪个模型/枚举 | 查 `ARCHITECTURE.md` 与 `app/models.py` |
| 是否影响客户外链 | 检查是否暴露原图路径、token 权限、过期状态 |
| 是否影响数据库 | 新增 Alembic 迁移并验证 `alembic current` |

## 2. 后端规范

### 2.1 路由

- 所有业务路由使用 `APIRouter(prefix="/api/v1/xxx", tags=["xxx"])`。
- 具体路由必须写在通配路由前，例如 `/project/{project_id}/sessions` 必须早于 `/{token}`。
- 认证后台接口必须通过 `Depends(get_current_user)` 或对应权限依赖获取用户。
- 数据库会话必须通过 `Depends(get_db)` 注入。

### 2.2 异步边界

- 图片处理、RAW 解析、ZIP 打包、批量扫描等 CPU 或磁盘重任务不能直接阻塞 async 路由。
- 使用 `BackgroundTasks`、`run_in_threadpool` 或服务层调度器处理重任务。
- 长任务必须有状态查询接口或明确的后台状态字段。

### 2.3 数据模型

- ORM 模型集中在 `app/models.py`。
- 入参和响应模型集中在 `app/schemas/`。
- 修改枚举值必须同时处理：
  - `app/models.py`
  - Alembic enum 迁移
  - 前端状态映射
  - `API_REGISTRY.md`

### 2.4 文件与路径安全

- NAS 根路径来自 `NAS_MOUNT_PATH`，禁止硬编码宿主机路径。
- `/storage/{file_path}` 只允许访问 NAS 根目录下文件。
- 客户审核页面、交付页面默认只暴露必要展示资源；审核页严禁返回 `original_path`。

## 3. 前端规范

### 3.1 页面入口

- 受保护后台页面必须在 `frontend_admin/src/router/index.ts` 设置 `requiresAuth: true`。
- 公开 token 页面仅限：
  - `/share/:token`
  - `/delivery/:token`
- 管理员页面必须设置角色限制。

### 3.2 API 调用

- 统一使用 `frontend_admin/src/api/request.ts`。
- 登录接口固定为 `/api/v1/auth/login`。
- 不再新增 `/api/v1/system/auth/*`、`/api/v1/system/users/*` 这类旧路径。
- 公开下载可以使用 `fetch`，但必须明确 token 路径和错误处理。

### 3.3 标准组件复用

| 能力 | 标准入口 |
| --- | --- |
| 目标详情三段工作台 | `components/TargetDetail.vue` |
| 照片分拣 | `components/PhotoShuttle.vue` |
| 原图确认 | `components/ConfirmedRawSection.vue` |
| 精修版本 | `components/RetouchedSection.vue` |
| 成片交付 | `components/FinalSection.vue`、`components/ProjectDelivery.vue` |
| 审核分享 | `components/ShareReviewModal.vue` |
| 交付分享 | `components/ShareDeliveryModal.vue` |
| 下载照片 | `composables/usePhotoDownload.ts` |

## 4. 业务状态规范

### 4.1 项目状态

当前后端 `ProjectStatus` 包含：

- `not_started`
- `shooting`
- `retouching`
- `client_review`
- `completed`
- `archived`

状态自动计算入口：`app/logic/status_manager.py`。

### 4.2 照片处理状态

照片主流程：

`raw` 原图导入 -> `is_confirmed=true` 确认原图 -> `retouched` 精修版本 -> `final` 成片交付。

### 4.3 目标状态

目标槽位按 `ProjectTarget` 管理，支持软删除。目标卡片、详情页、分拣器都必须过滤已删除目标。

## 5. 文档同步规范

| 改动类型 | 必须同步 |
| --- | --- |
| 新增/修改接口 | `API_REGISTRY.md`、`docs/API_NAVIGATION.md` |
| 新增/修改页面 | `docs/PAGE_BUSINESS_FLOW.md` |
| 新增通用开发规则 | `kf01.md`、`docs/STANDARDS.md` |
| 修改架构/模型/状态机 | `ARCHITECTURE.md` |
| 修复重大线上问题 | 新增或更新审计/修复记录 |

## 6. 验证规范

后端：

```powershell
python -m compileall app
docker compose exec -T web alembic current
Invoke-RestMethod http://localhost:8000/health
```

前端：

```powershell
cd frontend_admin
npm run build
```

本地联调：

```powershell
http://localhost:15173
admin / adminadmin
```

