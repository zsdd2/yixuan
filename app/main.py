from contextlib import asynccontextmanager
import os

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.database import Base, engine
import app.models  # noqa: F401  确保所有 ORM 模型注册到 Base.metadata
from app.init_db import seed_admin_user, seed_builtin_templates
from app.routers import analytics, auth, billing, clients, deliveries, guest, photos, projects, reviews, settings, system, tags, users
from app.services.delivery_scheduler import start_scheduler, stop_scheduler

APP_VERSION = "1.0.14"


# ── 生命周期事件 ──────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时写入种子数据；关闭时释放连接池。

    注意：数据库迁移由 Alembic 管理，在容器启动时通过 entrypoint.sh 执行。
    """
    # 数据库表由 Alembic 迁移创建，这里仅执行种子数据初始化
    await seed_admin_user()
    await seed_builtin_templates()
    print("[OK] Seed data ready")

    # 启动交付 ZIP 调度器
    start_scheduler()
    print("[OK] Delivery scheduler started")

    yield  # ── 应用运行中 ──

    # 停止调度器
    stop_scheduler()
    print("[OK] Delivery scheduler stopped")

    await engine.dispose()
    print("[OK] DB connection pool closed")


app = FastAPI(
    title="Commercial Photography Project Tracker",
    description="商业摄影项目跟进系统",
    version=APP_VERSION,
    lifespan=lifespan,
)

# ── CORS 中间件 ────────────────────────────────────────────
# 从环境变量读取允许的源
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:15173,http://127.0.0.1:15173"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 路由注册 ──────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(photos.router)
app.include_router(system.router)
app.include_router(guest.router)
app.include_router(tags.router)
app.include_router(clients.router)
app.include_router(settings.router)
app.include_router(reviews.router)
app.include_router(deliveries.router)
app.include_router(billing.router)
app.include_router(analytics.router)


@app.get("/", tags=["health"])
async def root():
    return {"status": "ok", "message": "System is running", "version": APP_VERSION}


@app.get("/health", tags=["health"])
async def health_check():
    """健康检查端点，用于容器健康监控"""
    return {"status": "healthy", "version": APP_VERSION}


# ── 静态文件代理（缩略图 & NAS 图片访问）─────────────────
import os
from pathlib import Path

NAS_MOUNT = Path(os.environ.get("NAS_MOUNT_PATH", "/mnt/nas_data"))

_SAFE_ROOTS = [
    NAS_MOUNT.resolve(),
]


@app.get("/storage/{file_path:path}", tags=["static"])
async def serve_file(file_path: str):
    """根据 NAS 相对路径提供缩略图 / NAS 原图文件，含路径穿越防护。"""
    import urllib.parse
    decoded = urllib.parse.unquote(file_path).replace("\\", "/")

    nas_root = NAS_MOUNT.resolve()

    candidate = Path(decoded)
    if candidate.is_absolute():
        target = candidate.resolve()
    else:
        target = (nas_root / decoded).resolve()

    if not target.is_relative_to(nas_root):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="forbidden",
        )

    if not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在",
        )

    return FileResponse(target)
