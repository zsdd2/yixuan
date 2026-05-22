"""
routers/reviews.py —— 客户审核系统接口
  - POST   /api/v1/reviews/create              创建审核会话（生成分享链接）
  - GET    /api/v1/reviews/project/{project_id}/sessions  获取项目所有审核会话列表
  - GET    /api/v1/reviews/project/{project_id}/feedbacks 获取项目所有反馈
  - GET    /api/v1/reviews/session/{session_id}/feedbacks 查询会话反馈
  - PATCH  /api/v1/reviews/session/{session_id}/disable   作废/恢复审核链接
  - GET    /api/v1/reviews/{token}             获取审核页面数据（无需认证）
  - POST   /api/v1/reviews/{token}/feedback    提交客户反馈（无需认证）
"""
import uuid
import base64
import os
import re
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import CurrentUser
from app.models import Client, Photo, ProcessState, Project, ProjectTarget, ReviewFeedback, ReviewSession, SystemConfig, User
from app.services.delivery_zip_service import mark_zip_dirty
from app.schemas.review_schema import (
    CreateReviewRequest,
    CreateReviewResponse,
    FeedbackItem,
    ReviewCategoryGroup,
    ReviewPhotoItem,
    ReviewSessionData,
    ReviewSessionItem,
    ReviewTargetGroup,
    SessionFeedbackResponse,
    SessionListResponse,
    SessionStatistics,
    SubmitFeedbackRequest,
)

router = APIRouter(prefix="/api/v1/reviews", tags=["reviews"])
NAS_ROOT = Path(os.environ.get("NAS_MOUNT_PATH", "/mnt/nas_data"))


def _save_annotation_image(data_url: str | None, session_id: int, photo_id: int) -> str | None:
    if not data_url:
        return None
    match = re.match(r"^data:image/(png|jpeg|jpg|webp);base64,(.+)$", data_url)
    if not match:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="annotation_image 必须是图片 base64 data URL",
        )

    ext = "jpg" if match.group(1) == "jpeg" else match.group(1)
    try:
        image_bytes = base64.b64decode(match.group(2), validate=True)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="annotation_image base64 无效",
        )
    if len(image_bytes) > 8 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="annotation_image 不能超过 8MB",
        )

    annotation_dir = NAS_ROOT / "review_annotations" / str(session_id)
    annotation_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{photo_id}_{uuid.uuid4().hex}.{ext}"
    path = annotation_dir / filename
    path.write_bytes(image_bytes)
    return str(path.relative_to(NAS_ROOT))


@router.post(
    "/create",
    summary="创建审核会话（生成分享链接）",
)
async def create_review_session(
    body: CreateReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, body.project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"项目 id={body.project_id} 不存在",
        )

    # 检查是否已存在活跃会话（未过期且未作废）
    now = datetime.now(timezone.utc)
    existing_stmt = (
        select(ReviewSession)
        .where(
            ReviewSession.project_id == body.project_id,
            ReviewSession.expired_at > now,
            ReviewSession.is_disabled == False,
        )
    )
    existing_session = (await db.execute(existing_stmt)).scalars().first()

    if existing_session:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"该项目已存在活跃审核会话（Token: {existing_session.token[:8]}...），请先关闭或等待过期后再创建新会话",
        )

    token = str(uuid.uuid4())
    expired_at = datetime.now(timezone.utc) + timedelta(days=body.expired_days)

    selected_photos = [
        {
            "photo_id": ps.photo_id,
            "version": ps.version,
            "category_type": ps.category_type,
            "target_name": ps.target_name,
        }
        for ps in body.photo_selections
    ]

    session = ReviewSession(
        token=token,
        project_id=body.project_id,
        created_by=None,  # 开发环境暂时不需要认证
        expired_at=expired_at,
        selected_photos={"photos": selected_photos},
    )
    db.add(session)

    # 标记项目已分享
    if not project.has_shared:
        project.has_shared = True

    await db.commit()
    await db.refresh(session)

    # 获取外网链接配置（优先使用外网链接）
    config_stmt = select(SystemConfig).where(SystemConfig.config_key == "external_share_url")
    config = (await db.execute(config_stmt)).scalar_one_or_none()

    if config and config.config_value:
        # 使用外网链接
        base_url = config.config_value.rstrip('/')
        share_url = f"{base_url}/share/{token}"
    else:
        # 使用相对路径（前端拼接）
        share_url = f"/share/{token}"

    return {
        "code": 200,
        "msg": "审核链接已生成",
        "data": CreateReviewResponse(
            token=token,
            share_url=share_url,
            expired_at=expired_at.isoformat(),
        ),
    }


