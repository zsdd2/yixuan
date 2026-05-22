# ArtSelect V5.0 开发者指南

> **最后更新：** 2026-04-24  
> **版本：** 5.0  
> **维护者：** 开发团队

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈](#2-技术栈)
3. [存储架构](#3-存储架构)
4. [开发环境配置](#4-开发环境配置)
5. [前端代理规则](#5-前端代理规则)
6. [图片处理逻辑](#6-图片处理逻辑)
7. [API 接口规范](#7-api-接口规范)
8. [数据库模型](#8-数据库模型)
9. [常见问题排查](#9-常见问题排查)
10. [部署指南](#10-部署指南)

---

## 1. 项目概述

**ArtSelect** 是一个商业摄影项目管理系统，专为摄影工作室设计，支持：

- 项目全生命周期管理（创建、拍摄、精修、交付）
- 照片三阶段工作流（原图 → 精修 → 完成图）
- 客户审核与反馈系统
- 自动 ZIP 打包与交付分享
- 作品中心与项目归档

**核心业务流程：**

```
创建项目 → 导入照片 → 确认原图 → 上传精修图 → 客户审核 → 标记完成图 → 归档交付
```

---

## 2. 技术栈

### 后端

| 技术 | 版本 | 用途 |
|------|------|------|
| **Python** | 3.11+ | 主语言 |
| **FastAPI** | 0.115+ | Web 框架 |
| **SQLAlchemy** | 2.0+ | ORM（异步） |
| **PostgreSQL** | 15+ | 数据库 |
| **Pydantic** | 2.0+ | 数据校验 |
| **Pillow** | 10.0+ | 图片处理 |
| **APScheduler** | 3.10+ | 定时任务 |
| **Docker** | 24.0+ | 容器化 |

### 前端

| 技术 | 版本 | 用途 |
|------|------|------|
| **Vue 3** | 3.4+ | 前端框架 |
| **TypeScript** | 5.0+ | 类型系统 |
| **Vite** | 5.0+ | 构建工具 |
| **Element Plus** | 2.8+ | UI 组件库 |
| **Tailwind CSS** | 3.4+ | 样式框架 |
| **Vue Router** | 4.0+ | 路由管理 |

---

## 3. 存储架构

### 3.1 目录结构

```
nas_mock_data/                    # NAS 挂载点（模拟）
├── {project_id}/                 # 项目目录（按项目 ID）
│   ├── raw/                      # 原图目录
│   │   └── {file_hash}.jpg       # 原图文件（SHA256 命名）
│   ├── thumb/                    # 缩略图目录
│   │   └── {file_hash}.webp      # 缩略图（800px 最大边）
│   └── retouched/                # 精修图目录（可选）
│       └── {file_hash}.jpg
├── deliveries/                   # 交付 ZIP 存储
│   └── {project_id}/
│       └── delivery.zip          # 自动生成的交付包
└── system_images/                # 系统图库
    ├── sample/                   # 样片
    └── template/                 # 模板图
```

### 3.2 路径存储规范

**数据库存储：** 所有文件路径必须存储为 **NAS 相对路径**，禁止存储绝对路径。

```python
# ✅ 正确：相对路径
original_path = "1/raw/abc123.jpg"
thumbnail_path = "1/thumb/abc123.webp"

# ❌ 错误：绝对路径
original_path = "/mnt/nas_data/1/raw/abc123.jpg"  # 禁止
original_path = "F:\\nas_mock_data\\1\\raw\\abc123.jpg"  # 禁止
```

**原因：** 避免 Windows 驱动器号导致 403 错误，保证跨平台兼容性。

### 3.3 文件命名规则

| 文件类型 | 命名规则 | 示例 |
|---------|---------|------|
| **原图** | `{SHA256}.{ext}` | `abc123def456.jpg` |
| **缩略图** | `{SHA256}.webp` | `abc123def456.webp` |
| **交付 ZIP** | `{机构名称}_{项目名称}_{归档日期}.zip` | `XX摄影_春季白图_20260420.zip` |

**文件哈希计算：**

```python
import hashlib

def compute_file_hash(file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()[:32]
```

---

## 4. 开发环境配置

### 4.1 环境变量

创建 `.env` 文件（项目根目录）：

```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/photo_studio

# NAS 挂载路径
NAS_MOUNT_PATH=/mnt/nas_data

# JWT 密钥（生产环境必须修改）
SECRET_KEY=your-secret-key-here

# 日志级别
LOG_LEVEL=INFO
```

### 4.2 启动服务

**后端（Docker）：**

```bash
# 启动所有服务（数据库 + 后端）
docker-compose up -d

# 查看日志
docker-compose logs -f web

# 重启后端
docker-compose restart web
```

**前端（Vite）：**

```bash
cd frontend_admin
npm install
npm run dev
```

访问地址：
- 前端：http://localhost:15173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 4.3 快捷脚本

| 脚本 | 用途 | 说明 |
|------|------|------|
| `restart_dev.bat` | 快速重启（保留数据） | 清理端口 + 重启容器 + 启动前端 |
| `restart_with_db.bat` | 完全重启（重置数据库） | 停止容器 + 重置数据库 + 启动服务 |

**使用场景：**

```bash
# 修改前端代码后
restart_dev.bat

# 修改数据库模型后
restart_with_db.bat
```

---

## 5. 前端代理规则

### 5.1 Vite 代理配置

**文件：** `frontend_admin/vite.config.ts`

```typescript
export default defineConfig({
  server: {
    port: 15173,
    strictPort: true,  // 防止端口漂移
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

### 5.2 代理路径映射

| 前端请求 | 后端实际路径 | 说明 |
|---------|------------|------|
| `GET /api/v1/projects` | `http://localhost:8000/api/v1/projects` | API 接口 |
| `GET /storage/1/raw/abc.jpg` | `http://localhost:8000/storage/1/raw/abc.jpg` | 静态文件 |

### 5.3 前端图片路径格式

```typescript
// ✅ 正确：相对路径（自动代理）
const imageUrl = `/storage/${photo.original_path}`

// ❌ 错误：硬编码端口
const imageUrl = `http://localhost:8000/storage/${photo.original_path}`
```

### 5.4 端口冲突防护

**问题：** Vite 端口被占用时自动跳转到 15174/15175，导致代理失效。

**解决方案：**

1. **package.json 自动清理端口：**

```json
{
  "scripts": {
    "dev": "npx kill-port 15173 && vite"
  }
}
```

2. **vite.config.ts 严格端口模式：**

```typescript
{
  server: {
    strictPort: true  // 端口被占用时直接报错，而非自动跳转
  }
}
```

---

## 6. 图片处理逻辑

### 6.1 缩略图生成

**触发时机：**
- 上传照片时（`POST /api/v1/photos/upload`）
- NAS 扫描时（`POST /api/v1/photos/scan-nas`）

**处理流程：**

```python
from PIL import Image

def generate_thumbnail(src_path: Path, thumb_path: Path):
    """生成缩略图（800px 最大边，WEBP 格式）"""
    with Image.open(src_path) as img:
        # 1. 应用 EXIF 旋转
        img = apply_exif_orientation(img)
        
        # 2. 缩放（保持宽高比）
        img.thumbnail((800, 800), Image.LANCZOS)
        
        # 3. 保存为 WEBP
        img.save(thumb_path, format="WEBP", quality=85, method=4)
```

**参数说明：**

| 参数 | 值 | 说明 |
|------|---|------|
| `THUMB_MAX_SIZE` | 800 | 缩略图最大边长（像素） |
| `format` | WEBP | 输出格式（压缩率高） |
| `quality` | 85 | 质量（0-100） |
| `method` | 4 | 压缩方法（0-6，4 为平衡） |

### 6.2 EXIF 旋转处理

**问题：** 手机拍摄的照片可能包含 EXIF 旋转信息，直接读取会显示错误方向。

**解决方案：**

```python
def apply_exif_orientation(img: Image.Image) -> Image.Image:
    """根据 EXIF Orientation 标签旋转图片"""
    try:
        from PIL import ExifTags
        exif = img._getexif()
        if exif is None:
            return img
        
        orientation_key = next(
            k for k, v in ExifTags.TAGS.items() if v == "Orientation"
        )
        orientation = exif.get(orientation_key)
        
        # EXIF Orientation 映射
        rotations = {3: 180, 6: 270, 8: 90}
        if orientation in rotations:
            img = img.rotate(rotations[orientation], expand=True)
    except Exception:
        pass  # 降级：保持原样
    return img
```

### 6.3 拍摄时间提取

```python
def extract_shot_at(img: Image.Image) -> datetime | None:
    """从 EXIF 提取拍摄时间"""
    try:
        from PIL import ExifTags
        exif = img._getexif()
        if exif is None:
            return None
        
        datetime_key = next(
            k for k, v in ExifTags.TAGS.items() if v == "DateTimeOriginal"
        )
        datetime_str = exif.get(datetime_key)
        if datetime_str:
            return datetime.strptime(datetime_str, "%Y:%m:%d %H:%M:%S")
    except Exception:
        pass
    return None
```

### 6.4 支持的图片格式

```python
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic"}
```

**注意：** RAW 格式（.arw, .cr2, .nef）需要额外处理，当前版本不支持。

---

## 7. API 接口规范

### 7.1 统一响应格式

**操作类接口**（创建/更新/删除）：

```json
{
  "code": 200,
  "msg": "操作描述",
  "data": { ... } | null
}
```

**查询/列表类接口**：

```json
{
  "total": 100,
  "items": [ ... ],
  "skip": 0,
  "limit": 20
}
```

**错误响应**：

```json
{
  "detail": "具体错误原因"
}
```

### 7.2 路由前缀规范

| 模块 | 路由前缀 | 文件 |
|------|---------|------|
| 项目管理 | `/api/v1/projects` | `routers/projects.py` |
| 照片管理 | `/api/v1/photos` | `routers/photos.py` |
| 客户管理 | `/api/v1/clients` | `routers/clients.py` |
| 标签管理 | `/api/v1/projects/{id}/tags` | `routers/tags.py` |
| 系统配置 | `/api/v1/system` | `routers/system.py` |
| 设置中心 | `/api/v1/system` | `routers/settings.py` |
| 客户审核 | `/api/v1/reviews` | `routers/reviews.py` |
| 客户交付 | `/api/v1/deliveries` | `routers/deliveries.py` |
| Guest 模块 | `/api/v1/guest` | `routers/guest.py` |

### 7.3 路由定义顺序规则

**关键原则：** 具体路径在前，通配路由在后。

```python
# ✅ 正确
@router.get("/project/{project_id}/sessions")  # 具体路径
async def get_project_sessions(project_id: int): ...

@router.get("/{token}")  # 通配路由
async def get_review_by_token(token: str): ...

# ❌ 错误（通配路由会拦截所有请求）
@router.get("/{token}")
async def get_review_by_token(token: str): ...

@router.get("/project/{project_id}/sessions")  # 永远不会匹配
async def get_project_sessions(project_id: int): ...
```

### 7.4 依赖注入规范

```python
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.deps import CurrentUser

@router.get("/projects")
async def list_projects(
    current_user: CurrentUser,  # 当前用户（认证）
    db: AsyncSession = Depends(get_db),  # 数据库会话
):
    ...
```

**严禁在函数体内直接实例化数据库连接或认证逻辑。**

---

## 8. 数据库模型

### 8.1 核心表结构

| 表名 | 模型类 | 说明 |
|------|--------|------|
| `users` | `User` | 用户表 |
| `clients` | `Client` | 客户表 |
| `projects` | `Project` | 项目表 |
| `project_targets` | `ProjectTarget` | 目标槽位表 |
| `photos` | `Photo` | 照片表 |
| `project_tags` | `ProjectTag` | 项目标签表 |
| `review_sessions` | `ReviewSession` | 审核会话表 |
| `review_feedbacks` | `ReviewFeedback` | 审核反馈表 |
| `delivery_sessions` | `DeliverySession` | 交付会话表 |
| `system_configs` | `SystemConfig` | 系统配置表 |

### 8.2 枚举类型

```python
class UserRole(str, Enum):
    staff = "staff"
    admin = "admin"
    client = "client"

class PhotoStatus(str, Enum):
    pending = "pending"
    selected = "selected"
    deleted = "deleted"

class ProcessState(str, Enum):
    raw = "raw"
    retouched = "retouched"
    final = "final"

class CategoryType(str, Enum):
    white = "white"
    scene = "scene"

class TargetStatus(str, Enum):
    not_started = "not_started"
    shooting = "shooting"
    retouching = "retouching"
    client_review = "client_review"
    completed = "completed"

class ProjectStatus(str, Enum):
    not_started = "not_started"
    shooting = "shooting"
    retouching = "retouching"
    completed = "completed"

class ZipStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
```

### 8.3 照片三阶段工作流

```
┌─────────┐    confirm_raw    ┌───────────┐    upload_retouched    ┌───────┐
│  raw    │ ─────────────────> │ retouched │ ─────────────────────> │ final │
│ 原图    │                    │  精修图    │                        │ 完成图 │
└─────────┘                    └───────────┘                        └───────┘
   ↓                               ↓                                   ↓
is_confirmed=true            parent_id → raw.id                  is_locked=true
                             version = 1, 2, 3...
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `process_state` | Enum | 处理阶段（raw/retouched/final） |
| `is_confirmed` | Boolean | 是否确认（仅 raw 阶段） |
| `parent_id` | Integer | 父照片 ID（精修图指向原图） |
| `version` | Integer | 精修版本号（同一原图的多个精修版本） |
| `is_locked` | Boolean | 是否锁定（客户确认后锁定，防止误删） |

---

## 9. 常见问题排查

### 9.1 图片无法加载（404）

**排查步骤：**

1. **验证后端静态文件服务：**

```bash
curl -I http://localhost:8000/storage/1/raw/example.jpg
```

2. **验证前端代理：**

```bash
curl -I http://localhost:15173/storage/1/raw/example.jpg
```

3. **检查数据库路径：**

```sql
SELECT id, original_path, thumbnail_path 
FROM photos 
WHERE project_id = 1 
LIMIT 5;
```

4. **检查文件是否存在：**

```bash
ls -la nas_mock_data/1/raw/
```

### 9.2 前端端口漂移（15173 → 15174）

**原因：** 端口被占用，Vite 自动跳转到下一个端口。

**解决方案：**

```bash
# 清理端口
npx kill-port 15173 15174 15175

# 重启前端
npm run dev
```

### 9.3 数据显示异常

**排查清单：**

1. 强制刷新浏览器（Ctrl+Shift+R）
2. 运行 `restart_dev.bat`
3. 如果问题依然存在，运行 `restart_with_db.bat`

### 9.4 后端容器无法启动

```bash
# 查看容器日志
docker-compose logs -f web --tail=50

# 检查数据库连接
docker-compose exec db psql -U postgres -d photo_studio -c "SELECT 1;"
```

---

## 10. 部署指南

### 10.1 生产环境配置

**环境变量（.env.production）：**

```bash
# 数据库（使用生产数据库）
DATABASE_URL=postgresql+asyncpg://user:password@db-host:5432/photo_studio

# NAS 挂载路径（实际 NAS 路径）
NAS_MOUNT_PATH=/mnt/nas_production

# JWT 密钥（必须修改）
SECRET_KEY=your-production-secret-key-here

# CORS 配置（添加生产域名）
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# 日志级别
LOG_LEVEL=WARNING
```

### 10.2 Docker 部署

```bash
# 构建镜像
docker-compose -f docker-compose.prod.yml build

# 启动服务
docker-compose -f docker-compose.prod.yml up -d

# 查看日志
docker-compose -f docker-compose.prod.yml logs -f
```

### 10.3 前端构建

```bash
cd frontend_admin
npm run build

# 输出目录：dist/
```

### 10.4 Nginx 配置示例

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    # 前端静态文件
    location / {
        root /var/www/artselect/dist;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # 静态文件代理
    location /storage {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
    }
}
```

---

## 附录

### A. 项目文件结构

```
artselect/
├── app/                          # 后端代码
│   ├── routers/                  # 路由模块
│   │   ├── projects.py           # 项目管理
│   │   ├── photos.py             # 照片管理
│   │   ├── clients.py            # 客户管理
│   │   ├── tags.py               # 标签管理
│   │   ├── system.py             # 系统工具
│   │   ├── settings.py           # 设置中心
│   │   ├── reviews.py            # 客户审核
│   │   ├── deliveries.py         # 客户交付
│   │   └── guest.py              # Guest 模块
│   ├── schemas/                  # Pydantic Schema
│   ├── services/                 # 业务服务
│   │   ├── delivery_zip_service.py      # ZIP 打包服务
│   │   └── delivery_scheduler.py        # 定时任务
│   ├── logic/                    # 业务逻辑
│   │   └── status_manager.py     # 状态计算
│   ├── models.py                 # ORM 模型
│   ├── database.py               # 数据库连接
│   ├── deps.py                   # 依赖注入
│   └── main.py                   # 应用入口
├── frontend_admin/               # 前端代码
│   ├── src/
│   │   ├── components/           # Vue 组件
│   │   ├── views/                # 页面视图
│   │   ├── router/               # 路由配置
│   │   └── main.ts               # 入口文件
│   ├── vite.config.ts            # Vite 配置
│   └── package.json              # 依赖配置
├── nas_mock_data/                # NAS 模拟数据
├── docker-compose.yml            # Docker 配置
├── .env                          # 环境变量
├── API_REGISTRY.md               # API 接口台账
├── ARCHITECTURE.md               # 架构文档
└── DEVELOPER_GUIDE.md            # 开发者指南（本文档）
```

### B. 相关文档

- **API 接口台账：** [API_REGISTRY.md](./API_REGISTRY.md)
- **架构文档：** [ARCHITECTURE.md](./ARCHITECTURE.md)
- **快捷脚本说明：** [开发环境快捷脚本说明.md](./开发环境快捷脚本说明.md)

### C. 联系方式

- **技术支持：** 开发团队
- **问题反馈：** 提交 Issue 或联系项目负责人

---

**文档版本：** 5.0  
**最后更新：** 2026-04-24
