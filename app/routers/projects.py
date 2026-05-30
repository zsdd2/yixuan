"""
routers/projects.py —— 项目管理相关接口
"""
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote
import hashlib
import io
import zipfile

from fastapi import APIRouter, Depends, Form, HTTPException, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func as sa_func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUser
from app.models import CategoryType, Client, Photo, PhotoStatus, ProcessState, Project, ProjectGroup, ProjectStatus, ProjectTag, ProjectTarget, ProjectTemplate, SystemTargetDictionary, TargetReferenceAsset, TargetStatus, TemplateTarget, User, UserRole, photo_tags, user_project_access
from app.schemas.project_schema import (
    ArchiveResponse,
    ProjectCreate,
    ProjectDetailResponse,
    ProjectGroupCreate,
    ProjectGroupListResponse,
    ProjectGroupResponse,
    ProjectGroupUpdate,
    ProjectInList,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.schemas.photo_schema import PhotoInList, PhotoListResponse, PhotoResponse
from app.schemas.target_schema import (
    TargetCreate,
    TargetListResponse,
    TargetResponse,
    TargetUpdate,
)
from app.routers.photos import _save_and_thumbnail, _next_display_id
from app.logic.status_manager import compute_project_status, compute_target_status

from sqlalchemy.orm import selectinload

import os
NAS_ROOT = Path(os.environ.get("NAS_MOUNT_PATH", "/mnt/nas_data"))

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


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


# ── 项目列表 ─────────────────────────────────────────────

@router.get(
    "",
    response_model=ProjectListResponse,
    summary="获取项目列表",
)
async def list_projects(
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="模糊搜索项目名称、编号或客户名称"),
    sort_by: str = Query("deadline", description="排序方式: deadline | photo_count"),
    status_filter: str | None = Query(None, description="状态筛选: active|archived|deleted|completed"),
    client_id: int | None = Query(None, description="按客户ID筛选"),
    template_id: int | None = Query(None, description="按模板ID筛选"),
    min_photo_count: int | None = Query(None, ge=0, description="最少图量"),
    max_photo_count: int | None = Query(None, ge=0, description="最多图量"),
    date_from: str | None = Query(None, description="创建时间起 YYYY-MM-DD"),
    date_to: str | None = Query(None, description="创建时间止 YYYY-MM-DD"),
    include_completed: bool = Query(False, description="(deprecated) 使用 status_filter 替代"),
    include_deleted: bool = Query(False, description="(deprecated) 使用 status_filter 替代"),
    db: AsyncSession = Depends(get_db),
) -> ProjectListResponse:
    from sqlalchemy import or_, cast, String
    from datetime import datetime as dt
    base_where = []

    # ── RBAC 权限过滤 ──────────────────────────────────────
    if current_user.role not in (UserRole.super_admin, UserRole.admin):
        allowed_project_ids = (await db.execute(
            select(user_project_access.c.project_id).where(user_project_access.c.user_id == current_user.id)
        )).scalars().all()
        if allowed_project_ids:
            base_where.append(Project.id.in_(allowed_project_ids))
        else:
            base_where.append(Project.id == -1)
    # super_admin 和 admin 可以看到所有项目，无需额外过滤

    if status_filter:
        if status_filter == "active":
            base_where.append(Project.archived_at.is_(None))
            base_where.append(Project.deleted_at.is_(None))
        elif status_filter == "archived":
            base_where.append(Project.archived_at.isnot(None))
            base_where.append(Project.deleted_at.is_(None))
        elif status_filter == "deleted":
            base_where.append(Project.deleted_at.isnot(None))
    else:
        if not include_deleted:
            base_where.append(Project.deleted_at.is_(None))

    if client_id is not None:
        base_where.append(Project.client_id == client_id)
    if template_id is not None:
        base_where.append(Project.template_id == template_id)

    if date_from:
        try:
            base_where.append(Project.created_at >= dt.strptime(date_from, "%Y-%m-%d"))
        except ValueError:
            pass
    if date_to:
        try:
            base_where.append(Project.created_at < dt.strptime(date_to, "%Y-%m-%d").replace(hour=23, minute=59, second=59))
        except ValueError:
            pass

    if search:
        keyword = f"%{search}%"
        matching_client_ids_stmt = select(Client.id).where(Client.name.ilike(keyword))
        base_where.append(or_(
            Project.name.ilike(keyword),
            (Project.client_prefix + cast(Project.serial_number, String)).ilike(keyword),
            Project.client_id.in_(matching_client_ids_stmt),
        ))

    if min_photo_count is not None or max_photo_count is not None:
        photo_cnt_sub = (
            select(Photo.project_id, sa_func.count(Photo.id).label("cnt"))
            .where(Photo.deleted_at.is_(None))
            .group_by(Photo.project_id)
            .subquery()
        )
        if min_photo_count is not None:
            having_ids = select(photo_cnt_sub.c.project_id).where(photo_cnt_sub.c.cnt >= min_photo_count)
            base_where.append(Project.id.in_(having_ids))
        if max_photo_count is not None:
            having_ids_max = select(photo_cnt_sub.c.project_id).where(photo_cnt_sub.c.cnt <= max_photo_count)
            base_where.append(Project.id.in_(having_ids_max))

    count_stmt = select(sa_func.count(Project.id)).where(*base_where) if base_where else select(sa_func.count(Project.id))
    total = (await db.execute(count_stmt)).scalar() or 0

    projects_stmt = select(Project)
    for w in base_where:
        projects_stmt = projects_stmt.where(w)

    if sort_by == "photo_count":
        photo_cnt_sub = (
            select(Photo.project_id, sa_func.count(Photo.id).label("cnt"))
            .where(Photo.deleted_at.is_(None))
            .group_by(Photo.project_id)
            .subquery()
        )
        projects_stmt = (
            projects_stmt
            .outerjoin(photo_cnt_sub, Project.id == photo_cnt_sub.c.project_id)
            .order_by(photo_cnt_sub.c.cnt.desc().nulls_last())
        )
    else:
        projects_stmt = projects_stmt.order_by(
            Project.estimated_end_time.asc().nulls_last(),
            Project.created_at.desc(),
        )

    projects_stmt = projects_stmt.offset(skip).limit(limit)
    projects = (await db.execute(projects_stmt)).scalars().all()

    project_ids = [p.id for p in projects]
    photo_counts: dict[int, int] = {}
    target_counts: dict[int, int] = {}
    white_target_counts: dict[int, int] = {}
    scene_target_counts: dict[int, int] = {}
    white_completed_counts: dict[int, int] = {}
    scene_completed_counts: dict[int, int] = {}

    if project_ids:
        pc_stmt = (
            select(Photo.project_id, sa_func.count(Photo.id))
            .where(
                Photo.project_id.in_(project_ids),
                Photo.deleted_at.is_(None)
            )
            .group_by(Photo.project_id)
        )
        photo_counts = dict((await db.execute(pc_stmt)).all())

        tc_stmt = (
            select(ProjectTarget.project_id, sa_func.count(ProjectTarget.id))
            .where(
                ProjectTarget.project_id.in_(project_ids),
                ProjectTarget.deleted_at.is_(None)
            )
            .group_by(ProjectTarget.project_id)
        )
        target_counts = dict((await db.execute(tc_stmt)).all())

        wt_stmt = (
            select(ProjectTarget.project_id, sa_func.count(ProjectTarget.id))
            .where(
                ProjectTarget.project_id.in_(project_ids),
                ProjectTarget.category_type == CategoryType.white,
                ProjectTarget.deleted_at.is_(None)
            )
            .group_by(ProjectTarget.project_id)
        )
        white_target_counts = dict((await db.execute(wt_stmt)).all())

        st_stmt = (
            select(ProjectTarget.project_id, sa_func.count(ProjectTarget.id))
            .where(
                ProjectTarget.project_id.in_(project_ids),
                ProjectTarget.category_type == CategoryType.scene,
                ProjectTarget.deleted_at.is_(None)
            )
            .group_by(ProjectTarget.project_id)
        )
        scene_target_counts = dict((await db.execute(st_stmt)).all())

        wc_stmt = (
            select(ProjectTarget.project_id, sa_func.count(ProjectTarget.id))
            .where(
                ProjectTarget.project_id.in_(project_ids),
                ProjectTarget.category_type == CategoryType.white,
                ProjectTarget.target_status == TargetStatus.completed,
                ProjectTarget.deleted_at.is_(None)
            )
            .group_by(ProjectTarget.project_id)
        )
        white_completed_counts = dict((await db.execute(wc_stmt)).all())

        sc_stmt = (
            select(ProjectTarget.project_id, sa_func.count(ProjectTarget.id))
            .where(
                ProjectTarget.project_id.in_(project_ids),
                ProjectTarget.category_type == CategoryType.scene,
                ProjectTarget.target_status == TargetStatus.completed,
                ProjectTarget.deleted_at.is_(None)
            )
            .group_by(ProjectTarget.project_id)
        )
        scene_completed_counts = dict((await db.execute(sc_stmt)).all())

    client_ids = list({p.client_id for p in projects})
    client_names: dict[int, str] = {}
    if client_ids:
        client_stmt = select(Client.id, Client.name).where(Client.id.in_(client_ids))
        client_names = dict((await db.execute(client_stmt)).all())

    template_ids = list({p.template_id for p in projects if p.template_id is not None})
    template_names: dict[int, str] = {}
    if template_ids:
        tpl_stmt = select(ProjectTemplate.id, ProjectTemplate.name).where(ProjectTemplate.id.in_(template_ids))
        template_names = dict((await db.execute(tpl_stmt)).all())

    completed_target_counts: dict[int, int] = {}
    if project_ids:
        ctc_stmt = (
            select(ProjectTarget.project_id, sa_func.count(ProjectTarget.id))
            .where(
                ProjectTarget.project_id.in_(project_ids),
                ProjectTarget.target_status == TargetStatus.completed,
                ProjectTarget.deleted_at.is_(None)
            )
            .group_by(ProjectTarget.project_id)
        )
        completed_target_counts = dict((await db.execute(ctc_stmt)).all())

    items_all = [
        ProjectInList(
            id=p.id,
            name=p.name,
            display_id=p.display_id,
            cover_image=p.cover_image,
            client_name=client_names.get(p.client_id),
            template_name=template_names.get(p.template_id) if p.template_id else None,
            shooting_type=p.shooting_type,
            created_by=p.created_by,
            photo_count=photo_counts.get(p.id, 0),
            target_count=target_counts.get(p.id, 0),
            completed_target_count=completed_target_counts.get(p.id, 0),
            white_target=white_target_counts.get(p.id, 0),
            scene_target=scene_target_counts.get(p.id, 0),
            white_count=white_completed_counts.get(p.id, 0),
            scene_count=scene_completed_counts.get(p.id, 0),
            white_completed=white_completed_counts.get(p.id, 0),
            scene_completed=scene_completed_counts.get(p.id, 0),
            estimated_end_time=p.estimated_end_time.isoformat() if p.estimated_end_time else None,
            archived_at=p.archived_at.isoformat() if p.archived_at else None,
            deleted_at=p.deleted_at.isoformat() if p.deleted_at else None,
            description=p.description,
            project_status=p.project_status.value if p.project_status else "not_started",
            created_at=p.created_at.isoformat(),
        )
        for p in projects
    ]

    if not status_filter and not include_completed:
        items_all = [
            item for item in items_all
            if item.archived_at is None
        ]

    return ProjectListResponse(total=total, items=items_all, skip=skip, limit=limit)


