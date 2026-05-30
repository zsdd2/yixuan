"""
routers/system.py —— 系统工具类接口
  - GET /api/v1/system/directory-tree   浏览 NAS 目录树
"""
from pathlib import Path
from typing import Any, TypeVar, Generic

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cleanup_service import RETENTION_DAYS, run_cleanup
from app.database import get_db
from app.deps import CurrentUser
from app.models import SystemConfig

# NAS 根挂载点（与 docker-compose volume 对应）
import os
NAS_ROOT = Path(os.environ.get("NAS_MOUNT_PATH", "/mnt/nas_data"))

router = APIRouter(prefix="/api/v1/system", tags=["system"])


# ── 统一响应包装 ─────────────────────────────────────────────
T = TypeVar("T")


class WrappedResponse(BaseModel, Generic[T]):
    code: int = 200
    msg: str = "success"
    data: T


# ── Schemas ───────────────────────────────────────────────

class DirectoryNode(BaseModel):
    """单个目录/文件节点，树状结构递归嵌套。"""
    name: str
    path: str          # 相对于 NAS_ROOT 的路径（用于传给 scan-nas 的 nas_path）
    type: str          # "directory" | "file"
    children: list["DirectoryNode"] | None = None   # 仅 directory 有此字段
    # 仅 file 有以下字段
    size_bytes: int | None = None
    suffix: str | None = None


class DirectoryTreeResponse(BaseModel):
    root: str                     # NAS_ROOT 绝对路径（容器内）
    query_path: str               # 本次查询的相对路径
    max_depth: int
    tree: list[DirectoryNode]


# ── 内部递归构建函数 ──────────────────────────────────────

# 目录树展示时只显示这些后缀的文件，其余文件隐藏（减少噪音）
_SHOW_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic", ".raw", ".cr2", ".nef", ".arw"}


def _build_tree(
    current_dir: Path,
    nas_root: Path,
    current_depth: int,
    max_depth: int,
    show_files: bool,
) -> list[DirectoryNode]:
    """
    递归构建目录树，返回当前层的节点列表。
    - 遇到 max_depth 时停止递归，目录节点的 children 设为 None（表示未展开）
    - show_files=False 时只返回目录节点，不列出文件
    """
    nodes: list[DirectoryNode] = []
    try:
        entries = sorted(current_dir.iterdir(), key=lambda p: (p.is_file(), p.name.lower()))
    except PermissionError:
        return nodes  # 权限不足时跳过

    for entry in entries:
        # 隐藏以 . 开头的隐藏文件/目录
        if entry.name.startswith("."):
            continue

        rel_path = str(entry.relative_to(nas_root))

        if entry.is_dir():
            if current_depth < max_depth:
                children = _build_tree(
                    entry, nas_root, current_depth + 1, max_depth, show_files
                )
            else:
                children = None  # 达到最大深度，不展开

            nodes.append(
                DirectoryNode(
                    name=entry.name,
                    path=rel_path,
                    type="directory",
                    children=children,
                )
            )

        elif entry.is_file() and show_files:
            if entry.suffix.lower() in _SHOW_SUFFIXES:
                nodes.append(
                    DirectoryNode(
                        name=entry.name,
                        path=rel_path,
                        type="file",
                        size_bytes=entry.stat().st_size,
                        suffix=entry.suffix.lower(),
                    )
                )

    return nodes


# ── 路由 ──────────────────────────────────────────────────

@router.get(
    "/directory-tree",
    response_model=WrappedResponse[DirectoryTreeResponse],
    summary="浏览 NAS 目录树",
    description=(
        "返回 NAS 挂载目录下的树状结构，供前端渲染目录选择器，"
        "或供管理员确认 `nas_path` 后传给 `/api/v1/photos/scan-nas`。\n\n"
        "- `path`：相对于 NAS 根目录的起始路径，默认为根 `\".\"` \n"
        "- `max_depth`：最大递归深度（1-10），默认 3 \n"
        "- `show_files`：是否在树中显示图片文件节点，默认 false（只显目录）"
    ),
)
async def directory_tree(
    current_user: CurrentUser,
    path: str = Query(
        default=".",
        description="相对于 NAS 根目录的起始路径，例如 '2024/client_a'",
        examples=[".", "2024", "2024/client_a"],
    ),
    max_depth: int = Query(
        default=3,
        ge=1,
        le=10,
        description="最大递归深度（1-10）",
    ),
    show_files: bool = Query(
        default=False,
        description="是否在树中显示图片文件节点",
    ),
) -> WrappedResponse[DirectoryTreeResponse]:
    """
    浏览 NAS 目录树。

    典型工作流：
    1. 调用此接口选定 `nas_path`（如 `2024/client_a`）
    2. 将该 `nas_path` 传给 `POST /api/v1/photos/scan-nas` 触发扫描
    """
    # 路径安全校验（防止 ../../../ 穿越）
    try:
        query_dir = (NAS_ROOT / path).resolve()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的 path 参数",
        )

    if not query_dir.is_relative_to(NAS_ROOT.resolve()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="path 不允许路径穿越（不能超出 NAS 根目录）",
        )

    if not query_dir.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"路径不存在：{path}",
        )

    if not query_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"路径不是目录：{path}",
        )

    tree = _build_tree(
        current_dir=query_dir,
        nas_root=NAS_ROOT.resolve(),
        current_depth=1,
        max_depth=max_depth,
        show_files=show_files,
    )

    return WrappedResponse(data=DirectoryTreeResponse(
        root=str(NAS_ROOT),
        query_path=path,
        max_depth=max_depth,
        tree=tree,
    ))


# ── NAS 目录浏览（平铺式，供文件夹选择器使用） ───────────

