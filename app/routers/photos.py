"""
routers/photos.py —— 图片相关接口
  - POST  /api/v1/photos/upload        上传本地图片
  - POST  /api/v1/photos/scan-nas      触发 NAS 目录扫描并异步入库
  - GET   /api/v1/photos/scan-nas/{task_id}/status  查询扫描任务状态
  - PATCH /api/v1/photos/bulk-update   批量更新照片状态/目标
"""
import hashlib
import io
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from PIL import Image
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.deps import CurrentUser
from app.models import CategoryType, Client, Photo, PhotoStatus, ProcessState, Project, ProjectGroup, ProjectTag, ProjectTarget, photo_tags
from app.services.delivery_zip_service import mark_zip_dirty
from app.schemas.photo_schema import (
    BulkTagRequest,
    BulkTagResponse,
    BulkUpdateRequest,
    BulkUpdateResponse,
    ConfirmRawRequest,
    HardDeleteResponse,
    PhotoResponse,
    PortfolioFilterOption,
    PortfolioFilterResponse,
    PortfolioItem,
    PortfolioListResponse,
    ScanNasRequest,
    ScanNasResponse,
    ScanTaskStatusResponse,
    SoftDeleteRequest,
    SoftDeleteResponse,
    UpdateNotesRequest,
)

# ── 常量 ──────────────────────────────────────────────────

import os
NAS_ROOT = Path(os.environ.get("NAS_MOUNT_PATH", "/mnt/nas_data"))
THUMB_MAX_SIZE = int(os.environ.get("THUMB_MAX_SIZE", "800"))
SUPPORTED_SUFFIXES = set(
    os.environ.get(
        "SUPPORTED_IMAGE_FORMATS",
        ".jpg,.jpeg,.png,.tif,.tiff,.webp,.heic"
    ).split(",")
)

_scan_tasks: dict[str, dict[str, Any]] = {}

router = APIRouter(prefix="/api/v1/photos", tags=["photos"])


async def _next_display_id(db: AsyncSession, project_id: int) -> int:
    result = await db.execute(
        select(sa_func.coalesce(sa_func.max(Photo.display_id), 0))
        .where(Photo.project_id == project_id)
    )
    return (result.scalar() or 0) + 1


# ── 同步图片处理函数（在线程池中调用）────────────────────

def _apply_exif_orientation(img: Image.Image) -> Image.Image:
    try:
        from PIL import ExifTags
        exif = img._getexif()  # type: ignore[attr-defined]
        if exif is None:
            return img
        orientation_key = next(
            k for k, v in ExifTags.TAGS.items() if v == "Orientation"
        )
        orientation = exif.get(orientation_key)
        rotations = {3: 180, 6: 270, 8: 90}
        if orientation in rotations:
            img = img.rotate(rotations[orientation], expand=True)
    except Exception:
        pass
    return img


def _make_thumbnail_sync(src_path: Path, thumb_path: Path) -> datetime | None:
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    shot_at: datetime | None = None
    with Image.open(src_path) as img:
        shot_at = _extract_shot_at(img)
        img = _apply_exif_orientation(img)
        img.thumbnail((THUMB_MAX_SIZE, THUMB_MAX_SIZE), Image.LANCZOS)
        img.save(thumb_path, format="WEBP", quality=85, method=4)
    return shot_at