# ── 创建项目 ─────────────────────────────────────────────

@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建项目",
)
async def create_project(
    body: ProjectCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    user_id: int = current_user.id

    client = await db.get(Client, body.client_id)
    if client is None or client.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"客户 id={body.client_id} 不存在",
        )

    project = Project(
        name=body.name,
        client_prefix=client.prefix,
        template_id=body.template_id,
        shooting_type=body.shooting_type,
        estimated_end_time=body.estimated_end_time,
        description=body.description,
        client_id=client.id,
        created_by=user_id,
    )
    db.add(project)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="项目编号生成冲突，请重试",
        )
    await db.refresh(project)

    project_dir = NAS_ROOT / str(project.id)
    try:
        (project_dir / "raw").mkdir(parents=True, exist_ok=True)
        (project_dir / "thumb").mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"无法创建项目文件夹：{exc}",
        )

    await db.commit()

    if body.template_id is not None:
        tpl_targets = (await db.execute(
            select(TemplateTarget)
            .where(TemplateTarget.template_id == body.template_id)
            .order_by(TemplateTarget.sort_order)
        )).scalars().all()
        for tt in tpl_targets:
            pt = ProjectTarget(
                project_id=project.id,
                name=tt.name,
                category_type=tt.category_type,
                sample_path=None,
                requirement_desc=tt.requirement_desc,
                sort_order=tt.sort_order,
            )
            db.add(pt)
        if tpl_targets:
            await db.commit()

    return ProjectResponse(
        id=project.id,
        name=project.name,
        display_id=project.display_id,
        created_by=project.created_by,
        folder_path=str(project_dir),
    )


# ── 单项目详情 ───────────────────────────────────────────