@router.get("/download", summary="下载 NAS 存储文件")
async def download_storage_file(
    current_user: CurrentUser,
    path: str = Query(..., description="相对 NAS 根目录的文件路径"),
    filename: str | None = Query(None, description="下载时使用的文件名"),
):
    import urllib.parse

    decoded = urllib.parse.unquote(path).replace("\\", "/")
    nas_root = NAS_ROOT.resolve()
    candidate = Path(decoded)
    target = candidate.resolve() if candidate.is_absolute() else (nas_root / decoded).resolve()

    if not target.is_relative_to(nas_root):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    if not target.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    download_name = (filename or target.name).replace("\r", "").replace("\n", "").strip() or target.name
    return FileResponse(target, filename=download_name, content_disposition_type="attachment")


class BrowseNasResponse(BaseModel):
    current_path: str
    parent_path: str | None
    folders: list[str]


@router.get(
    "/browse-nas",
    response_model=WrappedResponse[BrowseNasResponse],
    summary="浏览 NAS 子文件夹（平铺）",
)
async def browse_nas(
    current_user: CurrentUser,
    path: str = Query(
        default=".",
        description="相对于 NAS 根目录的当前路径",
    ),
) -> WrappedResponse[BrowseNasResponse]:
    try:
        target = (NAS_ROOT / path).resolve()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效路径")

    if not target.is_relative_to(NAS_ROOT.resolve()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="路径越界")

    if not target.exists() or not target.is_dir():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="目录不存在")

    folders: list[str] = []
    try:
        for entry in sorted(target.iterdir(), key=lambda p: p.name.lower()):
            if entry.is_dir() and not entry.name.startswith("."):
                folders.append(entry.name)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")

    rel = target.relative_to(NAS_ROOT.resolve())
    current_str = str(rel) if str(rel) != "." else "."
    parent_str: str | None = None
    if current_str != ".":
        p = rel.parent
        parent_str = str(p) if str(p) != "." else "."

    return WrappedResponse(data=BrowseNasResponse(
        current_path=current_str,
        parent_path=parent_str,
        folders=folders,
    ))


# ── 临时清理触发接口（仅供测试） ──────────────────────────

class TriggerCleanupResponse(BaseModel):
    retention_days: int
    scanned_projects: int
    eligible_projects: list[int]
    files_deleted: int
    files_missing: int
    rows_deleted: int
    errors: list[str]


@router.post(
    "/trigger-cleanup",
    response_model=WrappedResponse[TriggerCleanupResponse],
    summary="[测试用] 立刻触发回收站清理服务",
)
async def trigger_cleanup(
    current_user: CurrentUser,
    retention_days: int = Query(
        default=RETENTION_DAYS,
        ge=0,
        le=365,
        description="保留天数，默认 15。开发期可传 0 立刻清理所有归档项目。",
    ),
    db: AsyncSession = Depends(get_db),
) -> WrappedResponse[TriggerCleanupResponse]:
    """
    同步执行一次 cleanup_service.run_cleanup() 并返回报告。

    生产环境应改用 cron / 定时任务调用 `python -m cleanup_service`。
    """
    report = await run_cleanup(db, retention_days=retention_days)
    return WrappedResponse(data=TriggerCleanupResponse(
        retention_days=retention_days,
        **report.to_dict(),
    ))


# ── 系统配置管理 ──────────────────────────────────────────

class SystemConfigItem(BaseModel):
    config_key: str
    config_value: str | None
    description: str | None


class UpdateConfigRequest(BaseModel):
    config_value: str


@router.get(
    "/configs",
    response_model=WrappedResponse[list[SystemConfigItem]],
    summary="获取所有系统配置",
)
async def get_configs(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> WrappedResponse[list[SystemConfigItem]]:
    """获取所有系统配置项。"""
    stmt = select(SystemConfig)
    result = await db.execute(stmt)
    configs = result.scalars().all()

    return WrappedResponse(data=[
        SystemConfigItem(
            config_key=c.config_key,
            config_value=c.config_value,
            description=c.description,
        )
        for c in configs
    ])


@router.get(
    "/configs/{config_key}",
    response_model=WrappedResponse[SystemConfigItem],
    summary="获取单个系统配置",
)
async def get_config(
    config_key: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> WrappedResponse[SystemConfigItem]:
    """获取指定配置项的值。"""
    stmt = select(SystemConfig).where(SystemConfig.config_key == config_key)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if not config:
        # 如果配置不存在，返回空值
        return WrappedResponse(
            msg="配置不存在",
            data=SystemConfigItem(
                config_key=config_key,
                config_value=None,
                description=None,
            ),
        )

    return WrappedResponse(
        msg="获取成功",
        data=SystemConfigItem(
            config_key=config.config_key,
            config_value=config.config_value,
            description=config.description,
        ),
    )


@router.put(
    "/configs/{config_key}",
    response_model=WrappedResponse[SystemConfigItem],
    summary="更新系统配置",
)
async def update_config(
    config_key: str,
    request: UpdateConfigRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> WrappedResponse[SystemConfigItem]:
    """更新指定配置项的值，如果不存在则创建。"""
    stmt = select(SystemConfig).where(SystemConfig.config_key == config_key)
    result = await db.execute(stmt)
    config = result.scalar_one_or_none()

    if config:
        config.config_value = request.config_value
    else:
        config = SystemConfig(
            config_key=config_key,
            config_value=request.config_value,
            description=None,
        )
        db.add(config)

    await db.commit()
    await db.refresh(config)

    return WrappedResponse(
        msg="配置已更新",
        data=SystemConfigItem(
            config_key=config.config_key,
            config_value=config.config_value,
            description=config.description,
        ),
    )
