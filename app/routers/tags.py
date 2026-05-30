"""
routers/tags.py —— 项目标签 CRUD
  - GET    /api/v1/projects/{project_id}/tags       获取项目标签列表
  - POST   /api/v1/projects/{project_id}/tags       创建标签
  - PATCH  /api/v1/projects/{project_id}/tags/{id}  更新标签
  - DELETE /api/v1/projects/{project_id}/tags/{id}  删除标签
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import distinct, select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import AdminUser, CurrentUser
from app.models import Project, ProjectTag, SystemTag, photo_tags
from app.schemas.tag_schema import (
    TagCreate,
    TagListResponse,
    ProjectTagUsageResponse,
    ProjectTagUsageItem,
    PromoteProjectTagRequest,
    TagResponse,
    TagUpdate,
)

router = APIRouter(prefix="/api/v1/projects", tags=["tags"])


@router.get(
    "/{project_id}/tags",
    response_model=TagListResponse,
    summary="获取项目标签列表",
)
async def list_tags(
    project_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TagListResponse:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    stmt = (
        select(ProjectTag)
        .where(ProjectTag.project_id == project_id)
        .order_by(ProjectTag.sort_order, ProjectTag.id)
    )
    tags = (await db.execute(stmt)).scalars().all()

    items = [
        TagResponse(
            id=t.id,
            project_id=t.project_id,
            name=t.name,
            color=t.color,
            scope=getattr(t, "scope", "project"),
            sort_order=t.sort_order,
            created_at=t.created_at.isoformat(),
        )
        for t in tags
    ]
    return TagListResponse(items=items, total=len(items))


@router.post(
    "/{project_id}/tags",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建项目标签",
)
async def create_tag(
    project_id: int,
    body: TagCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TagResponse:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    tag = ProjectTag(
        project_id=project_id,
        name=body.name,
        color=body.color,
        scope=body.scope if body.scope in {"project", "system"} else "project",
        sort_order=body.sort_order,
    )
    db.add(tag)
    await db.flush()
    await db.refresh(tag)
    await db.commit()

    return TagResponse(
        id=tag.id,
        project_id=tag.project_id,
        name=tag.name,
        color=tag.color,
        scope=getattr(tag, "scope", "project"),
        sort_order=tag.sort_order,
        created_at=tag.created_at.isoformat(),
    )


@router.patch(
    "/{project_id}/tags/{tag_id}",
    response_model=TagResponse,
    summary="更新标签",
)
async def update_tag(
    project_id: int,
    tag_id: int,
    body: TagUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TagResponse:
    tag = await db.get(ProjectTag, tag_id)
    if tag is None or tag.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"标签 id={tag_id} 不存在或不属于该项目",
        )

    if body.name is not None:
        tag.name = body.name
    if body.color is not None:
        tag.color = body.color
    if body.sort_order is not None:
        tag.sort_order = body.sort_order

    await db.commit()
    await db.refresh(tag)

    return TagResponse(
        id=tag.id,
        project_id=tag.project_id,
        name=tag.name,
        color=tag.color,
        scope=getattr(tag, "scope", "project"),
        sort_order=tag.sort_order,
        created_at=tag.created_at.isoformat(),
    )


@router.delete(
    "/{project_id}/tags/{tag_id}",
    summary="删除标签",
)
async def delete_tag(
    project_id: int,
    tag_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    tag = await db.get(ProjectTag, tag_id)
    if tag is None or tag.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"标签 id={tag_id} 不存在或不属于该项目",
        )

    await db.delete(tag)
    await db.commit()

    return {"code": 200, "msg": "标签已删除", "data": None}


@router.get(
    "/tags/usage/project-local",
    response_model=ProjectTagUsageResponse,
    summary="项目临时标签同名使用排行",
)
async def project_tag_usage(
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectTagUsageResponse:
    rows = (await db.execute(
        select(
            ProjectTag.name,
            sa_func.min(ProjectTag.color).label("color"),
            sa_func.count(distinct(ProjectTag.project_id)).label("project_count"),
            sa_func.count(photo_tags.c.photo_id).label("photo_count"),
        )
        .outerjoin(photo_tags, photo_tags.c.tag_id == ProjectTag.id)
        .where(ProjectTag.scope == "project")
        .group_by(ProjectTag.name)
        .order_by(sa_func.count(distinct(ProjectTag.project_id)).desc(), ProjectTag.name.asc())
        .limit(100)
    )).all()

    items = [
        ProjectTagUsageItem(
            name=name,
            color=color or "#409eff",
            project_count=int(project_count or 0),
            photo_count=int(photo_count or 0),
        )
        for name, color, project_count, photo_count in rows
    ]
    return ProjectTagUsageResponse(items=items, total=len(items))


@router.post(
    "/tags/promote",
    summary="将项目临时标签转为通用标签",
)
async def promote_project_tag(
    body: PromoteProjectTagRequest,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="标签名称不能为空")

    existing = await db.scalar(select(SystemTag).where(SystemTag.name == name))
    if existing is None:
        system_tag = SystemTag(name=name, color=body.color, sort_order=0)
        db.add(system_tag)

    rows = (await db.execute(select(ProjectTag).where(ProjectTag.name == name))).scalars().all()
    for tag in rows:
        tag.scope = "system"
        tag.color = body.color or tag.color

    await db.commit()
    return {"code": 200, "msg": "已转为通用标签", "data": {"name": name, "affected": len(rows)}}