@router.get(
    "/{project_id}",
    response_model=ProjectDetailResponse,
    summary="获取单项目详情",
)
async def get_project_detail(
    project_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectDetailResponse:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    photo_count = (await db.execute(
        select(sa_func.count(Photo.id)).where(
            Photo.project_id == project_id,
            Photo.deleted_at.is_(None)
        )
    )).scalar() or 0

    target_count = (await db.execute(
        select(sa_func.count(ProjectTarget.id)).where(
            ProjectTarget.project_id == project_id,
            ProjectTarget.deleted_at.is_(None)
        )
    )).scalar() or 0

    client_name: str | None = None
    client = await db.get(Client, project.client_id)
    if client:
        client_name = client.name

    return ProjectDetailResponse(
        id=project.id,
        name=project.name,
        display_id=project.display_id,
        cover_image=project.cover_image,
        client_id=project.client_id,
        client_name=client_name,
        created_by=project.created_by,
        white_target=project.white_target,
        scene_target=project.scene_target,
        white_count=0,
        scene_count=0,
        estimated_end_time=project.estimated_end_time.isoformat() if project.estimated_end_time else None,
        archived_at=project.archived_at.isoformat() if project.archived_at else None,
        description=project.description,
        created_at=project.created_at.isoformat(),
        photo_count=photo_count,
        target_count=target_count,
        project_status=project.project_status.value if project.project_status else "not_started",
    )


# ── 目标槽位 (Targets) ──────────────────────────────────

@router.get("/{project_id}/groups", response_model=ProjectGroupListResponse, summary="获取项目组合")
async def list_project_groups(
    project_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectGroupListResponse:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"项目 id={project_id} 不存在")
    groups = (await db.execute(
        select(ProjectGroup)
        .where(ProjectGroup.project_id == project_id, ProjectGroup.deleted_at.is_(None))
        .order_by(ProjectGroup.sort_order, ProjectGroup.id)
    )).scalars().all()
    group_ids = [g.id for g in groups]
    target_counts: dict[int, int] = {}
    photo_counts: dict[int, int] = {}
    if group_ids:
        target_counts = dict((await db.execute(
            select(ProjectTarget.group_id, sa_func.count(ProjectTarget.id))
            .where(ProjectTarget.group_id.in_(group_ids), ProjectTarget.deleted_at.is_(None))
            .group_by(ProjectTarget.group_id)
        )).all())
        photo_counts = dict((await db.execute(
            select(Photo.group_id, sa_func.count(Photo.id))
            .where(Photo.group_id.in_(group_ids), Photo.deleted_at.is_(None))
            .group_by(Photo.group_id)
        )).all())
    return ProjectGroupListResponse(
        items=[
            ProjectGroupResponse(
                id=g.id,
                project_id=g.project_id,
                name=g.name,
                description=g.description,
                sort_order=g.sort_order,
                target_count=target_counts.get(g.id, 0),
                photo_count=photo_counts.get(g.id, 0),
                created_at=g.created_at.isoformat(),
            )
            for g in groups
        ],
        total=len(groups),
    )


@router.post("/{project_id}/groups", response_model=ProjectGroupResponse, status_code=status.HTTP_201_CREATED, summary="创建项目组合")
async def create_project_group(
    project_id: int,
    body: ProjectGroupCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectGroupResponse:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"项目 id={project_id} 不存在")
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="组合名称不能为空")
    existing = await db.scalar(select(ProjectGroup).where(ProjectGroup.project_id == project_id, ProjectGroup.name == name, ProjectGroup.deleted_at.is_(None)))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"组合「{name}」已存在")
    group = ProjectGroup(project_id=project_id, name=name, description=body.description, sort_order=body.sort_order)
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return ProjectGroupResponse(id=group.id, project_id=group.project_id, name=group.name, description=group.description, sort_order=group.sort_order, target_count=0, photo_count=0, created_at=group.created_at.isoformat())


@router.patch("/{project_id}/groups/{group_id}", response_model=ProjectGroupResponse, summary="更新项目组合")
async def update_project_group(
    project_id: int,
    group_id: int,
    body: ProjectGroupUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectGroupResponse:
    group = await _ensure_group(db, project_id, group_id)
    update_data = body.model_dump(exclude_unset=True)
    if "name" in update_data and update_data["name"] is not None:
        name = update_data.pop("name").strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="组合名称不能为空")
        duplicate = await db.scalar(select(ProjectGroup).where(ProjectGroup.project_id == project_id, ProjectGroup.name == name, ProjectGroup.id != group_id, ProjectGroup.deleted_at.is_(None)))
        if duplicate is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"组合「{name}」已存在")
        group.name = name
    for field, value in update_data.items():
        setattr(group, field, value)
    await db.commit()
    await db.refresh(group)
    target_count = (await db.execute(select(sa_func.count(ProjectTarget.id)).where(ProjectTarget.group_id == group_id, ProjectTarget.deleted_at.is_(None)))).scalar() or 0
    photo_count = (await db.execute(select(sa_func.count(Photo.id)).where(Photo.group_id == group_id, Photo.deleted_at.is_(None)))).scalar() or 0
    return ProjectGroupResponse(id=group.id, project_id=group.project_id, name=group.name, description=group.description, sort_order=group.sort_order, target_count=target_count, photo_count=photo_count, created_at=group.created_at.isoformat())


