# API 导航索引

最后更新：2026-05-21

本文件是 `API_REGISTRY.md` 的快速入口。完整字段、请求体、响应体仍以根目录 `API_REGISTRY.md` 为准。

## 1. 基础规则

- 后端入口：`http://localhost:8000`
- 前端开发代理：`http://localhost:15173`
- 登录接口：`POST /api/v1/auth/login`
- 当前超级管理员：`admin / adminadmin`
- Token：`Authorization: Bearer <token>`

## 2. 模块分组

| 模块 | 前缀 | 路由文件 | 主要页面 |
| --- | --- | --- | --- |
| 认证 | `/api/v1/auth` | `app/routers/auth.py` | 登录、个人中心 |
| 用户管理 | `/api/v1/users` | `app/routers/users.py` | `/admin/users` |
| 项目 | `/api/v1/projects` | `app/routers/projects.py` | 工作台、项目中心、项目详情 |
| 照片 | `/api/v1/photos` | `app/routers/photos.py` | 导入中心、目标详情、作品中心 |
| 客户 | `/api/v1/clients` | `app/routers/clients.py` | 客户中心 |
| 标签 | `/api/v1/projects/{id}/tags` | `app/routers/tags.py` | 导入中心、标签操作 |
| 系统配置/NAS | `/api/v1/system` | `app/routers/system.py` | 基础设置、NAS 选择 |
| 设置中心 | `/api/v1/settings` | `app/routers/settings.py` | 设置中心 |
| 审核 | `/api/v1/reviews` | `app/routers/reviews.py` | 分享审核、客户审核页 |
| 交付 | `/api/v1/deliveries` | `app/routers/deliveries.py` | 交付分享、客户下载页 |
| 公开预览 | `/api/v1/guest` | `app/routers/guest.py` | 历史客户预览 |

### 子项目场景图与交付链路

- 场景子项目参考图：`GET/POST /api/v1/projects/{project_id}/targets/{target_id}/references`
- 参考图类型：`scene_goal` 为场景目标图，可多张并存，不做版本迭代；`empty_scene` 为场景空场景，每次选择会生成新版本，并把旧版本标记为非当前。
- 精修图分类字段：`photos.retouch_quality`，取值为 `generated`（生成图）、`generated_4k`（4K生成图）、`high_res`（高清图）。
- 精修迭代批次字段：`photos.retouch_batch_id`，同一次多图精修上传共用一个批次号，用于详情页把当次迭代图片合并展示。
- 最终图上传：`POST /api/v1/photos/upload-final`，必须关联一张已确认精修图，链路为 `最终图 -> 精修图 -> 原图`。
- 精修图直转完成图：`POST /api/v1/photos/{photo_id}/promote-final`，从精修图生成新的完成图记录，不修改原精修图。
- 目标卡片样图：`GET /api/v1/projects/{id}/targets` 的 `sample_path` 优先返回手动样图；为空时自动回退最新完成图、精修图、原图、场景目标图。
- 客户审核页只负责确认和反馈，不再把精修图自动转换为最终图。
- 修改示意图：`POST /api/v1/reviews/{token}/feedback` 可提交 `annotation_image`（base64 data URL），后端保存到 `review_annotations/{session_id}`，反馈返回 `annotation_path`。

### 素材中心

- 前端入口：`/materials`
- 上传素材：复用 `POST /api/v1/settings/images/upload`，`category` 使用 `一级分类/二级分类`，`tags` 保存附加标签。
- 批量分类：`PATCH /api/v1/settings/images/bulk-update`，按素材 ID 批量更新 `category` 和 `tags`。
- 分类配置：`GET/PUT /api/v1/system/configs/material_categories`，在基础设置页面维护 JSON 分类树。

## 3. 路由顺序风险清单

交付分享创建规则：`POST /api/v1/deliveries/create` 要求项目状态为 `completed` 且有最终交付图；不再要求项目必须归档。

这些模块存在 token 或通配路径，新增接口时必须把具体路径放在前面：

- `app/routers/reviews.py`
- `app/routers/deliveries.py`
- 任何新增 `/{token}`、`/{id}`、`/{slug}` 的模块

正确示例：

```python
@router.get("/project/{project_id}/sessions")
async def list_sessions(...):
    ...

@router.get("/{token}")
async def get_public_page(...):
    ...
```

## 4. 废弃/遗留路径

下列路径不应新增调用：

- `/api/v1/system/auth/login`
- `/api/v1/system/users`
- `/api/v1/system/images`

如果发现浏览器请求这些路径，优先检查：

1. 前端是否跑旧进程。
2. 浏览器是否缓存旧 bundle。
3. 遗留页面 `SettingsCenter.vue` 是否被重新挂载。
4. API 文档或调用代码是否未同步。

## 5. 快速验证命令

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/v1/auth/login -ContentType 'application/json' -Body '{"username":"admin","password":"adminadmin"}'
```