@router.get(
    "/project/{project_id}/sessions",
    summary="获取项目所有审核会话列表（含统计）",
)
async def get_project_sessions(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    print(f"[get_project_sessions] 开始处理请求，project_id={project_id}")

    try:
        # 查询该项目的所有审核会话（按创建时间倒序）
        # 注意：creator 可能为 NULL，使用 selectinload 时需要处理
        stmt = (
            select(ReviewSession)
            .where(ReviewSession.project_id == project_id)
            .options(
                selectinload(ReviewSession.feedbacks),
            )
            .order_by(ReviewSession.created_at.desc())
        )
        print(f"[get_project_sessions] 执行数据库查询...")
        sessions = (await db.execute(stmt)).scalars().all()
        print(f"[get_project_sessions] 查询到 {len(sessions)} 个会话")

        sessions_data = []
        for session in sessions:
            print(f"[get_project_sessions] 处理会话 id={session.id}, token={session.token[:8]}..., created_by={session.created_by}")

            # 手动查询创建人（避免 selectinload 在 NULL 外键时的问题）
            creator_name = "未知"
            if session.created_by:
                creator = await db.get(User, session.created_by)
                if creator:
                    creator_name = creator.username

            # 统计反馈（按 process_state 分类）
            stats = SessionStatistics()
            for fb in session.feedbacks:
                if not fb.is_confirmed:
                    continue
                # 查询照片的 process_state
                photo = await db.get(Photo, fb.photo_id)
                if photo:
                    if photo.process_state == ProcessState.raw:
                        stats.raw_confirmed += 1
                    elif photo.process_state == ProcessState.retouched:
                        stats.retouched_confirmed += 1
                    elif photo.process_state == ProcessState.final:
                        stats.final_confirmed += 1

            sessions_data.append(
                ReviewSessionItem(
                    id=session.id,
                    token=session.token,
                    created_by_name=creator_name,
                    created_at=session.created_at.isoformat(),
                    expired_at=session.expired_at.isoformat(),
                    is_viewed=session.is_viewed,
                    viewed_at=session.viewed_at.isoformat() if session.viewed_at else None,
                    is_disabled=session.is_disabled,
                    statistics=stats,
                )
            )

        print(f"[get_project_sessions] 成功构建响应数据，共 {len(sessions_data)} 条")
        return {"code": 200, "msg": "获取成功", "data": SessionListResponse(sessions=sessions_data)}

    except Exception as e:
        print(f"[get_project_sessions] 发生异常: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"服务器内部错误: {str(e)}",
        )


@router.get(
    "/project/{project_id}/feedbacks",
    summary="获取项目所有反馈（按会话分组，供 Admin 端轮询）",
)
async def get_project_feedbacks(
    project_id: int,
    db: AsyncSession = Depends(get_db),
):
    # 查询该项目的所有审核会话（按创建时间倒序）
    stmt = (
        select(ReviewSession)
        .where(ReviewSession.project_id == project_id)
        .options(selectinload(ReviewSession.feedbacks))
        .order_by(ReviewSession.created_at.desc())
    )
    sessions = (await db.execute(stmt)).scalars().all()

    # 按会话分组反馈
    sessions_data = []
    for session in sessions:
        feedbacks = [
            FeedbackItem(
                id=fb.id,
                photo_id=fb.photo_id,
                is_confirmed=fb.is_confirmed,
                comment=fb.comment,
                annotation_path=fb.annotation_path,
                created_at=fb.created_at.isoformat(),
            )
            for fb in session.feedbacks
        ]

        sessions_data.append(
            SessionFeedbackResponse(
                session_id=session.id,
                token=session.token,
                is_viewed=session.is_viewed,
                viewed_at=session.viewed_at.isoformat() if session.viewed_at else None,
                feedbacks=feedbacks,
            )
        )

    return {"code": 200, "msg": "获取成功", "data": sessions_data}


@router.get(
    "/session/{session_id}/feedbacks",
    summary="查询会话反馈（Admin）",
)
async def get_session_feedbacks(
    session_id: int,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ReviewSession)
        .where(ReviewSession.id == session_id)
        .options(selectinload(ReviewSession.feedbacks))
    )
    session = (await db.execute(stmt)).scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"审核会话 id={session_id} 不存在",
        )

    feedbacks = [
        FeedbackItem(
            id=fb.id,
            photo_id=fb.photo_id,
            is_confirmed=fb.is_confirmed,
            comment=fb.comment,
            annotation_path=fb.annotation_path,
            created_at=fb.created_at.isoformat(),
        )
        for fb in session.feedbacks
    ]

    data = SessionFeedbackResponse(
        session_id=session.id,
        token=session.token,
        is_viewed=session.is_viewed,
        viewed_at=session.viewed_at.isoformat() if session.viewed_at else None,
        feedbacks=feedbacks,
    )

    return {"code": 200, "msg": "获取成功", "data": data}


@router.patch(
    "/session/{session_id}/disable",
    summary="作废/恢复审核链接",
)
async def toggle_session_disable(
    session_id: int,
    is_disabled: bool,
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(ReviewSession, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"审核会话 id={session_id} 不存在",
        )

    session.is_disabled = is_disabled
    await db.commit()

    action = "已作废" if is_disabled else "已恢复"
    return {"code": 200, "msg": f"审核链接{action}", "data": None}


# ============================================================
# 以下是通配路由 /{token}，必须放在最后，避免路由冲突
# ============================================================

@router.get(
    "/{token}",
    summary="获取审核页面数据（无需认证）",
)
async def get_review_session(
    token: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(ReviewSession)
        .where(ReviewSession.token == token)
        .options(
            selectinload(ReviewSession.project).selectinload(Project.client),
            selectinload(ReviewSession.feedbacks),
        )
    )
    session = (await db.execute(stmt)).scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="审核链接不存在或已失效",
        )

    # 检查是否已作废
    if session.is_disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="分享已失效，请联系管理员",
        )

    now = datetime.now(timezone.utc)
    is_expired = now > session.expired_at

    if not session.is_viewed:
        session.is_viewed = True
        session.viewed_at = now
        await db.commit()

    photo_ids = [p["photo_id"] for p in session.selected_photos.get("photos", [])]
    if not photo_ids:
        categories = []
    else:
        stmt_photos = select(Photo).where(Photo.id.in_(photo_ids))
        photos = (await db.execute(stmt_photos)).scalars().all()
        photo_map = {p.id: p for p in photos}

        feedback_map = {fb.photo_id: fb for fb in session.feedbacks}

        # 按 category_type + target_name 分组，同时统计原图确认数
        categories_dict = defaultdict(lambda: {"photos": [], "confirmed_count": 0, "total_count": 0})

        for ps in session.selected_photos.get("photos", []):
            photo = photo_map.get(ps["photo_id"])
            if photo is None:
                continue

            feedback = feedback_map.get(photo.id)
            feedback_data = None
            if feedback:
                feedback_data = {
                    "is_confirmed": feedback.is_confirmed,
                    "comment": feedback.comment,
                    "annotation_path": feedback.annotation_path,
                    "created_at": feedback.created_at.isoformat(),
                }

            photo_item = ReviewPhotoItem(
                id=photo.id,
                display_id=photo.display_id,
                original_filename=photo.original_filename,
                thumbnail_path=photo.thumbnail_path,
                version=photo.version,
                parent_id=photo.parent_id,
                process_state=photo.process_state.value,
                target_name=ps["target_name"],
                feedback=feedback_data,
            )

            key = (ps["category_type"], ps["target_name"])
            categories_dict[key]["photos"].append(photo_item)
            categories_dict[key]["total_count"] += 1

            # 统计当前分享中客户已确认的照片；原图兼容管理端本地确认状态。
            if (feedback and feedback.is_confirmed) or (photo.process_state == ProcessState.raw and photo.is_confirmed):
                categories_dict[key]["confirmed_count"] += 1

        # 重新组织为二级结构
        category_targets_map = defaultdict(list)
        for (cat_type, target_name), data in categories_dict.items():
            category_targets_map[cat_type].append(
                ReviewTargetGroup(
                    target_name=target_name,
                    photos=data["photos"],
                    confirmed_count=data["confirmed_count"],
                    total_count=data["total_count"],
                )
            )

        categories = []
        category_labels = {"white": "白图", "scene": "场景图"}
        for cat_type, targets in category_targets_map.items():
            categories.append(
                ReviewCategoryGroup(
                    category_type=cat_type,
                    category_label=category_labels.get(cat_type, cat_type),
                    targets=targets,
                )
            )

    data = ReviewSessionData(
        project_id=session.project.id,
        project_name=session.project.name,
        project_display_id=session.project.display_id,
        cover_image=session.project.cover_image,
        client_name=session.project.client.name if session.project.client else None,
        expired_at=session.expired_at.isoformat(),
        is_expired=is_expired,
        categories=categories,
    )

    return {"code": 200, "msg": "获取成功", "data": data}


@router.post(
    "/{token}/feedback",
    summary="提交客户反馈（无需认证）",
)
async def submit_feedback(
    token: str,
    body: SubmitFeedbackRequest,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(ReviewSession).where(ReviewSession.token == token)
    session = (await db.execute(stmt)).scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="审核链接不存在或已失效",
        )

    # 检查是否已作废
    if session.is_disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="分享已失效，请联系管理员",
        )

    now = datetime.now(timezone.utc)
    if now > session.expired_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="审核链接已过期",
        )

    # 查询照片信息，判断是否需要锁定
    photo = await db.get(Photo, body.photo_id)
    if photo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"照片 id={body.photo_id} 不存在",
        )

    # 如果客户确认了精修图（process_state=retouched 或 final），自动锁定
    if body.is_confirmed and photo.process_state in [ProcessState.retouched, ProcessState.final]:
        photo.is_locked = True

    annotation_path = _save_annotation_image(body.annotation_image, session.id, body.photo_id)

    # 最终图由管理端上传并显式关联单张精修图；客户审核只负责确认和备注。

    existing_stmt = select(ReviewFeedback).where(
        ReviewFeedback.session_id == session.id,
        ReviewFeedback.photo_id == body.photo_id,
    )
    existing = (await db.execute(existing_stmt)).scalar_one_or_none()

    if existing:
        existing.is_confirmed = body.is_confirmed
        existing.comment = body.comment
        if annotation_path is not None:
            existing.annotation_path = annotation_path
    else:
        feedback = ReviewFeedback(
            session_id=session.id,
            photo_id=body.photo_id,
            is_confirmed=body.is_confirmed,
            comment=body.comment,
            annotation_path=annotation_path,
        )
        db.add(feedback)

    await db.commit()

    reviewed_photo_ids = set()
    feedback_rows = (await db.execute(
        select(ReviewFeedback).where(ReviewFeedback.session_id == session.id)
    )).scalars().all()
    for fb in feedback_rows:
        if fb.is_confirmed or (fb.comment and fb.comment.strip()):
            reviewed_photo_ids.add(fb.photo_id)

    selected_photo_ids = {
        item.get("photo_id")
        for item in (session.selected_photos or {}).get("photos", [])
        if item.get("photo_id") is not None
    }
    if selected_photo_ids and selected_photo_ids.issubset(reviewed_photo_ids):
        session.is_disabled = True
        await db.commit()

    # 如果标记为 final，触发脏数据标记
    if body.mark_as_final and body.is_confirmed and photo.process_state == ProcessState.final:
        await mark_zip_dirty(photo.project_id, db)

    return {"code": 200, "msg": "反馈已提交", "data": None}
