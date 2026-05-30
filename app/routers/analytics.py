from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUser
from app.models import (
    CategoryType,
    Client,
    Photo,
    PhotoStatus,
    ProcessState,
    Project,
    ProjectBillingSummary,
    ProjectStatus,
    ProjectTarget,
    TargetStatus,
    UserRole,
    user_project_access,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


PROJECT_STATUS_LABELS = {
    ProjectStatus.not_started: "未开始",
    ProjectStatus.shooting: "拍摄中",
    ProjectStatus.retouching: "修图中",
    ProjectStatus.client_review: "客户审核",
    ProjectStatus.completed: "已完成",
}

TARGET_STATUS_LABELS = {
    TargetStatus.not_started: "未开始",
    TargetStatus.shooting: "拍摄中",
    TargetStatus.retouching: "修图中",
    TargetStatus.client_review: "客户审核",
    TargetStatus.completed: "已完成",
}


def _period_bounds(year: int, month: int | None) -> tuple[datetime, datetime]:
    if month:
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        return start, end
    return datetime(year, 1, 1, tzinfo=timezone.utc), datetime(year + 1, 1, 1, tzinfo=timezone.utc)


def _money(value) -> float:
    return float(Decimal(str(value or 0)).quantize(Decimal("0.01")))


def _rate(current: float, previous: float) -> float | None:
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def _month_index(value) -> int:
    return max(1, min(12, int(value or 1))) - 1


def _project_visibility_filter(current_user: CurrentUser):
    if current_user.role in (UserRole.super_admin, UserRole.admin):
        return None
    return or_(
        Project.customer_id == current_user.id,
        Project.id.in_(
            select(user_project_access.c.project_id).where(user_project_access.c.user_id == current_user.id)
        ),
    )


def _project_filters(
    current_user: CurrentUser,
    client_id: int | None = None,
    shooting_type: str | None = None,
):
    filters = [Project.deleted_at.is_(None)]
    visibility = _project_visibility_filter(current_user)
    if visibility is not None:
        filters.append(visibility)
    if client_id:
        filters.append(Project.client_id == client_id)
    if shooting_type:
        filters.append(Project.shooting_type == shooting_type)
    return filters


async def _scalar_int(db: AsyncSession, stmt) -> int:
    return int(await db.scalar(stmt) or 0)


async def _scalar_money(db: AsyncSession, stmt) -> float:
    return _money(await db.scalar(stmt) or 0)


async def _overview(
    db: AsyncSession,
    current_user: CurrentUser,
    year: int,
    month: int | None,
    client_id: int | None,
    shooting_type: str | None,
) -> dict:
    start, end = _period_bounds(year, month)
    prev_start, prev_end = _period_bounds(year - 1, month)
    filters = _project_filters(current_user, client_id, shooting_type)

    async def completed_count(period_start: datetime, period_end: datetime) -> int:
        return await _scalar_int(db, select(func.count(Project.id)).where(
            *filters,
            Project.project_status == ProjectStatus.completed,
            func.coalesce(Project.archived_at, Project.created_at) >= period_start,
            func.coalesce(Project.archived_at, Project.created_at) < period_end,
        ))

    async def active_count(period_start: datetime, period_end: datetime) -> int:
        return await _scalar_int(db, select(func.count(Project.id)).where(
            *filters,
            Project.project_status != ProjectStatus.completed,
            Project.created_at >= period_start,
            Project.created_at < period_end,
        ))

    async def final_count(period_start: datetime, period_end: datetime) -> int:
        return await _scalar_int(db, select(func.count(Photo.id)).join(Project, Photo.project_id == Project.id).where(
            *filters,
            Photo.deleted_at.is_(None),
            Photo.status != PhotoStatus.deleted,
            Photo.process_state == ProcessState.final,
            Photo.created_at >= period_start,
            Photo.created_at < period_end,
        ))

    async def receivable(period_start: datetime, period_end: datetime) -> float:
        return await _scalar_money(db, select(func.coalesce(func.sum(ProjectBillingSummary.total_amount), 0))
            .join(Project, ProjectBillingSummary.project_id == Project.id)
            .where(
                *filters,
                ProjectBillingSummary.billing_status.in_(("confirmed", "paid")),
                ProjectBillingSummary.confirmed_at.isnot(None),
                ProjectBillingSummary.confirmed_at >= period_start,
                ProjectBillingSummary.confirmed_at < period_end,
            ))

    async def received(period_start: datetime, period_end: datetime) -> float:
        return await _scalar_money(db, select(func.coalesce(func.sum(ProjectBillingSummary.total_amount), 0))
            .join(Project, ProjectBillingSummary.project_id == Project.id)
            .where(
                *filters,
                ProjectBillingSummary.billing_status == "paid",
                ProjectBillingSummary.paid_at.isnot(None),
                ProjectBillingSummary.paid_at >= period_start,
                ProjectBillingSummary.paid_at < period_end,
            ))

    completed_now = await completed_count(start, end)
    completed_prev = await completed_count(prev_start, prev_end)
    active_now = await active_count(start, end)
    active_prev = await active_count(prev_start, prev_end)
    final_now = await final_count(start, end)
    final_prev = await final_count(prev_start, prev_end)
    receivable_now = await receivable(start, end)
    receivable_prev = await receivable(prev_start, prev_end)
    received_now = await received(start, end)
    received_prev = await received(prev_start, prev_end)
    unreceived_now = max(receivable_now - received_now, 0)
    unreceived_prev = max(receivable_prev - received_prev, 0)

    return {
        "completed_projects": {"value": completed_now, "year_over_year_rate": _rate(completed_now, completed_prev)},
        "active_projects": {"value": active_now, "year_over_year_rate": _rate(active_now, active_prev)},
        "monthly_final_photos": {"value": final_now, "year_over_year_rate": _rate(final_now, final_prev)},
        "receivable_amount": {"value": receivable_now, "year_over_year_rate": _rate(receivable_now, receivable_prev)},
        "received_amount": {"value": received_now, "year_over_year_rate": _rate(received_now, received_prev)},
        "unreceived_amount": {"value": unreceived_now, "year_over_year_rate": _rate(unreceived_now, unreceived_prev)},
    }


async def _work_progress(
    db: AsyncSession,
    current_user: CurrentUser,
    client_id: int | None,
    shooting_type: str | None,
) -> dict:
    filters = _project_filters(current_user, client_id, shooting_type)

    project_rows = (await db.execute(
        select(Project.project_status, func.count(Project.id)).where(*filters).group_by(Project.project_status)
    )).all()
    status_map = {status: int(count or 0) for status, count in project_rows}
    distribution = [
        {
            "status": status.value,
            "label": PROJECT_STATUS_LABELS[status],
            "count": status_map.get(status, 0),
        }
        for status in ProjectStatus
    ]

    target_rows = (await db.execute(
        select(ProjectTarget.category_type, ProjectTarget.target_status, func.count(ProjectTarget.id))
        .join(Project, ProjectTarget.project_id == Project.id)
        .where(*filters, ProjectTarget.deleted_at.is_(None))
        .group_by(ProjectTarget.category_type, ProjectTarget.target_status)
    )).all()
    category_total = {"white": 0, "scene": 0}
    category_completed = {"white": 0, "scene": 0}
    for category, target_status, count in target_rows:
        key = category.value
        category_total[key] += int(count or 0)
        if target_status == TargetStatus.completed:
            category_completed[key] += int(count or 0)

    photo_rows = (await db.execute(
        select(Photo.process_state, func.count(Photo.id))
        .join(Project, Photo.project_id == Project.id)
        .where(*filters, Photo.deleted_at.is_(None), Photo.status != PhotoStatus.deleted)
        .group_by(Photo.process_state)
    )).all()
    photo_map = {state: int(count or 0) for state, count in photo_rows}

    return {
        "project_status_distribution": distribution,
        "white_total": category_total["white"],
        "white_completed": category_completed["white"],
        "scene_total": category_total["scene"],
        "scene_completed": category_completed["scene"],
        "raw_photo_count": photo_map.get(ProcessState.raw, 0),
        "retouched_photo_count": photo_map.get(ProcessState.retouched, 0),
        "final_photo_count": photo_map.get(ProcessState.final, 0),
    }


async def _annual_trends(
    db: AsyncSession,
    current_user: CurrentUser,
    year: int,
    client_id: int | None,
    shooting_type: str | None,
) -> dict:
    filters = _project_filters(current_user, client_id, shooting_type)
    start, end = _period_bounds(year, None)
    months = list(range(1, 13))
    output = {
        "months": months,
        "white_final": [0] * 12,
        "scene_final": [0] * 12,
        "final_total": [0] * 12,
        "completed_projects": [0] * 12,
    }
    income = {
        "months": months,
        "receivable": [0.0] * 12,
        "received": [0.0] * 12,
        "unreceived": [0.0] * 12,
    }

    final_rows = (await db.execute(
        select(
            func.extract("month", Photo.created_at),
            ProjectTarget.category_type,
            func.count(Photo.id),
        )
        .join(Project, Photo.project_id == Project.id)
        .outerjoin(ProjectTarget, Photo.target_id == ProjectTarget.id)
        .where(
            *filters,
            Photo.deleted_at.is_(None),
            Photo.status != PhotoStatus.deleted,
            Photo.process_state == ProcessState.final,
            Photo.created_at >= start,
            Photo.created_at < end,
        )
        .group_by(func.extract("month", Photo.created_at), ProjectTarget.category_type)
    )).all()
    for month_value, category, count in final_rows:
        idx = _month_index(month_value)
        key = "scene_final" if category == CategoryType.scene else "white_final"
        output[key][idx] += int(count or 0)
        output["final_total"][idx] += int(count or 0)

    completed_rows = (await db.execute(
        select(func.extract("month", func.coalesce(Project.archived_at, Project.created_at)), func.count(Project.id))
        .where(
            *filters,
            Project.project_status == ProjectStatus.completed,
            func.coalesce(Project.archived_at, Project.created_at) >= start,
            func.coalesce(Project.archived_at, Project.created_at) < end,
        )
        .group_by(func.extract("month", func.coalesce(Project.archived_at, Project.created_at)))
    )).all()
    for month_value, count in completed_rows:
        output["completed_projects"][_month_index(month_value)] = int(count or 0)

    receivable_rows = (await db.execute(
        select(func.extract("month", ProjectBillingSummary.confirmed_at), func.coalesce(func.sum(ProjectBillingSummary.total_amount), 0))
        .join(Project, ProjectBillingSummary.project_id == Project.id)
        .where(
            *filters,
            ProjectBillingSummary.billing_status.in_(("confirmed", "paid")),
            ProjectBillingSummary.confirmed_at.isnot(None),
            ProjectBillingSummary.confirmed_at >= start,
            ProjectBillingSummary.confirmed_at < end,
        )
        .group_by(func.extract("month", ProjectBillingSummary.confirmed_at))
    )).all()
    for month_value, amount in receivable_rows:
        income["receivable"][_month_index(month_value)] = _money(amount)

    received_rows = (await db.execute(
        select(func.extract("month", ProjectBillingSummary.paid_at), func.coalesce(func.sum(ProjectBillingSummary.total_amount), 0))
        .join(Project, ProjectBillingSummary.project_id == Project.id)
        .where(
            *filters,
            ProjectBillingSummary.billing_status == "paid",
            ProjectBillingSummary.paid_at.isnot(None),
            ProjectBillingSummary.paid_at >= start,
            ProjectBillingSummary.paid_at < end,
        )
        .group_by(func.extract("month", ProjectBillingSummary.paid_at))
    )).all()
    for month_value, amount in received_rows:
        income["received"][_month_index(month_value)] = _money(amount)

    income["unreceived"] = [
        max(round(receivable - received, 2), 0)
        for receivable, received in zip(income["receivable"], income["received"], strict=True)
    ]

    return {"monthly_output": output, "monthly_income": income}


async def _client_business(
    db: AsyncSession,
    current_user: CurrentUser,
    year: int,
    month: int | None,
    client_id: int | None,
    shooting_type: str | None,
) -> dict:
    start, end = _period_bounds(year, month)
    filters = _project_filters(current_user, client_id, shooting_type)

    consumption_rows = (await db.execute(
        select(
            Client.id,
            Client.name,
            func.count(func.distinct(Project.id)),
            func.coalesce(func.sum(case(
                (ProjectBillingSummary.billing_status.in_(("confirmed", "paid")), ProjectBillingSummary.total_amount),
                else_=0,
            )), 0),
            func.coalesce(func.sum(case(
                (ProjectBillingSummary.billing_status == "paid", ProjectBillingSummary.total_amount),
                else_=0,
            )), 0),
        )
        .join(Project, Project.client_id == Client.id)
        .outerjoin(ProjectBillingSummary, ProjectBillingSummary.project_id == Project.id)
        .where(
            *filters,
            Project.created_at < end,
            Project.created_at >= start,
        )
        .group_by(Client.id, Client.name)
        .order_by(func.coalesce(func.sum(ProjectBillingSummary.total_amount), 0).desc())
        .limit(5)
    )).all()
    consumption_ranking = [
        {
            "client_id": cid,
            "client_name": name,
            "project_count": int(project_count or 0),
            "receivable_amount": _money(receivable),
            "received_amount": _money(received),
            "unreceived_amount": max(round(_money(receivable) - _money(received), 2), 0),
        }
        for cid, name, project_count, receivable, received in consumption_rows
    ]

    output_rows = (await db.execute(
        select(
            Client.id,
            Client.name,
            func.count(Photo.id),
            func.coalesce(func.sum(case((ProjectTarget.category_type == CategoryType.white, 1), else_=0)), 0),
            func.coalesce(func.sum(case((ProjectTarget.category_type == CategoryType.scene, 1), else_=0)), 0),
        )
        .join(Project, Project.client_id == Client.id)
        .join(Photo, Photo.project_id == Project.id)
        .outerjoin(ProjectTarget, Photo.target_id == ProjectTarget.id)
        .where(
            *filters,
            Photo.deleted_at.is_(None),
            Photo.status != PhotoStatus.deleted,
            Photo.process_state == ProcessState.final,
            Photo.created_at >= start,
            Photo.created_at < end,
        )
        .group_by(Client.id, Client.name)
        .order_by(func.count(Photo.id).desc())
        .limit(5)
    )).all()
    output_ranking = [
        {
            "client_id": cid,
            "client_name": name,
            "final_photo_count": int(final_count or 0),
            "white_final_count": int(white_count or 0),
            "scene_final_count": int(scene_count or 0),
        }
        for cid, name, final_count, white_count, scene_count in output_rows
    ]

    payment_rows = (await db.execute(
        select(
            Project.id,
            Project.name,
            Client.name,
            ProjectBillingSummary.total_amount,
            ProjectBillingSummary.confirmed_at,
            Project.estimated_end_time,
        )
        .join(Client, Project.client_id == Client.id)
        .join(ProjectBillingSummary, ProjectBillingSummary.project_id == Project.id)
        .where(
            *filters,
            ProjectBillingSummary.billing_status == "confirmed",
            ProjectBillingSummary.confirmed_at.isnot(None),
        )
        .order_by(ProjectBillingSummary.confirmed_at.asc())
        .limit(8)
    )).all()
    payment_alerts = [
        {
            "project_id": pid,
            "project_name": project_name,
            "client_name": client_name,
            "amount": _money(amount),
            "confirmed_at": confirmed_at.isoformat() if confirmed_at else None,
            "estimated_end_time": estimated_end_time.isoformat() if estimated_end_time else None,
        }
        for pid, project_name, client_name, amount, confirmed_at, estimated_end_time in payment_rows
    ]

    return {
        "consumption_ranking": consumption_ranking,
        "output_ranking": output_ranking,
        "payment_alerts": payment_alerts,
    }


async def _filters(db: AsyncSession, current_user: CurrentUser, year: int) -> dict:
    filters = _project_filters(current_user)
    clients = (await db.execute(
        select(Client.id, Client.name)
        .join(Project, Project.client_id == Client.id)
        .where(*filters, Client.deleted_at.is_(None))
        .group_by(Client.id, Client.name)
        .order_by(Client.name)
    )).all()
    shooting_types = (await db.execute(
        select(Project.shooting_type)
        .where(*filters, Project.shooting_type.isnot(None), Project.shooting_type != "")
        .group_by(Project.shooting_type)
        .order_by(Project.shooting_type)
    )).scalars().all()
    return {
        "year": year,
        "clients": [{"id": cid, "name": name} for cid, name in clients],
        "shooting_types": list(shooting_types),
    }


@router.get("/compass", summary="数据罗盘")
async def analytics_compass(
    current_user: CurrentUser,
    year: int = Query(default_factory=lambda: datetime.now().year, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    client_id: int | None = Query(None),
    shooting_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    return {
        "filters": await _filters(db, current_user, year),
        "overview": await _overview(db, current_user, year, month, client_id, shooting_type),
        "work_progress": await _work_progress(db, current_user, client_id, shooting_type),
        "annual_trends": await _annual_trends(db, current_user, year, client_id, shooting_type),
        "client_business": await _client_business(db, current_user, year, month, client_id, shooting_type),
    }