def _extract_shot_at(img: Image.Image) -> datetime | None:
    """从 EXIF 提取拍摄时间，失败返回 None（降级为上传时间）。"""
    try:
        from PIL import ExifTags
        exif = img._getexif()  # type: ignore[attr-defined]
        if exif is None:
            return None
        dt_key = next(
            (k for k, v in ExifTags.TAGS.items() if v == "DateTimeOriginal"), None
        )
        if dt_key is None or dt_key not in exif:
            return None
        dt_str = exif[dt_key]
        return datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _save_and_thumbnail(
    raw_dir: Path,
    thumb_dir: Path,
    file_bytes: bytes,
    original_suffix: str,
) -> tuple[Path, Path, datetime | None]:
    """
    用 UUID 文件名保存原图 + 生成 WebP 缩略图 + 提取拍摄时间。
    返回 (原图 NAS 相对路径, 缩略图 NAS 相对路径, 拍摄时间或None)。
    """
    raw_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir.mkdir(parents=True, exist_ok=True)

    unique_stem = uuid.uuid4().hex
    original_path = raw_dir / f"{unique_stem}{original_suffix}"
    original_path.write_bytes(file_bytes)

    shot_at: datetime | None = None
    thumb_path = thumb_dir / f"{unique_stem}.webp"
    with Image.open(io.BytesIO(file_bytes)) as img:
        shot_at = _extract_shot_at(img)
        img = _apply_exif_orientation(img)
        img.thumbnail((THUMB_MAX_SIZE, THUMB_MAX_SIZE), Image.LANCZOS)
        img.save(thumb_path, format="WEBP", quality=85, method=4)

    nas_resolved = NAS_ROOT.resolve()
    rel_orig = original_path.resolve().relative_to(nas_resolved)
    rel_thumb = thumb_path.resolve().relative_to(nas_resolved)
    return rel_orig, rel_thumb, shot_at


def _hard_delete_file(path_str: str | None) -> tuple[int, int, str | None]:
    """
    物理删除单个文件。返回 (deleted, missing, error_or_None)。
    遵循 cleanup_service.py:54-66 的模式。
    """
    if not path_str:
        return (0, 0, None)
    p = Path(path_str)
    try:
        if p.is_file():
            p.unlink()
            return (1, 0, None)
        else:
            return (0, 1, None)
    except OSError as exc:
        return (0, 0, f"删除失败 {path_str}: {exc}")


async def _ensure_group(
    db: AsyncSession,
    project_id: int,
    group_id: int | None,
) -> ProjectGroup | None:
    if group_id is None:
        return None
    group = await db.get(ProjectGroup, group_id)
    if group is None or group.project_id != project_id or group.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"组合 id={group_id} 不存在或不属于该项目")
    return group


# ── 后台扫描任务 ─────────────────────────────────────────

async def _run_scan_task(
    task_id: str,
    project_id: int,
    group_id: int | None,
    target_id: int | None,
    scan_dir: Path,
    generate_thumbnails: bool,
    process_state: ProcessState = ProcessState.raw,
    tag_ids: list[int] | None = None,
) -> None:
    state = _scan_tasks[task_id]
    state["status"] = "running"

    all_files = sorted(
        f for f in scan_dir.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_SUFFIXES
    )
    state["total"] = len(all_files)

    failed_files: list[str] = []

    thumb_dir = NAS_ROOT / str(project_id) / "thumb"
    thumb_dir.mkdir(parents=True, exist_ok=True)

    async with AsyncSessionLocal() as session:
        # 加载项目的所有目标及其 folder_path（用于路径自动关联）
        targets_result = await session.execute(
            select(ProjectTarget.id, ProjectTarget.folder_path)
            .where(
                ProjectTarget.project_id == project_id,
                ProjectTarget.folder_path.isnot(None),
                ProjectTarget.deleted_at.is_(None)
            )
        )
        targets_map = {row[1]: row[0] for row in targets_result.all()}

        current_max = (await session.execute(
            select(sa_func.coalesce(sa_func.max(Photo.display_id), 0))
            .where(Photo.project_id == project_id)
        )).scalar() or 0

        for idx, file_path in enumerate(all_files):
            try:
                nas_resolved = NAS_ROOT.resolve()
                original_path_str = str(file_path.resolve().relative_to(nas_resolved))

                existing = await session.scalar(
                    select(Photo).where(Photo.original_path == original_path_str)
                )
                if existing is not None:
                    state["skipped"] += 1
                    state["processed"] += 1
                    continue

                thumb_path_str: str | None = None
                shot_at: datetime | None = None
                if generate_thumbnails:
                    thumb_name = f"{uuid.uuid4().hex}.webp"
                    thumb_path = thumb_dir / thumb_name
                    try:
                        shot_at = await run_in_threadpool(
                            _make_thumbnail_sync, file_path, thumb_path
                        )
                        thumb_path_str = str(thumb_path.resolve().relative_to(nas_resolved))
                    except Exception as thumb_exc:
                        failed_files.append(
                            f"{file_path.name} (thumb error: {thumb_exc})"
                        )

                # 路径自动关联：如果未指定 target_id，尝试根据文件路径匹配目标
                resolved_target_id = target_id
                if resolved_target_id is None and targets_map:
                    for folder_path, tid in targets_map.items():
                        if original_path_str.startswith(folder_path):
                            resolved_target_id = tid
                            break

                current_max += 1
                photo = Photo(
                    project_id=project_id,
                    group_id=group_id,
                    target_id=resolved_target_id,
                    original_path=original_path_str,
                    original_filename=file_path.name,
                    thumbnail_path=thumb_path_str,
                    display_id=current_max,
                    process_state=process_state,
                    shot_at=shot_at,
                )
                session.add(photo)

                if tag_ids:
                    await session.flush()
                    for tid in tag_ids:
                        await session.execute(
                            photo_tags.insert().values(photo_id=photo.id, tag_id=tid)
                        )
                session.add(photo)

                if (idx + 1) % 50 == 0:
                    await session.commit()

                state["processed"] += 1

            except Exception as exc:
                failed_files.append(f"{file_path.name}: {exc}")
                state["processed"] += 1
                continue

        try:
            await session.commit()
        except Exception as exc:
            await session.rollback()
            state["status"] = "failed"
            state["error"] = f"最终提交失败：{exc}"
            state["failed_files"] = failed_files
            return

    state["status"] = "done"
    state["failed_files"] = failed_files


