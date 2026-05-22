"""
routers/tags.py —— 项目标签 CRUD
  - GET    /api/v1/projects/{project_id}/tags       获取项目标签列表
  - POST   /api/v1/projects/{project_id}/tags       创建标签
  - PATCH  /api/v1/projects/{project_id}/tags/{id}  更新标签
  - DELETE /api/v1/projects/{project_id}/tags/{id}  删除标签
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUser
from app.models import Project, ProjectTag
from app.schemas.tag_schema import (
    TagCreate,
    TagListResponse,
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