@router.delete("/{project_id}/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除项目组合")
async def delete_project_group(
    project_id: int,
    group_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    group = await _ensure_group(db, project_id, group_id)
    group.deleted_at = datetime.now(timezone.utc)
    for target in (await db.execute(select(ProjectTarget).where(ProjectTarget.group_id == group_id))).scalars().all():
        target.group_id = None
    for photo in (await db.execute(select(Photo).where(Photo.group_id == group_id))).scalars().all():
        photo.group_id = None
    await db.commit()


@router.post(
    "/{project_id}/targets",
    response_model=TargetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建目标槽位",
)
async def create_target(
    project_id: int,
    body: TargetCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TargetResponse:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    group = await _ensure_group(db, project_id, body.group_id)
    target = ProjectTarget(
        project_id=project_id,
        group_id=body.group_id,
        name=body.name,
        category_type=CategoryType(body.category_type),
        sample_path=body.sample_path,
        requirement_desc=body.requirement_desc,
        sort_order=body.sort_order,
    )
    db.add(target)
    await db.flush()
    await db.refresh(target)
    await db.commit()

    return TargetResponse(
        id=target.id,
        project_id=target.project_id,
        group_id=target.group_id,
        group_name=group.name if group else None,
        name=target.name,
        category_type=target.category_type.value,
        target_status=target.target_status.value,
        is_manual=target.is_manual,
        sample_path=target.sample_path,
        requirement_desc=target.requirement_desc,
        sort_order=target.sort_order,
        photo_count=0,
        raw_count=0,
        retouched_count=0,
        final_count=0,
        created_at=target.created_at.isoformat(),
    )


@router.get(
    "/{project_id}/available-targets",
    summary="获取项目可用目标名称（通用+模板字典合并）",
)
async def get_available_targets(
    project_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"项目 id={project_id} 不存在")

    global_entries = (await db.execute(
        select(SystemTargetDictionary).order_by(SystemTargetDictionary.id)
    )).scalars().all()

    items: list[dict] = []
    seen_names: set[str] = set()
    for e in global_entries:
        items.append({"name": e.name, "category_type": e.category_type.value, "source": "global"})
        seen_names.add(e.name)

    if project.template_id:
        tpl = await db.get(ProjectTemplate, project.template_id)
        if tpl and tpl.target_dictionary:
            for d in tpl.target_dictionary:
                if d.get("name") and d["name"] not in seen_names:
                    items.append({"name": d["name"], "category_type": d.get("category_type", "white"), "source": "template"})
                    seen_names.add(d["name"])

    existing_targets = (await db.execute(
        select(ProjectTarget.name).where(
            ProjectTarget.project_id == project_id,
            ProjectTarget.deleted_at.is_(None)
        )
    )).scalars().all()
    existing_names = set(existing_targets)

    for item in items:
        item["used"] = item["name"] in existing_names

    return {"items": items, "total": len(items)}


@router.post(
    "/{project_id}/dictionary-entry",
    status_code=status.HTTP_201_CREATED,
    summary="快捷向关联模板追加字典词条",
)
async def add_dictionary_entry_to_template(
    project_id: int,
    body: TargetCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"项目 id={project_id} 不存在")
    if project.template_id is None:
        raise HTTPException(status_code=400, detail="该项目未关联模板，无法追加字典词条")

    tpl = await db.get(ProjectTemplate, project.template_id)
    if tpl is None:
        raise HTTPException(status_code=404, detail="关联模板不存在")

    dictionary = list(tpl.target_dictionary or [])
    existing_names = {d.get("name") for d in dictionary}
    if body.name in existing_names:
        raise HTTPException(status_code=409, detail=f"词条 '{body.name}' 已存在于模板字典中")

    dictionary.append({"name": body.name, "category_type": body.category_type})
    tpl.target_dictionary = dictionary
    await db.commit()

    return {"code": 200, "msg": f"词条 '{body.name}' 已追加到模板字典", "data": {"name": body.name, "category_type": body.category_type}}


@router.get(
    "/{project_id}/targets",
    response_model=TargetListResponse,
    summary="获取项目的目标槽位清单",
)
async def list_targets(
    project_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TargetListResponse:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    targets_stmt = (
        select(ProjectTarget)
        .where(
            ProjectTarget.project_id == project_id,
            ProjectTarget.deleted_at.is_(None)
        )
        .order_by(ProjectTarget.sort_order, ProjectTarget.id)
    )
    targets = (await db.execute(targets_stmt)).scalars().all()

    target_ids = [t.id for t in targets]
    group_ids = list({t.group_id for t in targets if t.group_id is not None})
    group_map: dict[int, ProjectGroup] = {}
    if group_ids:
        group_map = {
            g.id: g
            for g in (await db.execute(
                select(ProjectGroup).where(ProjectGroup.id.in_(group_ids))
            )).scalars().all()
        }
    photo_counts: dict[int, int] = {}
    raw_counts: dict[int, int] = {}
    retouched_counts: dict[int, int] = {}
    final_counts: dict[int, int] = {}
    confirmed_counts: dict[int, int] = {}
    if target_ids:
        pc_stmt = (
            select(Photo.target_id, sa_func.count(Photo.id))
            .where(
                Photo.target_id.in_(target_ids),
                Photo.deleted_at.is_(None)
            )
            .group_by(Photo.target_id)
        )
        photo_counts = dict((await db.execute(pc_stmt)).all())

        ps_stmt = (
            select(Photo.target_id, Photo.process_state, sa_func.count(Photo.id))
            .where(
                Photo.target_id.in_(target_ids),
                Photo.deleted_at.is_(None)
            )
            .group_by(Photo.target_id, Photo.process_state)
        )
        for tid, pstate, cnt in (await db.execute(ps_stmt)).all():
            if pstate == ProcessState.raw:
                raw_counts[tid] = cnt
            elif pstate == ProcessState.retouched:
                retouched_counts[tid] = cnt
            elif pstate == ProcessState.final:
                final_counts[tid] = cnt

        confirmed_stmt = (
            select(Photo.target_id, sa_func.count(Photo.id))
            .where(
                Photo.target_id.in_(target_ids),
                Photo.is_confirmed.is_(True),
                Photo.process_state == ProcessState.raw,
                Photo.deleted_at.is_(None)
            )
            .group_by(Photo.target_id)
        )
        confirmed_counts = dict((await db.execute(confirmed_stmt)).all())

    status_order = {"not_started": 0, "shooting": 1, "retouching": 2, "client_review": 3, "completed": 4}

    items: list[TargetResponse] = []
    for t in targets:
        pc = photo_counts.get(t.id, 0)
        rc = raw_counts.get(t.id, 0)
        rtc = retouched_counts.get(t.id, 0)
        fc = final_counts.get(t.id, 0)

        if t.is_manual:
            computed_status = t.target_status.value
        else:
            if pc == 0:
                computed_status = "not_started"
            elif fc > 0:
                computed_status = "completed"
            elif rtc > 0 or fc > 0:
                computed_status = "retouching"
            else:
                computed_status = "shooting"

        items.append(TargetResponse(
            id=t.id,
            project_id=t.project_id,
            group_id=t.group_id,
            group_name=group_map[t.group_id].name if t.group_id in group_map else None,
            name=t.name,
            category_type=t.category_type.value,
            target_status=computed_status,
            is_manual=t.is_manual,
            sample_path=t.sample_path,
            requirement_desc=t.requirement_desc,
            sort_order=t.sort_order,
            photo_count=pc,
            raw_count=rc,
            confirmed_count=confirmed_counts.get(t.id, 0),
            retouched_count=rtc,
            final_count=fc,
            created_at=t.created_at.isoformat(),
        ))

    items.sort(key=lambda x: status_order.get(x.target_status, 99))

    return TargetListResponse(items=items, total=len(items))


# ── 更新目标 ───────────────────────────────────────────

@router.patch(
    "/{project_id}/targets/{target_id}",
    response_model=TargetResponse,
    summary="更新目标槽位",
)
async def update_target(
    project_id: int,
    target_id: int,
    body: TargetUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TargetResponse:
    target = await db.get(ProjectTarget, target_id)
    if target is None or target.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目标 id={target_id} 不存在或不属于该项目",
        )

    update_data = body.model_dump(exclude_unset=True)

    if "target_status" in update_data and update_data["target_status"] is not None:
        try:
            target.target_status = TargetStatus(update_data.pop("target_status"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的状态值",
            )
        target.is_manual = True

    if "category_type" in update_data and update_data["category_type"] is not None:
        try:
            target.category_type = CategoryType(update_data.pop("category_type"))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="无效的分类值",
            )

    group: ProjectGroup | None = None
    if "group_id" in update_data:
        group = await _ensure_group(db, project_id, update_data.pop("group_id"))
        target.group_id = group.id if group else None
    elif target.group_id is not None:
        group = await db.get(ProjectGroup, target.group_id)

    for field, value in update_data.items():
        if value is not None:
            setattr(target, field, value)

    await db.commit()
    await db.refresh(target)

    pc_stmt = select(sa_func.count(Photo.id)).where(
        Photo.target_id == target_id,
        Photo.deleted_at.is_(None)
    )
    photo_count = (await db.execute(pc_stmt)).scalar() or 0

    return TargetResponse(
        id=target.id,
        project_id=target.project_id,
        group_id=target.group_id,
        group_name=group.name if group else None,
        name=target.name,
        category_type=target.category_type.value,
        target_status=target.target_status.value,
        is_manual=target.is_manual,
        sample_path=target.sample_path,
        requirement_desc=target.requirement_desc,
        sort_order=target.sort_order,
        photo_count=photo_count,
        raw_count=0,
        retouched_count=0,
        final_count=0,
        created_at=target.created_at.isoformat(),
    )


# ── 删除目标 ───────────────────────────────────────────

@router.delete(
    "/{project_id}/targets/{target_id}",
    summary="删除目标槽位（软删除）",
)
async def delete_target(
    project_id: int,
    target_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(ProjectTarget, target_id)
    if target is None or target.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目标 id={target_id} 不存在或不属于该项目",
        )

    if target.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="目标已被删除",
        )

    from sqlalchemy import update
    # 软删除：设置 deleted_at 时间戳
    target.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    return {"code": 200, "msg": "目标已删除", "data": None}


# ── 标记完成 ───────────────────────────────────────────

@router.post(
    "/{project_id}/targets/{target_id}/complete",
    response_model=TargetResponse,
    summary="标记目标为已完成",
)
async def complete_target(
    project_id: int,
    target_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TargetResponse:
    target = await db.get(ProjectTarget, target_id)
    if target is None or target.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"目标 id={target_id} 不存在或不属于该项目",
        )

    target.target_status = TargetStatus.completed
    target.is_manual = True
    await db.commit()
    await db.refresh(target)

    pc_stmt = select(sa_func.count(Photo.id)).where(
        Photo.target_id == target_id,
        Photo.deleted_at.is_(None)
    )
    photo_count = (await db.execute(pc_stmt)).scalar() or 0

    return TargetResponse(
        id=target.id,
        project_id=target.project_id,
        name=target.name,
        category_type=target.category_type.value,
        target_status=target.target_status.value,
        is_manual=target.is_manual,
        sample_path=target.sample_path,
        requirement_desc=target.requirement_desc,
        sort_order=target.sort_order,
        photo_count=photo_count,
        raw_count=0,
        retouched_count=0,
        final_count=0,
        created_at=target.created_at.isoformat(),
    )


@router.get("/{project_id}/targets/{target_id}/references", summary="获取目标参考图")
async def list_target_references(
    project_id: int,
    target_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    target = await db.get(ProjectTarget, target_id)
    if target is None or target.project_id != project_id or target.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="目标不存在")

    rows = (await db.execute(
        select(TargetReferenceAsset)
        .where(TargetReferenceAsset.target_id == target_id)
        .options(selectinload(TargetReferenceAsset.photo))
        .order_by(TargetReferenceAsset.asset_type, TargetReferenceAsset.version.desc(), TargetReferenceAsset.id.desc())
    )).scalars().all()

    return {
        "items": [
            {
                "id": item.id,
                "asset_type": item.asset_type,
                "photo_id": item.photo_id,
                "version": item.version,
                "is_current": item.is_current,
                "notes": item.notes,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "photo": {
                    "id": item.photo.id,
                    "display_id": item.photo.display_id,
                    "original_filename": item.photo.original_filename,
                    "thumbnail_path": item.photo.thumbnail_path,
                    "original_path": item.photo.original_path,
                } if item.photo else None,
            }
            for item in rows
        ]
    }


@router.post("/{project_id}/targets/{target_id}/references", summary="设置目标参考图")
async def set_target_reference(
    project_id: int,
    target_id: int,
    body: dict,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    asset_type = body.get("asset_type")
    photo_id = body.get("photo_id")
    notes = body.get("notes")
    if asset_type not in {"scene_goal", "empty_scene"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="asset_type 必须是 scene_goal 或 empty_scene")
    if not photo_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="photo_id 不能为空")

    target = await db.get(ProjectTarget, target_id)
    if target is None or target.project_id != project_id or target.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="目标不存在")
    photo = await db.get(Photo, int(photo_id))
    if photo is None or photo.project_id != project_id or photo.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="图片不属于该项目")

    if asset_type == "empty_scene":
        current_rows = (await db.execute(
            select(TargetReferenceAsset).where(
                TargetReferenceAsset.target_id == target_id,
                TargetReferenceAsset.asset_type == asset_type,
                TargetReferenceAsset.is_current == True,
            )
        )).scalars().all()
        for item in current_rows:
            item.is_current = False
        max_version = (await db.execute(
            select(sa_func.coalesce(sa_func.max(TargetReferenceAsset.version), 0)).where(
                TargetReferenceAsset.target_id == target_id,
                TargetReferenceAsset.asset_type == asset_type,
            )
        )).scalar() or 0
        version = max_version + 1
    else:
        existing = await db.scalar(
            select(TargetReferenceAsset).where(
                TargetReferenceAsset.target_id == target_id,
                TargetReferenceAsset.asset_type == asset_type,
                TargetReferenceAsset.photo_id == int(photo_id),
                TargetReferenceAsset.is_current == True,
            )
        )
        if existing is not None:
            return {"code": 200, "msg": "参考图已存在", "data": {"id": existing.id}}
        version = 1

    ref = TargetReferenceAsset(
        target_id=target_id,
        asset_type=asset_type,
        photo_id=int(photo_id),
        version=version,
        is_current=True,
        notes=notes,
    )
    db.add(ref)
    await db.commit()
    await db.refresh(ref)
    return {"code": 200, "msg": "参考图已更新", "data": {"id": ref.id}}