# ── 路由 ──────────────────────────────────────────────────

@router.post(
    "/upload",
    response_model=PhotoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传本地图片",
)
async def upload_photo(
    current_user: CurrentUser,
    project_id: int = Form(..., description="所属项目 ID"),
    group_id: int | None = Form(None, description="组合/批次/商品组 ID"),
    target_id: int | None = Form(None, description="目标槽位 ID（可为空）"),
    process_state: str = Form("raw", description="入库阶段: raw/retouched/final"),
    tag_ids: str = Form("", description="逗号分隔的标签ID列表，如 1,2,3"),
    file: UploadFile = ...,
    db: AsyncSession = Depends(get_db),
) -> PhotoResponse:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    group = await _ensure_group(db, project_id, group_id)
    if target_id is not None:
        target = await db.get(ProjectTarget, target_id)
        if target is None or target.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"目标 id={target_id} 不存在或不属于该项目",
            )

    try:
        ps = ProcessState(process_state)
    except ValueError:
        valid = [s.value for s in ProcessState]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的处理阶段 '{process_state}'，合法值：{valid}",
        )

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="上传文件为空",
        )

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    existing = await db.scalar(
        select(Photo).where(Photo.project_id == project_id, Photo.file_hash == file_hash)
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"图片已存在于项目中（编号 #{existing.display_id}）",
        )

    original_filename = file.filename or "upload.jpg"
    suffix = Path(original_filename).suffix.lower() or ".jpg"

    raw_dir = NAS_ROOT / str(project_id) / "raw"
    thumb_dir = NAS_ROOT / str(project_id) / "thumb"

    try:
        original_path, thumb_path, shot_at = await run_in_threadpool(
            _save_and_thumbnail,
            raw_dir,
            thumb_dir,
            file_bytes,
            suffix,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"图片处理失败：{exc}",
        )

    parsed_tag_ids = [int(x) for x in tag_ids.split(",") if x.strip().isdigit()] if tag_ids else []

    display_id = await _next_display_id(db, project_id)
    photo = Photo(
        project_id=project_id,
        group_id=group_id,
        target_id=target_id,
        original_path=str(original_path),
        original_filename=file.filename,
        thumbnail_path=str(thumb_path),
        file_hash=file_hash,
        display_id=display_id,
        process_state=ps,
        shot_at=shot_at,
    )
    db.add(photo)
    await db.flush()

    if parsed_tag_ids:
        for tid in parsed_tag_ids:
            await db.execute(
                photo_tags.insert().values(photo_id=photo.id, tag_id=tid)
            )

    await db.refresh(photo)
    await db.commit()

    # 检查是否上传了 final 照片，触发脏数据标记
    if ps == ProcessState.final:
        await mark_zip_dirty(project_id, db)

    return PhotoResponse(
        id=photo.id,
        project_id=photo.project_id,
        group_id=photo.group_id,
        group_name=group.name if group else None,
        target_id=photo.target_id,
        display_id=photo.display_id,
        original_path=photo.original_path,
        original_filename=photo.original_filename,
        thumbnail_path=photo.thumbnail_path,
        status=photo.status.value,
        process_state=photo.process_state.value,
    )


@router.post(
    "/scan-nas",
    response_model=ScanNasResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="触发 NAS 目录扫描并异步入库",
)
async def scan_nas(
    body: ScanNasRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ScanNasResponse:
    project = await db.get(Project, body.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={body.project_id} 不存在",
        )

    await _ensure_group(db, body.project_id, body.group_id)
    if body.target_id is not None:
        target = await db.get(ProjectTarget, body.target_id)
        if target is None or target.project_id != body.project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"目标 id={body.target_id} 不存在或不属于该项目",
            )

    try:
        ps = ProcessState(body.process_state)
    except ValueError:
        valid = [s.value for s in ProcessState]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效的处理阶段 '{body.process_state}'，合法值：{valid}",
        )

    scan_dir = (NAS_ROOT / body.nas_path).resolve()
    if not scan_dir.is_relative_to(NAS_ROOT.resolve()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="nas_path 不允许路径穿越",
        )
    if not scan_dir.exists() or not scan_dir.is_dir():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NAS 路径不存在或不是目录：{body.nas_path}",
        )

    task_id = str(uuid.uuid4())
    _scan_tasks[task_id] = {
        "status": "queued",
        "total": 0,
        "processed": 0,
        "skipped": 0,
        "failed_files": [],
        "error": None,
    }

    background_tasks.add_task(
        _run_scan_task,
        task_id=task_id,
        project_id=body.project_id,
        group_id=body.group_id,
        target_id=body.target_id,
        scan_dir=scan_dir,
        generate_thumbnails=body.generate_thumbnails,
        process_state=ps,
        tag_ids=body.tag_ids or None,
    )

    return ScanNasResponse(
        task_id=task_id,
        message=f"扫描任务已排队，路径：{scan_dir}",
        status="queued",
    )


@router.get(
    "/scan-nas/{task_id}/status",
    response_model=ScanTaskStatusResponse,
    summary="查询 NAS 扫描任务状态",
)
async def get_scan_status(
    task_id: str,
    current_user: CurrentUser,
) -> ScanTaskStatusResponse:
    state = _scan_tasks.get(task_id)
    if state is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"任务 {task_id} 不存在",
        )
    return ScanTaskStatusResponse(
        task_id=task_id,
        status=state["status"],
        total=state["total"],
        processed=state["processed"],
        skipped=state["skipped"],
        failed_files=state["failed_files"],
        error=state.get("error"),
    )


# ── 批量更新路由 ──────────────────────────────────────────

@router.patch(
    "/bulk-update",
    response_model=BulkUpdateResponse,
    summary="批量更新照片状态/目标",
)
async def bulk_update_photos(
    body: BulkUpdateRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> BulkUpdateResponse:
    if body.status is None and body.target_id is None and body.group_id is None and body.process_state is None and not body.remove_from_target and not body.remove_from_group:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="至少需要提供一个更新字段：status / target_id / group_id / remove_from_target / remove_from_group / process_state",
        )

    if body.status is not None:
        try:
            PhotoStatus(body.status)
        except ValueError:
            valid = [s.value for s in PhotoStatus]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态值 '{body.status}'，合法值：{valid}",
            )

    if body.process_state is not None:
        try:
            ProcessState(body.process_state)
        except ValueError:
            valid = [s.value for s in ProcessState]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的处理阶段 '{body.process_state}'，合法值：{valid}",
            )

    if body.target_id is not None:
        target = await db.get(ProjectTarget, body.target_id)
        if target is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"目标 id={body.target_id} 不存在",
            )

    group: ProjectGroup | None = None
    if body.group_id is not None:
        group = await db.get(ProjectGroup, body.group_id)
        if group is None or group.deleted_at is not None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"组合 id={body.group_id} 不存在")

    stmt = select(Photo).where(Photo.id.in_(body.photo_ids))
    result = await db.execute(stmt)
    photos = result.scalars().all()

    if not photos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到任何匹配的照片",
        )

    now = datetime.now(timezone.utc)
    for photo in photos:
        if body.status is not None:
            new_status = PhotoStatus(body.status)
            photo.status = new_status
            if new_status == PhotoStatus.deleted:
                photo.deleted_at = now
            elif photo.deleted_at is not None:
                photo.deleted_at = None
        if body.target_id is not None:
            photo.target_id = body.target_id
            if target.group_id is not None:
                photo.group_id = target.group_id
        elif body.remove_from_target:
            photo.target_id = None
        if body.group_id is not None:
            if group and group.project_id != photo.project_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="组合与照片不属于同一项目")
            photo.group_id = body.group_id
        elif body.remove_from_group:
            photo.group_id = None
        if body.process_state is not None:
            photo.process_state = ProcessState(body.process_state)

    await db.commit()

    # 检查是否涉及 final 照片变化，触发脏数据标记
    if body.process_state:
        has_final_change = any(
            photo.process_state == ProcessState.final or body.process_state == "final"
            for photo in photos
        )
        if has_final_change and photos:
            await mark_zip_dirty(photos[0].project_id, db)

    return BulkUpdateResponse(
        updated=len(photos),
        message=f"成功更新 {len(photos)} 张照片",
    )


# ── 软删除 / 恢复 ────────────────────────────────────────

@router.post(
    "/bulk-soft-delete",
    response_model=SoftDeleteResponse,
    summary="批量将照片移入回收站（软删除）",
)
async def bulk_soft_delete(
    body: SoftDeleteRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SoftDeleteResponse:
    stmt = select(Photo).where(
        Photo.id.in_(body.photo_ids),
        Photo.status != PhotoStatus.deleted,
    )
    result = await db.execute(stmt)
    photos = result.scalars().all()

    if not photos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到任何可删除的照片（可能均已在回收站）",
        )

    now = datetime.now(timezone.utc)
    for photo in photos:
        photo.status = PhotoStatus.deleted
        photo.deleted_at = now

    await db.commit()

    # 检查是否删除了 final 照片，触发脏数据标记
    if photos:
        has_final = any(photo.process_state == ProcessState.final for photo in photos)
        if has_final:
            await mark_zip_dirty(photos[0].project_id, db)

    return SoftDeleteResponse(
        affected=len(photos),
        message=f"已将 {len(photos)} 张照片移入回收站",
    )


@router.post(
    "/bulk-restore",
    response_model=SoftDeleteResponse,
    summary="批量从回收站恢复照片",
)
async def bulk_restore(
    body: SoftDeleteRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SoftDeleteResponse:
    stmt = select(Photo).where(
        Photo.id.in_(body.photo_ids),
        Photo.status == PhotoStatus.deleted,
    )
    result = await db.execute(stmt)
    photos = result.scalars().all()

    if not photos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到任何可恢复的照片",
        )

    for photo in photos:
        photo.status = PhotoStatus.pending
        photo.deleted_at = None

    await db.commit()

    # 检查是否恢复了 final 照片，触发脏数据标记
    if photos:
        has_final = any(photo.process_state == ProcessState.final for photo in photos)
        if has_final:
            await mark_zip_dirty(photos[0].project_id, db)

    return SoftDeleteResponse(
        affected=len(photos),
        message=f"已恢复 {len(photos)} 张照片",
    )


# ── 物理删除 ────────────────────────────────────────────

@router.post(
    "/bulk-hard-delete",
    response_model=HardDeleteResponse,
    summary="批量物理删除照片（不可恢复：删除数据库记录 + 磁盘文件）",
)
async def bulk_hard_delete(
    body: SoftDeleteRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> HardDeleteResponse:
    stmt = select(Photo).where(Photo.id.in_(body.photo_ids))
    result = await db.execute(stmt)
    photos = result.scalars().all()

    if not photos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到任何匹配的照片",
        )

    file_paths: list[str | None] = []
    for photo in photos:
        file_paths.append(photo.original_path)
        file_paths.append(photo.thumbnail_path)

    for photo in photos:
        await db.delete(photo)
    await db.commit()

    files_deleted = 0
    files_missing = 0
    errors: list[str] = []
    for path_str in file_paths:
        d, m, err = await run_in_threadpool(_hard_delete_file, path_str)
        files_deleted += d
        files_missing += m
        if err:
            errors.append(err)

    return HardDeleteResponse(
        deleted=len(photos),
        files_deleted=files_deleted,
        files_missing=files_missing,
        errors=errors,
    )


# ── 批量标签操作 ────────────────────────────────────────

@router.post(
    "/bulk-add-tags",
    response_model=BulkTagResponse,
    summary="批量为照片添加标签",
)
async def bulk_add_tags(
    body: BulkTagRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> BulkTagResponse:
    existing = (await db.execute(
        select(photo_tags.c.photo_id, photo_tags.c.tag_id)
        .where(photo_tags.c.photo_id.in_(body.photo_ids), photo_tags.c.tag_id.in_(body.tag_ids))
    )).all()
    existing_set = {(r[0], r[1]) for r in existing}

    inserted = 0
    for pid in body.photo_ids:
        for tid in body.tag_ids:
            if (pid, tid) not in existing_set:
                await db.execute(photo_tags.insert().values(photo_id=pid, tag_id=tid))
                inserted += 1
    await db.commit()
    return BulkTagResponse(affected=inserted, message=f"已为 {len(body.photo_ids)} 张照片添加标签")


@router.post(
    "/bulk-remove-tags",
    response_model=BulkTagResponse,
    summary="批量移除照片标签",
)
async def bulk_remove_tags(
    body: BulkTagRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> BulkTagResponse:
    from sqlalchemy import delete
    result = await db.execute(
        delete(photo_tags).where(
            photo_tags.c.photo_id.in_(body.photo_ids),
            photo_tags.c.tag_id.in_(body.tag_ids),
        )
    )
    await db.commit()
    return BulkTagResponse(affected=result.rowcount, message=f"已移除标签")


# ═══════════════════ 作品中心 (Portfolio) ═══════════════════

@router.get("/portfolio/filters", response_model=PortfolioFilterResponse, summary="作品中心筛选项")
async def portfolio_filters(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> PortfolioFilterResponse:
    from sqlalchemy import distinct

    types_rows = (await db.execute(
        select(distinct(Project.shooting_type)).where(
            Project.shooting_type.isnot(None), Project.deleted_at.is_(None)
        )
    )).scalars().all()

    clients_rows = (await db.execute(
        select(Client.id, Client.name).where(Client.deleted_at.is_(None)).order_by(Client.id)
    )).all()

    projects_rows = (await db.execute(
        select(Project.id, Project.name).where(Project.deleted_at.is_(None)).order_by(Project.created_at.desc())
    )).all()

    # 获取所有目标名称（去重）
    target_names_rows = (await db.execute(
        select(distinct(ProjectTarget.name)).where(
            ProjectTarget.name.isnot(None),
            ProjectTarget.deleted_at.is_(None)
        ).order_by(ProjectTarget.name)
    )).scalars().all()

    return PortfolioFilterResponse(
        shooting_types=[t for t in types_rows if t],
        clients=[PortfolioFilterOption(id=r[0], name=r[1]) for r in clients_rows],
        projects=[PortfolioFilterOption(id=r[0], name=r[1]) for r in projects_rows],
        target_names=[t for t in target_names_rows if t],
    )


@router.get("/portfolio", response_model=PortfolioListResponse, summary="作品中心列表")
async def portfolio_list(
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    process_state: str = Query("final"),
    client_id: int | None = Query(None),
    project_id: int | None = Query(None),
    target_name: str | None = Query(None),
    shooting_type: str | None = Query(None),
    category_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> PortfolioListResponse:
    base = (
        select(
            Photo.id,
            Photo.project_id,
            Photo.original_path,
            Photo.thumbnail_path,
            Photo.process_state,
            Photo.shot_at,
            Photo.created_at,
            Project.name.label("project_name"),
            Project.client_prefix,
            Project.serial_number,
            Project.shooting_type,
            Client.name.label("client_name"),
            ProjectTarget.name.label("target_name"),
            ProjectTarget.category_type,
        )
        .join(Project, Photo.project_id == Project.id)
        .join(Client, Project.client_id == Client.id)
        .outerjoin(ProjectTarget, Photo.target_id == ProjectTarget.id)
        .where(
            Photo.status != PhotoStatus.deleted,
            Photo.process_state == ProcessState(process_state),
            Project.deleted_at.is_(None),
        )
    )

    if client_id is not None:
        base = base.where(Project.client_id == client_id)
    if project_id is not None:
        base = base.where(Photo.project_id == project_id)
    if target_name is not None:
        base = base.where(ProjectTarget.name == target_name)
    if shooting_type is not None:
        base = base.where(Project.shooting_type == shooting_type)
    if category_type is not None:
        base = base.where(ProjectTarget.category_type == CategoryType(category_type))

    count_stmt = select(sa_func.count()).select_from(base.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    rows = (await db.execute(
        base.order_by(Photo.created_at.desc()).offset(skip).limit(limit)
    )).all()

    items = []
    for r in rows:
        prefix = r.client_prefix or ""
        did = f"{prefix}{r.serial_number:06d}"
        items.append(PortfolioItem(
            id=r.id,
            project_id=r.project_id,
            project_name=r.project_name or "",
            display_id=did,
            client_name=r.client_name or "",
            shooting_type=r.shooting_type,
            target_name=r.target_name,
            category_type=r.category_type.value if r.category_type else None,
            thumbnail_path=r.thumbnail_path,
            original_path=r.original_path,
            process_state=r.process_state.value,
            shot_at=r.shot_at.isoformat() if r.shot_at else None,
            created_at=r.created_at.isoformat(),
        ))

    return PortfolioListResponse(total=total, items=items)


# ── 确认原图 ────────────────────────────────────────────────

@router.post(
    "/confirm-raw",
    summary="确认原图（标记 is_confirmed=True）",
)
async def confirm_raw_photos(
    body: ConfirmRawRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Photo).where(
        Photo.id.in_(body.photo_ids),
        Photo.process_state == ProcessState.raw,
        Photo.status != PhotoStatus.deleted,
    )
    photos = (await db.execute(stmt)).scalars().all()

    if not photos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到符合条件的原片（需为 raw 且未删除）",
        )

    for photo in photos:
        photo.is_confirmed = True

    await db.commit()

    return {"code": 200, "msg": f"成功确认 {len(photos)} 张原图", "data": {"confirmed": len(photos)}}


@router.post(
    "/unconfirm-raw",
    summary="取消确认原图（标记 is_confirmed=False）",
)
async def unconfirm_raw_photos(
    body: ConfirmRawRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Photo).where(
        Photo.id.in_(body.photo_ids),
        Photo.process_state == ProcessState.raw,
        Photo.status != PhotoStatus.deleted,
        Photo.is_confirmed == True,
    )
    photos = (await db.execute(stmt)).scalars().all()

    if not photos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到符合条件的已确认原片",
        )

    has_children_stmt = select(Photo.parent_id).where(
        Photo.parent_id.in_([p.id for p in photos]),
        Photo.status != PhotoStatus.deleted,
    ).distinct()
    parents_with_children = set(
        (await db.execute(has_children_stmt)).scalars().all()
    )
    if parents_with_children:
        ids_str = ", ".join(str(pid) for pid in parents_with_children)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"以下原图已关联精修版本，无法取消确认: {ids_str}",
        )

    for photo in photos:
        photo.is_confirmed = False

    await db.commit()

    return {"code": 200, "msg": f"已取消确认 {len(photos)} 张原图", "data": {"unconfirmed": len(photos)}}


# ── 上传精修图（关联确认原图）──────────────────────────────

@router.post(
    "/upload-retouched",
    response_model=PhotoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传精修图并关联确认原图（支持上传新文件或关联已有照片）",
)
async def upload_retouched(
    current_user: CurrentUser,
    file: UploadFile = None,
    project_id: int = Form(...),
    target_id: int = Form(...),
    parent_id: int = Form(..., description="确认原图 ID"),
    revision_notes: str | None = Form(None, description="修改说明"),
    existing_photo_id: int | None = Form(None, description="已有照片 ID（与 file 互斥）"),
    db: AsyncSession = Depends(get_db),
) -> PhotoResponse:
    parent_photo = await db.get(Photo, parent_id)
    if parent_photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"原图 id={parent_id} 不存在")
    if not parent_photo.is_confirmed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该原图尚未确认，无法关联精修图")
    if parent_photo.process_state != ProcessState.raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="parent_id 必须指向 process_state=raw 的照片")

    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"项目 id={project_id} 不存在")

    max_version = (await db.execute(
        select(sa_func.coalesce(sa_func.max(Photo.version), 0))
        .where(Photo.parent_id == parent_id, Photo.process_state == ProcessState.retouched)
    )).scalar() or 0
    new_version = max_version + 1

    if existing_photo_id is not None:
        existing_photo = await db.get(Photo, existing_photo_id)
        if existing_photo is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"照片 id={existing_photo_id} 不存在")
        if existing_photo.project_id != project_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="照片不属于该项目")

        existing_photo.process_state = ProcessState.retouched
        existing_photo.parent_id = parent_id
        existing_photo.target_id = target_id
        existing_photo.version = new_version
        existing_photo.revision_notes = revision_notes
        await db.commit()
        await db.refresh(existing_photo)

        return PhotoResponse(
            id=existing_photo.id,
            project_id=existing_photo.project_id,
            target_id=existing_photo.target_id,
            parent_id=existing_photo.parent_id,
            display_id=existing_photo.display_id,
            version=existing_photo.version,
            is_confirmed=existing_photo.is_confirmed,
            original_path=existing_photo.original_path,
            original_filename=existing_photo.original_filename,
            thumbnail_path=existing_photo.thumbnail_path,
            status=existing_photo.status.value,
            process_state=existing_photo.process_state.value,
            client_notes=existing_photo.client_notes,
            revision_notes=existing_photo.revision_notes,
        )

    if file is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="必须上传文件或提供 existing_photo_id")

    file_bytes = await file.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    suffix = Path(file.filename).suffix.lower() if file.filename else ".jpg"

    folder = NAS_ROOT / str(project_id)
    raw_dir = folder / "retouched"
    thumb_dir = folder / "thumb"

    saved_path, thumb_path, shot_at = await run_in_threadpool(
        _save_and_thumbnail, raw_dir, thumb_dir, file_bytes, suffix
    )

    display_id = await _next_display_id(db, project_id)

    photo = Photo(
        project_id=project_id,
        target_id=target_id,
        parent_id=parent_id,
        display_id=display_id,
        version=new_version,
        original_path=str(saved_path),
        original_filename=file.filename if file else None,
        file_hash=file_hash,
        thumbnail_path=str(thumb_path),
        process_state=ProcessState.retouched,
        revision_notes=revision_notes,
        shot_at=shot_at,
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    return PhotoResponse(
        id=photo.id,
        project_id=photo.project_id,
        target_id=photo.target_id,
        parent_id=photo.parent_id,
        display_id=photo.display_id,
        version=photo.version,
        is_confirmed=photo.is_confirmed,
        original_path=photo.original_path,
        original_filename=photo.original_filename,
        thumbnail_path=photo.thumbnail_path,
        status=photo.status.value,
        process_state=photo.process_state.value,
        client_notes=photo.client_notes,
        revision_notes=photo.revision_notes,
    )
# ── 更新备注（修改说明 / 客户备注）──────────────────────────

@router.patch(
    "/{photo_id}/notes",
    summary="更新照片备注（revision_notes / client_notes）",
)
async def update_photo_notes(
    photo_id: int,
    body: UpdateNotesRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    photo = await db.get(Photo, photo_id)
    if photo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"照片 id={photo_id} 不存在")

    if body.client_notes is not None:
        photo.client_notes = body.client_notes
    if body.revision_notes is not None:
        photo.revision_notes = body.revision_notes

    await db.commit()

    return {"code": 200, "msg": "备注更新成功", "data": None}
