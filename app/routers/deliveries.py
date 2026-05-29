import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.deps import CurrentUser
from app.models import DeliverySession, Photo, PhotoStatus, ProcessState, Project, ProjectStatus, ProjectTarget, SystemConfig, TargetStatus, User
from app.schemas.delivery_schema import DeliverySessionCreate
from app.services.delivery_zip_service import generate_delivery_zip


router = APIRouter(prefix="/api/v1/deliveries", tags=["deliveries"])

STORAGE_ROOT = Path("storage")


@router.post("/create", summary="Create delivery share session")
async def create_delivery_session(
    body: DeliverySessionCreate,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, body.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project id={body.project_id} not found",
        )

    if project.project_status != ProjectStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only completed projects can create delivery links",
        )

    final_count = await db.scalar(
        select(Photo.id)
        .join(ProjectTarget, Photo.target_id == ProjectTarget.id)
        .where(
            Photo.project_id == body.project_id,
            Photo.process_state == ProcessState.final,
            Photo.status != PhotoStatus.deleted,
            Photo.deleted_at.is_(None),
            ProjectTarget.deleted_at.is_(None),
            ProjectTarget.target_status == TargetStatus.completed,
        )
        .limit(1)
    )
    if final_count is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project has no final delivery photos",
        )

    token = str(uuid.uuid4())
    expired_at = datetime.now(timezone.utc) + timedelta(days=body.expired_days)

    session = DeliverySession(
        token=token,
        project_id=body.project_id,
        created_by=current_user.id,
        expired_at=expired_at,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    if project.zip_status != "completed":
        project.zip_status = "pending"
        await db.commit()
        background_tasks.add_task(_generate_delivery_zip_background, body.project_id)

    config_stmt = select(SystemConfig).where(SystemConfig.config_key == "external_share_url")
    config = (await db.execute(config_stmt)).scalar_one_or_none()
    base_url = config.config_value.rstrip("/") if config and config.config_value else ""
    share_url = f"{base_url}/delivery/{token}" if base_url else f"/delivery/{token}"

    return {
        "code": 200,
        "msg": "delivery link created",
        "data": {
            "token": token,
            "share_url": share_url,
            "expired_at": expired_at.isoformat(),
            "zip_status": project.zip_status,
            "zip_path": project.zip_path,
        },
    }


async def _generate_delivery_zip_background(project_id: int) -> None:
    async with AsyncSessionLocal() as db:
        project = await db.get(Project, project_id)
        if project is None:
            return
        project.zip_status = "processing"
        await db.commit()
        await generate_delivery_zip(project_id, db)


@router.get("/project/{project_id}/sessions", summary="List project delivery sessions")
async def get_project_delivery_sessions(
    project_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project id={project_id} not found",
        )

    stmt = (
        select(DeliverySession, User.display_name)
        .outerjoin(User, DeliverySession.created_by == User.id)
        .where(DeliverySession.project_id == project_id)
        .order_by(DeliverySession.created_at.desc())
    )
    sessions_with_users = (await db.execute(stmt)).all()

    items = [
        {
            "id": session.id,
            "token": session.token,
            "created_by_name": creator_name or "Unknown",
            "created_at": session.created_at.isoformat(),
            "expired_at": session.expired_at.isoformat(),
            "is_disabled": session.is_disabled,
            "zip_status": project.zip_status,
        }
        for session, creator_name in sessions_with_users
    ]

    return {
        "code": 200,
        "msg": "success",
        "data": {"total": len(items), "items": items},
    }


@router.patch("/session/{session_id}/disable", summary="Toggle delivery session")
async def toggle_delivery_session(
    session_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(DeliverySession, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session id={session_id} not found",
        )

    session.is_disabled = not session.is_disabled
    await db.commit()

    return {
        "code": 200,
        "msg": "success",
        "data": {"is_disabled": session.is_disabled},
    }


# Token routes must stay below concrete admin routes to avoid route shadowing.
@router.get("/{token}", summary="Get delivery page data")
async def get_delivery_page(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    session = await _get_valid_session(token, db)
    project = await db.get(Project, session.project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    from app.models import Client

    client = await db.scalar(select(Client).where(Client.id == project.client_id))
    client_name = client.name if client else "Unknown"

    photo_count_stmt = select(Photo).where(
        Photo.project_id == project.id,
        Photo.process_state == ProcessState.final,
        Photo.target_id.isnot(None),
        Photo.status != PhotoStatus.deleted,
        Photo.deleted_at.is_(None),
        Photo.target.has(ProjectTarget.target_status == TargetStatus.completed),
    )
    photo_count = len((await db.execute(photo_count_stmt)).scalars().all())

    zip_size = None
    if project.zip_path and project.zip_status == "completed":
        zip_file_path = STORAGE_ROOT / project.zip_path
        if zip_file_path.exists():
            zip_size = zip_file_path.stat().st_size

    return {
        "code": 200,
        "msg": "success",
        "data": {
            "project_id": project.id,
            "project_name": project.name,
            "project_display_id": project.display_id,
            "client_name": client_name,
            "expired_at": session.expired_at.isoformat(),
            "is_expired": False,
            "zip_status": project.zip_status,
            "zip_path": project.zip_path,
            "zip_size": zip_size,
            "photo_count": photo_count,
        },
    }


@router.get("/{token}/download", summary="Download delivery ZIP")
async def download_delivery_zip(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    session = await _get_valid_session(token, db)
    project = await db.get(Project, session.project_id)
    if project is None or not project.zip_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery file not found")

    if project.zip_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Delivery file is not ready: {project.zip_status}",
        )

    zip_file_path = STORAGE_ROOT / project.zip_path
    if not zip_file_path.resolve().is_relative_to(STORAGE_ROOT.resolve()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden path")

    if not zip_file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Delivery file not found")

    return FileResponse(path=zip_file_path, media_type="application/zip", filename=zip_file_path.name)


@router.delete("/{session_id}", summary="Delete delivery session")
async def delete_delivery_session(
    session_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(DeliverySession, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session id={session_id} not found",
        )

    await db.delete(session)
    await db.commit()

    return {"code": 200, "msg": "deleted", "data": None}


async def _get_valid_session(token: str, db: AsyncSession) -> DeliverySession:
    session = await db.scalar(select(DeliverySession).where(DeliverySession.token == token))
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Share link not found")

    if session.is_disabled:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Share link disabled")

    if datetime.now(timezone.utc) > session.expired_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Share link expired")

    return session