# ── 项目照片列表 ─────────────────────────────────────────

@router.get(
    "/{project_id}/photos",
    response_model=PhotoListResponse,
    summary="获取项目照片列表",
)
async def get_project_photos(
    project_id: int,
    current_user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    status_filter: str | None = Query(None, alias="status", description="按状态过滤"),
    display_id: int | None = Query(None, description="按项目内编号过滤"),
    tag_id: int | None = Query(None, description="按标签ID过滤"),
    shot_dates: str | None = Query(None, description="逗号分隔的拍摄日期 YYYY-MM-DD，特殊值 'none' 表示无拍摄日期"),
    unassigned: bool = Query(False, description="仅返回未分配目标的照片 (target_id IS NULL)"),
    process_state: str | None = Query(None, description="按处理阶段过滤: raw/retouched/final"),
    is_confirmed: bool | None = Query(None, description="按确认状态过滤"),
    parent_id: int | None = Query(None, description="按源原图ID过滤"),
    group_id: int | None = Query(None, description="按组合/批次/商品组 ID 过滤"),
    target_id: int | None = Query(None, description="按目标槽位ID过滤"),
    db: AsyncSession = Depends(get_db),
) -> PhotoListResponse:
    from app.models import UserRole

    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    # ── RBAC 权限验证 ──────────────────────────────────────
    if current_user.role == UserRole.client:
        # 客户只能访问 customer_id = 自己 ID 的项目
        if project.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此项目",
            )
    elif current_user.role == UserRole.staff:
        # 员工只能访问自己创建的项目
        if project.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此项目",
            )
    # super_admin 和 admin 可以访问所有项目

    base_stmt = select(Photo).where(Photo.project_id == project_id)
    count_where = [Photo.project_id == project_id]

    if status_filter is not None:
        try:
            # Support comma-separated status values
            status_values = [s.strip() for s in status_filter.split(',')]
            status_enums = []
            for sv in status_values:
                status_enums.append(PhotoStatus(sv))
            base_stmt = base_stmt.where(Photo.status.in_(status_enums))
            count_where.append(Photo.status.in_(status_enums))
        except ValueError:
            valid = [s.value for s in PhotoStatus]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"无效的状态值，合法值：{valid}",
            )

    if display_id is not None:
        base_stmt = base_stmt.where(Photo.display_id == display_id)
        count_where.append(Photo.display_id == display_id)

    if tag_id is not None:
        base_stmt = base_stmt.join(photo_tags, photo_tags.c.photo_id == Photo.id).where(photo_tags.c.tag_id == tag_id)
        count_where.append(Photo.id.in_(select(photo_tags.c.photo_id).where(photo_tags.c.tag_id == tag_id)))

    if unassigned:
        base_stmt = base_stmt.where(Photo.target_id.is_(None))
        count_where.append(Photo.target_id.is_(None))

    if process_state is not None:
        try:
            ps_val = ProcessState(process_state)
        except ValueError:
            valid = [s.value for s in ProcessState]
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"无效的处理阶段 '{process_state}'，合法值：{valid}")
        base_stmt = base_stmt.where(Photo.process_state == ps_val)
        count_where.append(Photo.process_state == ps_val)

    if is_confirmed is not None:
        base_stmt = base_stmt.where(Photo.is_confirmed.is_(is_confirmed))
        count_where.append(Photo.is_confirmed.is_(is_confirmed))

    if parent_id is not None:
        base_stmt = base_stmt.where(Photo.parent_id == parent_id)
        count_where.append(Photo.parent_id == parent_id)

    if group_id is not None:
        base_stmt = base_stmt.where(Photo.group_id == group_id)
        count_where.append(Photo.group_id == group_id)

    if target_id is not None:
        base_stmt = base_stmt.where(Photo.target_id == target_id)
        count_where.append(Photo.target_id == target_id)

    if shot_dates is not None:
        from sqlalchemy import cast, Date, or_
        date_parts = [d.strip() for d in shot_dates.split(",") if d.strip()]
        date_conditions = []
        for dp in date_parts:
            if dp == "none":
                date_conditions.append(Photo.shot_at.is_(None))
            else:
                try:
                    parsed = datetime.strptime(dp, "%Y-%m-%d").date()
                    date_conditions.append(cast(Photo.shot_at, Date) == parsed)
                except ValueError:
                    continue
        if date_conditions:
            combined = or_(*date_conditions)
            base_stmt = base_stmt.where(combined)
            count_where.append(combined)

    count_stmt = select(sa_func.count(Photo.id)).where(*count_where)
    total = (await db.execute(count_stmt)).scalar() or 0

    photos_stmt = (
        base_stmt
        .order_by(Photo.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    photos = (await db.execute(photos_stmt)).scalars().all()

    photo_ids = [p.id for p in photos]
    target_ids = list({p.target_id for p in photos if p.target_id is not None})
    group_ids = list({p.group_id for p in photos if p.group_id is not None})
    tag_map: dict[int, list[int]] = {pid: [] for pid in photo_ids}
    target_map: dict[int, ProjectTarget] = {}
    group_map: dict[int, ProjectGroup] = {}
    if photo_ids:
        tag_rows = (await db.execute(
            select(photo_tags.c.photo_id, photo_tags.c.tag_id)
            .where(photo_tags.c.photo_id.in_(photo_ids))
        )).all()
        for pid, tid in tag_rows:
            tag_map[pid].append(tid)
    if target_ids:
        target_map = {
            t.id: t
            for t in (await db.execute(
                select(ProjectTarget).where(ProjectTarget.id.in_(target_ids))
            )).scalars().all()
        }
    if group_ids:
        group_map = {
            g.id: g
            for g in (await db.execute(
                select(ProjectGroup).where(ProjectGroup.id.in_(group_ids))
            )).scalars().all()
        }

    items = [
        PhotoInList(
            id=photo.id,
            project_id=photo.project_id,
            group_id=photo.group_id,
            target_id=photo.target_id,
            parent_id=photo.parent_id,
            display_id=photo.display_id,
            version=photo.version,
            is_confirmed=photo.is_confirmed,
            original_path=photo.original_path,
            thumbnail_path=photo.thumbnail_path,
            status=photo.status.value,
            process_state=photo.process_state.value,
            client_notes=photo.client_notes,
            revision_notes=photo.revision_notes,
            retouch_quality=getattr(photo, "retouch_quality", None),
            retouch_batch_id=getattr(photo, "retouch_batch_id", None),
            group_name=group_map[photo.group_id].name if photo.group_id in group_map else None,
            target_name=target_map[photo.target_id].name if photo.target_id in target_map else None,
            category_type=target_map[photo.target_id].category_type.value if photo.target_id in target_map else None,
            shot_at=photo.shot_at.isoformat() if photo.shot_at else None,
            tag_ids=tag_map.get(photo.id, []),
            deleted_at=photo.deleted_at.isoformat() if photo.deleted_at else None,
            created_at=photo.created_at.isoformat(),
        )
        for photo in photos
    ]

    return PhotoListResponse(total=total, items=items, skip=skip, limit=limit)


# ── 项目拍摄日期列表 ───────────────────────────────────────

@router.get(
    "/{project_id}/photos/shot-dates",
    summary="获取项目内所有不同拍摄日期",
)
async def get_shot_dates(
    project_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import cast, Date
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    date_stmt = (
        select(cast(Photo.shot_at, Date).label("shot_date"), sa_func.count(Photo.id).label("count"))
        .where(
            Photo.project_id == project_id,
            Photo.shot_at.isnot(None),
            Photo.deleted_at.is_(None)
        )
        .group_by("shot_date")
        .order_by("shot_date")
    )
    rows = (await db.execute(date_stmt)).all()

    null_count = (await db.execute(
        select(sa_func.count(Photo.id))
        .where(
            Photo.project_id == project_id,
            Photo.shot_at.is_(None),
            Photo.deleted_at.is_(None)
        )
    )).scalar() or 0

    dates = [{"date": str(row.shot_date), "count": row.count} for row in rows]
    if null_count > 0:
        dates.append({"date": "none", "count": null_count})

    return {"items": dates}


# ── 上传至项目 ───────────────────────────────────────────

@router.post(
    "/{project_id}/photos/upload",
    response_model=PhotoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="上传图片至指定项目（拖拽直传）",
)
async def upload_photo_to_project(
    project_id: int,
    file: UploadFile,
    current_user: CurrentUser,
    group_id: int | None = Form(None, description="组合/批次/商品组 ID"),
    target_id: int | None = Form(None, description="目标槽位 ID（可为空）"),
    process_state: str = Form("raw", description="入库阶段: raw/retouched/final"),
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
    from sqlalchemy import select as sa_select
    existing = await db.scalar(
        sa_select(Photo).where(Photo.project_id == project_id, Photo.file_hash == file_hash)
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

    display_id = await _next_display_id(db, project_id)
    photo = Photo(
        project_id=project_id,
        group_id=group_id,
        target_id=target_id,
        original_path=str(original_path),
        thumbnail_path=str(thumb_path),
        file_hash=file_hash,
        display_id=display_id,
        process_state=ps,
        shot_at=shot_at,
    )
    db.add(photo)
    await db.flush()
    await db.refresh(photo)
    await db.commit()

    return PhotoResponse(
        id=photo.id,
        project_id=photo.project_id,
        group_id=photo.group_id,
        group_name=group.name if group else None,
        target_id=photo.target_id,
        display_id=photo.display_id,
        original_path=photo.original_path,
        thumbnail_path=photo.thumbnail_path,
        status=photo.status.value,
        process_state=photo.process_state.value,
    )


# ── 归档 / 取消归档 ─────────────────────────────────────

@router.post(
    "/{project_id}/archive",
    response_model=ArchiveResponse,
    summary="归档项目（启动 15 天清理倒计时）",
)
async def archive_project(
    project_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ArchiveResponse:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    # ── RBAC 权限验证 ──────────────────────────────────────
    from app.models import UserRole
    if current_user.role == UserRole.client:
        # 客户只能归档关联到自己的项目
        if project.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此项目",
            )
    # staff、admin、super_admin 可以归档所有项目

    project.archived_at = datetime.now(timezone.utc)
    # 归档时自动设置为已完成状态
    project.project_status = ProjectStatus.completed
    await db.commit()
    await db.refresh(project)

    return ArchiveResponse(
        project_id=project.id,
        archived_at=project.archived_at.isoformat(),
        message="项目已归档并标记为已完成，15 天后将自动清理回收站内容",
    )


@router.post(
    "/{project_id}/unarchive",
    response_model=ArchiveResponse,
    summary="取消项目归档",
)
async def unarchive_project(
    project_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ArchiveResponse:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    # ── RBAC 权限验证 ──────────────────────────────────────
    from app.models import UserRole
    if current_user.role == UserRole.client:
        # 客户只能取消归档关联到自己的项目
        if project.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此项目",
            )
    # staff、admin、super_admin 可以取消归档所有项目

    project.archived_at = None
    await db.commit()
    return ArchiveResponse(
        project_id=project.id,
        archived_at="",
        message="项目已取消归档",
    )


# ── 更新项目 ───────────────────────────────────────────

@router.patch(
    "/{project_id}",
    summary="更新项目信息",
)
async def update_project(
    project_id: int,
    body: ProjectUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    # ── RBAC 权限验证 ──────────────────────────────────────
    from app.models import UserRole
    if current_user.role == UserRole.client:
        # 客户只能修改关联到自己的项目
        if project.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"无权访问此项目 (role={current_user.role.value}, customer_id={project.customer_id}, user_id={current_user.id})",
            )
    # staff、admin、super_admin 可以修改所有项目

    update_data = body.model_dump(exclude_unset=True)

    if "project_status" in update_data and update_data["project_status"] is not None:
        try:
            project.project_status = ProjectStatus(update_data.pop("project_status"))
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无效的项目状态值")

    for field, value in update_data.items():
        if value is not None:
            setattr(project, field, value)

    await db.commit()
    await db.refresh(project)

    return {
        "code": 200,
        "msg": "项目已更新",
        "data": {
            "id": project.id,
            "name": project.name,
            "estimated_end_time": project.estimated_end_time.isoformat() if project.estimated_end_time else None,
        },
    }


# ── 软删除项目（进回收站） ──────────────────────────────

@router.post(
    "/{project_id}/soft-delete",
    summary="软删除项目（移入回收站）",
)
async def soft_delete_project(
    project_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    if current_user.role not in (UserRole.super_admin, UserRole.admin):
        if not getattr(current_user, "can_delete_projects", False):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无删除项目权限")
        allowed = await db.scalar(
            select(user_project_access.c.project_id).where(
                user_project_access.c.user_id == current_user.id,
                user_project_access.c.project_id == project_id,
            )
        )
        if allowed is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此项目")

    project.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"code": 200, "msg": "项目已移入回收站", "data": None}


# ── 恢复项目 ───────────────────────────────────────────

@router.post(
    "/{project_id}/restore",
    summary="从回收站恢复项目",
)
async def restore_project(
    project_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    # ── RBAC 权限验证 ──────────────────────────────────────
    from app.models import UserRole
    if current_user.role == UserRole.client:
        # 客户只能恢复关联到自己的项目
        if project.customer_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此项目",
            )
    # staff、admin、super_admin 可以恢复所有项目

    project.deleted_at = None
    await db.commit()
    return {"code": 200, "msg": "项目已恢复", "data": None}


# ── 下载选中照片 ZIP ──────────────────────────────────

@router.get(
    "/{project_id}/photos/download",
    summary="下载选中照片 ZIP 压缩包",
)
async def download_selected_photos(
    project_id: int,
    current_user: CurrentUser,
    photo_ids: str = Query(..., description="逗号分隔的照片ID列表"),
    db: AsyncSession = Depends(get_db),
):
    """
    下载选中的照片，打包成 ZIP。
    按白图/场景图分类，文件命名：子分类名称 + 编号
    """
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    # 解析照片ID列表
    try:
        ids = [int(x.strip()) for x in photo_ids.split(',') if x.strip()]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的照片ID格式",
        )

    if not ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请至少选择一张照片",
        )

    # 查询照片和目标信息
    stmt = (
        select(Photo)
        .where(Photo.id.in_(ids), Photo.status != PhotoStatus.deleted)
        .options(selectinload(Photo.target))
    )
    photos = (await db.execute(stmt)).scalars().all()

    if not photos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到有效照片",
        )

    # 按白图/场景图分类
    white_photos = []
    scene_photos = []

    for photo in photos:
        if photo.target:
            if photo.target.category_type == CategoryType.white:
                white_photos.append((photo.target.name, photo))
            elif photo.target.category_type == CategoryType.scene:
                scene_photos.append((photo.target.name, photo))

    # 创建 ZIP 文件（内存模式）
    zip_buffer = io.BytesIO()

    def create_zip():
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 处理白图
            if white_photos:
                white_grouped = {}
                for target_name, photo in white_photos:
                    if target_name not in white_grouped:
                        white_grouped[target_name] = []
                    white_grouped[target_name].append(photo)

                for target_name, photos_list in white_grouped.items():
                    for idx, photo in enumerate(photos_list, start=1):
                        try:
                            original_path = NAS_ROOT / photo.original_path
                            if not original_path.exists():
                                continue

                            # 安全检查：确保文件在NAS_ROOT内
                            if not original_path.resolve().is_relative_to(NAS_ROOT.resolve()):
                                continue

                            suffix = original_path.suffix or '.jpg'
                            # 清理target_name，防止路径穿越
                            safe_target_name = target_name.replace('/', '_').replace('\\', '_').replace('..', '_')
                            zip_path = f"白图/{safe_target_name}{idx:02d}{suffix}"
                            zf.write(original_path, zip_path)
                        except Exception as e:
                            # 单个文件失败不影响整体打包
                            continue

            # 处理场景图
            if scene_photos:
                scene_grouped = {}
                for target_name, photo in scene_photos:
                    if target_name not in scene_grouped:
                        scene_grouped[target_name] = []
                    scene_grouped[target_name].append(photo)

                for target_name, photos_list in scene_grouped.items():
                    for idx, photo in enumerate(photos_list, start=1):
                        try:
                            original_path = NAS_ROOT / photo.original_path
                            if not original_path.exists():
                                continue

                            # 安全检查：确保文件在NAS_ROOT内
                            if not original_path.resolve().is_relative_to(NAS_ROOT.resolve()):
                                continue

                            suffix = original_path.suffix or '.jpg'
                            # 清理target_name，防止路径穿越
                            safe_target_name = target_name.replace('/', '_').replace('\\', '_').replace('..', '_')
                            zip_path = f"场景图/{safe_target_name}{idx:02d}{suffix}"
                            zf.write(original_path, zip_path)
                        except Exception as e:
                            # 单个文件失败不影响整体打包
                            continue

    # 在线程池中执行 ZIP 创建
    await run_in_threadpool(create_zip)

    # 重置缓冲区指针
    zip_buffer.seek(0)

    # 返回流式响应
    filename = f"选中照片_{len(photos)}张.zip"
    encoded_filename = quote(filename)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )


# ── 下载最终交付图 ZIP ──────────────────────────────────

@router.get(
    "/{project_id}/download-final",
    summary="下载最终交付图 ZIP 压缩包",
)
async def download_final_photos(
    project_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    下载项目的最终交付图，按白图/场景图分类打包成 ZIP。
    文件命名规则：子分类名称 + 编号（如：正视图01.jpg）
    """
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    # 直接查询最终交付图，避免 N+1 问题
    white_stmt = (
        select(ProjectTarget.name, Photo)
        .join(Photo, Photo.target_id == ProjectTarget.id)
        .where(
            ProjectTarget.project_id == project_id,
            ProjectTarget.deleted_at.is_(None),
            ProjectTarget.target_status == TargetStatus.completed,
            ProjectTarget.category_type == CategoryType.white,
            Photo.process_state == ProcessState.final,
            Photo.status != PhotoStatus.deleted,
            Photo.deleted_at.is_(None)
        )
        .order_by(ProjectTarget.sort_order, Photo.display_id)
    )
    white_results = (await db.execute(white_stmt)).all()
    white_photos = [(name, photo) for name, photo in white_results]

    scene_stmt = (
        select(ProjectTarget.name, Photo)
        .join(Photo, Photo.target_id == ProjectTarget.id)
        .where(
            ProjectTarget.project_id == project_id,
            ProjectTarget.deleted_at.is_(None),
            ProjectTarget.target_status == TargetStatus.completed,
            ProjectTarget.category_type == CategoryType.scene,
            Photo.process_state == ProcessState.final,
            Photo.status != PhotoStatus.deleted,
            Photo.deleted_at.is_(None)
        )
        .order_by(ProjectTarget.sort_order, Photo.display_id)
    )
    scene_results = (await db.execute(scene_stmt)).all()
    scene_photos = [(name, photo) for name, photo in scene_results]

    if not white_photos and not scene_photos:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该项目暂无最终交付图",
        )

    # 创建 ZIP 文件（内存模式）
    zip_buffer = io.BytesIO()

    def create_zip():
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 处理白图
            if white_photos:
                # 按目标名称分组并编号
                white_grouped = {}
                for target_name, photo in white_photos:
                    if target_name not in white_grouped:
                        white_grouped[target_name] = []
                    white_grouped[target_name].append(photo)

                for target_name, photos in white_grouped.items():
                    for idx, photo in enumerate(photos, start=1):
                        try:
                            # 获取原始文件路径
                            original_path = NAS_ROOT / photo.original_path
                            if not original_path.exists():
                                continue

                            # 安全检查：确保文件在NAS_ROOT内
                            if not original_path.resolve().is_relative_to(NAS_ROOT.resolve()):
                                continue

                            # 文件扩展名
                            suffix = original_path.suffix or '.jpg'
                            # 清理target_name，防止路径穿越
                            safe_target_name = target_name.replace('/', '_').replace('\\', '_').replace('..', '_')
                            # ZIP 内路径：白图/正视图01.jpg
                            zip_path = f"白图/{safe_target_name}{idx:02d}{suffix}"

                            # 读取文件并写入 ZIP
                            zf.write(original_path, zip_path)
                        except Exception as e:
                            # 单个文件失败不影响整体打包
                            continue

            # 处理场景图
            if scene_photos:
                scene_grouped = {}
                for target_name, photo in scene_photos:
                    if target_name not in scene_grouped:
                        scene_grouped[target_name] = []
                    scene_grouped[target_name].append(photo)

                for target_name, photos in scene_grouped.items():
                    for idx, photo in enumerate(photos, start=1):
                        try:
                            original_path = NAS_ROOT / photo.original_path
                            if not original_path.exists():
                                continue

                            # 安全检查：确保文件在NAS_ROOT内
                            if not original_path.resolve().is_relative_to(NAS_ROOT.resolve()):
                                continue

                            suffix = original_path.suffix or '.jpg'
                            # 清理target_name，防止路径穿越
                            safe_target_name = target_name.replace('/', '_').replace('\\', '_').replace('..', '_')
                            zip_path = f"场景图/{safe_target_name}{idx:02d}{suffix}"

                            zf.write(original_path, zip_path)
                        except Exception as e:
                            # 单个文件失败不影响整体打包
                            continue

    # 在线程池中执行 ZIP 创建（避免阻塞）
    await run_in_threadpool(create_zip)

    # 重置缓冲区指针
    zip_buffer.seek(0)

    # 返回流式响应
    filename = f"{project.name}_最终交付图.zip"
    encoded_filename = quote(filename)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )
