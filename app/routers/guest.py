"""
routers/guest.py —— 客户端（免认证）接口
  - GET /api/v1/guest/photos  获取项目照片列表（含 display_id）
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Photo, PhotoStatus, Project
from app.schemas.photo_schema import PhotoInList, PhotoListResponse

router = APIRouter(prefix="/api/v1/guest", tags=["guest"])


@router.get(
    "/photos",
    response_model=PhotoListResponse,
    summary="客户端获取项目照片列表",
)
async def guest_list_photos(
    project_id: int = Query(..., description="项目 ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    display_id: int | None = Query(None, description="按项目内编号过滤"),
    db: AsyncSession = Depends(get_db),
) -> PhotoListResponse:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={project_id} 不存在",
        )

    base_where = (Photo.project_id == project_id) & (Photo.status != PhotoStatus.deleted)

    if display_id is not None:
        base_where = base_where & (Photo.display_id == display_id)

    count_stmt = select(sa_func.count(Photo.id)).where(base_where)
    total = (await db.execute(count_stmt)).scalar() or 0

    photos_stmt = (
        select(Photo)
        .where(base_where)
        .order_by(Photo.display_id)
        .offset(skip)
        .limit(limit)
    )
    photos = (await db.execute(photos_stmt)).scalars().all()

    items = [
        PhotoInList(
            id=photo.id,
            project_id=photo.project_id,
            target_id=photo.target_id,
            display_id=photo.display_id,
            original_path=photo.original_path,
            thumbnail_path=photo.thumbnail_path,
            status=photo.status.value,
            process_state=photo.process_state.value,
            client_notes=photo.client_notes,
            deleted_at=photo.deleted_at.isoformat() if photo.deleted_at else None,
            created_at=photo.created_at.isoformat(),
        )
        for photo in photos
    ]

    return PhotoListResponse(total=total, items=items, skip=skip, limit=limit)
