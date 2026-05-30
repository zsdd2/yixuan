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

    all_project_rows = (await db.execute(
        select(Project.id, Project.project_status, Project.is_manual).where(*filters)
    )).all()

    final_target_ids = set((await db.execute(
        select(Photo.target_id)
        .join(Project, Photo.project_id == Project.id)
        .where(
            *filters,
            Photo.target_id.isnot(None),
            Photo.deleted_at.is_(None),
            Photo.status != PhotoStatus.deleted,
            Photo.process_state == ProcessState.final,
        )
        .group_by(Photo.target_id)
    )).scalars().all())

    target_rows = (await db.execute(
        select(ProjectTarget.project_id, ProjectTarget.id, ProjectTarget.category_type, ProjectTarget.target_status)
        .join(Project, ProjectTarget.project_id == Project.id)
        .where(*filters, ProjectTarget.deleted_at.is_(None))
    )).all()
    category_total = {"white": 0, "scene": 0}
    category_completed = {"white": 0, "scene": 0}
    project_target_totals: dict[int, int] = {}
    project_target_completed: dict[int, int] = {}
    white_totals: dict[int, int] = {}
    white_completed: dict[int, int] = {}
    scene_totals: dict[int, int] = {}
    scene_completed: dict[int, int] = {}

    for project_id, target_id, category, target_status in target_rows:
        key = category.value
        category_total[key] += 1
        project_target_totals[project_id] = project_target_totals.get(project_id, 0) + 1
        completed = target_status == TargetStatus.completed or target_id in final_target_ids
        if completed:
            category_completed[key] += 1
            project_target_completed[project_id] = project_target_completed.get(project_id, 0) + 1
        if category == CategoryType.scene:
            scene_totals[project_id] = scene_totals.get(project_id, 0) + 1
            if completed:
                scene_completed[project_id] = scene_completed.get(project_id, 0) + 1
        else:
            white_totals[project_id] = white_totals.get(project_id, 0) + 1
            if completed:
                white_completed[project_id] = white_completed.get(project_id, 0) + 1

    photo_state_rows = (await db.execute(
        select(Photo.project_id, Photo.process_state, func.count(Photo.id))
        .join(Project, Photo.project_id == Project.id)
        .where(*filters, Photo.deleted_at.is_(None), Photo.status != PhotoStatus.deleted)
        .group_by(Photo.project_id, Photo.process_state)
    )).all()
    photo_map: dict[ProcessState, int] = {}
    project_photo_states: dict[int, dict[ProcessState, int]] = {}
    for project_id, process_state, count in photo_state_rows:
        count_int = int(count or 0)
        photo_map[process_state] = photo_map.get(process_state, 0) + count_int
        project_photo_states.setdefault(project_id, {})[process_state] = count_int

    def computed_project_status(
        project_id: int,
        stored_status: ProjectStatus | None,
        is_manual: bool,
    ) -> ProjectStatus:
        if is_manual:
            return stored_status or ProjectStatus.not_started
        target_total = project_target_totals.get(project_id, 0)
        completed_total = project_target_completed.get(project_id, 0)
        if target_total > 0 and completed_total >= target_total:
            return ProjectStatus.completed
        states = project_photo_states.get(project_id, {})
        if states.get(ProcessState.retouched, 0) > 0 or states.get(ProcessState.final, 0) > 0:
            return ProjectStatus.retouching
        if sum(states.values()) > 0:
            return ProjectStatus.shooting
        return ProjectStatus.not_started

    computed_status_by_project = {
        project_id: computed_project_status(project_id, stored_status, is_manual)
        for project_id, stored_status, is_manual in all_project_rows
    }
    status_map: dict[ProjectStatus, int] = {}
    for computed_status in computed_status_by_project.values():
        status_map[computed_status] = status_map.get(computed_status, 0) + 1
    distribution = [
        {
            "status": status.value,
            "label": PROJECT_STATUS_LABELS[status],
            "count": status_map.get(status, 0),
        }
        for status in ProjectStatus
    ]

    project_rows = (await db.execute(
        select(Project)
        .where(*filters)
        .order_by(Project.estimated_end_time.asc().nulls_last(), Project.created_at.desc())
        .limit(120)
    )).scalars().all()
    project_ids = [project.id for project in project_rows]
    client_names: dict[int, str] = {}

    if project_ids:
        client_ids = list({project.client_id for project in project_rows})
        if client_ids:
            client_names = dict((await db.execute(
                select(Client.id, Client.name).where(Client.id.in_(client_ids))
            )).all())

    projects_by_status: dict[str, list[dict]] = {status.value: [] for status in ProjectStatus}
    for project in project_rows:
        computed_status = computed_status_by_project.get(project.id, project.project_status or ProjectStatus.not_started)
        status_value = computed_status.value
        projects_by_status.setdefault(status_value, []).append({
            "id": project.id,
            "name": project.name,
            "client_name": client_names.get(project.client_id, ""),
            "cover_image": project.cover_image,
            "project_status": status_value,
            "status_label": PROJECT_STATUS_LABELS.get(computed_status, ""),
            "white_total": white_totals.get(project.id, 0),
            "white_completed": white_completed.get(project.id, 0),
            "scene_total": scene_totals.get(project.id, 0),
            "scene_completed": scene_completed.get(project.id, 0),
        })

    return {
        "project_status_distribution": distribution,
        "projects_by_status": projects_by_status,
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


@router.get("/billing-projects", summary="数据罗盘账目项目明细")
async def analytics_billing_projects(
    current_user: CurrentUser,
    amount_type: str = Query("receivable", pattern="^(receivable|received|unreceived)$"),
    year: int = Query(default_factory=lambda: datetime.now().year, ge=2000, le=2100),
    month: int | None = Query(None, ge=1, le=12),
    client_id: int | None = Query(None),
    shooting_type: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if month is None:
        month = datetime.now().month
    start, end = _period_bounds(year, month)
    filters = _project_filters(current_user, client_id, shooting_type)

    stmt = (
        select(
            Project.id,
            Project.name,
            Project.client_prefix,
            Project.serial_number,
            Client.name.label("client_name"),
            ProjectBillingSummary.total_amount,
            ProjectBillingSummary.billing_status,
            ProjectBillingSummary.confirmed_at,
            ProjectBillingSummary.paid_at,
        )
        .join(Client, Project.client_id == Client.id)
        .join(ProjectBillingSummary, ProjectBillingSummary.project_id == Project.id)
        .where(*filters)
    )
    if amount_type == "receivable":
        stmt = stmt.where(
            ProjectBillingSummary.billing_status.in_(("confirmed", "paid")),
            ProjectBillingSummary.confirmed_at.isnot(None),
            ProjectBillingSummary.confirmed_at >= start,
            ProjectBillingSummary.confirmed_at < end,
        ).order_by(ProjectBillingSummary.confirmed_at.desc())
    elif amount_type == "received":
        stmt = stmt.where(
            ProjectBillingSummary.billing_status == "paid",
            ProjectBillingSummary.paid_at.isnot(None),
            ProjectBillingSummary.paid_at >= start,
            ProjectBillingSummary.paid_at < end,
        ).order_by(ProjectBillingSummary.paid_at.desc())
    else:
        stmt = stmt.where(
            ProjectBillingSummary.billing_status == "confirmed",
            ProjectBillingSummary.confirmed_at.isnot(None),
            ProjectBillingSummary.confirmed_at >= start,
            ProjectBillingSummary.confirmed_at < end,
        ).order_by(ProjectBillingSummary.confirmed_at.desc())

    rows = (await db.execute(stmt.limit(100))).all()
    items = [
        {
            "project_id": project_id,
            "project_name": project_name,
            "project_display_id": f"{client_prefix or ''}{int(serial_number or 0):06d}",
            "client_name": client_name,
            "amount": _money(amount),
            "billing_status": billing_status,
            "confirmed_at": confirmed_at.isoformat() if confirmed_at else None,
            "paid_at": paid_at.isoformat() if paid_at else None,
        }
        for project_id, project_name, client_prefix, serial_number, client_name, amount, billing_status, confirmed_at, paid_at in rows
    ]
    return {
        "year": year,
        "month": month,
        "amount_type": amount_type,
        "total_amount": _money(sum(item["amount"] for item in items)),
        "items": items,
    }
