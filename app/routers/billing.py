from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import CurrentUser, SuperAdminUser
from app.models import (
    BillingPriceRule,
    Client,
    Photo,
    PhotoStatus,
    ProcessState,
    Project,
    ProjectBillingItem,
    ProjectBillingSummary,
    ProjectTarget,
    UserRole,
    user_project_access,
)
from app.schemas.billing_schema import (
    BillingConfirmRequest,
    BillingPriceRuleCreate,
    BillingPriceRuleListResponse,
    BillingPriceRuleResponse,
    BillingPriceRuleUpdate,
    ProjectBillingItemCreate,
    ProjectBillingItemResponse,
    ProjectBillingItemUpdate,
    ProjectBillingResponse,
    ProjectBillingSummaryResponse,
)

router = APIRouter(prefix="/api/v1", tags=["billing"])

DEFAULT_RULES = (
    ("white", "normal", "默认制作"),
    ("scene", "normal", "默认制作"),
)
READABLE_BILLING_STATUS = {"confirmed", "paid"}


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _item_amount(quantity, unit_price) -> Decimal:
    return (_money(quantity) * _money(unit_price)).quantize(Decimal("0.01"))


def _is_super_admin(current_user: CurrentUser) -> bool:
    return current_user.role == UserRole.super_admin


async def _get_project_for_user(
    db: AsyncSession,
    project_id: int,
    current_user: CurrentUser,
) -> Project:
    project = await db.get(Project, project_id)
    if project is None or project.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")

    if current_user.role in (UserRole.super_admin, UserRole.admin):
        return project

    allowed = await db.scalar(
        select(user_project_access.c.project_id).where(
            user_project_access.c.user_id == current_user.id,
            user_project_access.c.project_id == project_id,
        )
    )
    if allowed is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此项目")
    return project


async def _ensure_summary(db: AsyncSession, project_id: int) -> ProjectBillingSummary:
    summary = await db.get(ProjectBillingSummary, project_id)
    if summary is None:
        summary = ProjectBillingSummary(project_id=project_id)
        db.add(summary)
        await db.flush()
    return summary


async def _recalculate_summary(db: AsyncSession, summary: ProjectBillingSummary) -> None:
    items = (await db.execute(
        select(ProjectBillingItem).where(ProjectBillingItem.project_id == summary.project_id)
    )).scalars().all()

    subtotal = sum(
        (_money(item.amount) for item in items if not item.is_excluded and item.source == "auto"),
        Decimal("0.00"),
    )
    adjustment = sum(
        (_money(item.amount) for item in items if not item.is_excluded and item.source == "manual"),
        Decimal("0.00"),
    )
    summary.subtotal_amount = subtotal
    summary.adjustment_amount = adjustment
    summary.total_amount = subtotal + adjustment


async def _price_rules_for_client(db: AsyncSession, client_id: int) -> list[BillingPriceRule]:
    rules = (await db.execute(
        select(BillingPriceRule)
        .where(BillingPriceRule.client_id == client_id)
        .order_by(BillingPriceRule.base_category_type, BillingPriceRule.is_default.desc(), BillingPriceRule.id)
    )).scalars().all()

    existing_keys = {(rule.base_category_type, rule.production_type) for rule in rules}
    defaults: list[BillingPriceRule] = []
    for base_category_type, production_type, production_name in DEFAULT_RULES:
        if (base_category_type, production_type) not in existing_keys:
            defaults.append(BillingPriceRule(
                client_id=client_id,
                base_category_type=base_category_type,
                production_type=production_type,
                production_name=production_name,
                unit_price=0,
                is_default=True,
                is_active=True,
            ))

    if defaults:
        db.add_all(defaults)
        await db.flush()
        rules = (await db.execute(
            select(BillingPriceRule)
            .where(BillingPriceRule.client_id == client_id)
            .order_by(BillingPriceRule.base_category_type, BillingPriceRule.is_default.desc(), BillingPriceRule.id)
        )).scalars().all()

    return rules


async def _default_rule_for_category(
    db: AsyncSession,
    client_id: int,
    base_category_type: str,
) -> BillingPriceRule:
    rules = await _price_rules_for_client(db, client_id)
    for rule in rules:
        if rule.base_category_type == base_category_type and rule.is_default and rule.is_active:
            return rule
    for rule in rules:
        if rule.base_category_type == base_category_type and rule.is_active:
            return rule

    rule = BillingPriceRule(
        client_id=client_id,
        base_category_type=base_category_type,
        production_type="normal",
        production_name="默认制作",
        unit_price=0,
        is_default=True,
        is_active=True,
    )
    db.add(rule)
    await db.flush()
    return rule


async def _find_active_rule(
    db: AsyncSession,
    client_id: int,
    base_category_type: str,
    production_type: str,
) -> BillingPriceRule | None:
    return await db.scalar(
        select(BillingPriceRule).where(
            BillingPriceRule.client_id == client_id,
            BillingPriceRule.base_category_type == base_category_type,
            BillingPriceRule.production_type == production_type,
            BillingPriceRule.is_active.is_(True),
        )
    )


async def _sync_final_photo_items(
    db: AsyncSession,
    project: Project,
    summary: ProjectBillingSummary,
) -> int:
    if summary.billing_status == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="账目已收款，不能重新同步")

    rows = (await db.execute(
        select(Photo, ProjectTarget)
        .join(ProjectTarget, Photo.target_id == ProjectTarget.id)
        .where(
            Photo.project_id == project.id,
            Photo.deleted_at.is_(None),
            Photo.status != PhotoStatus.deleted,
            Photo.process_state == ProcessState.final,
            ProjectTarget.deleted_at.is_(None),
        )
        .order_by(ProjectTarget.sort_order, Photo.display_id)
    )).all()

    current_photo_ids = {photo.id for photo, _target in rows}
    existing_items = (await db.execute(
        select(ProjectBillingItem).where(ProjectBillingItem.project_id == project.id)
    )).scalars().all()
    by_photo = {item.photo_id: item for item in existing_items if item.photo_id is not None}

    default_rules: dict[str, BillingPriceRule] = {}
    for photo, target in rows:
        base_category_type = target.category_type.value if target.category_type else "other"
        if base_category_type not in default_rules:
            default_rules[base_category_type] = await _default_rule_for_category(db, project.client_id, base_category_type)

        rule = default_rules[base_category_type]
        unit_price = _money(rule.unit_price)
        amount = _item_amount(1, unit_price)
        item = by_photo.get(photo.id)
        if item is None:
            db.add(ProjectBillingItem(
                project_id=project.id,
                photo_id=photo.id,
                target_id=target.id,
                base_category_type=base_category_type,
                production_type=rule.production_type,
                production_name=rule.production_name,
                quantity=Decimal("1.00"),
                unit_price=unit_price,
                amount=amount,
                source="auto",
            ))
            continue

        if item.source == "auto":
            item.target_id = target.id
            item.base_category_type = base_category_type
            if not item.production_type:
                item.production_type = rule.production_type
                item.production_name = rule.production_name
                item.unit_price = unit_price
            item.amount = _item_amount(item.quantity, item.unit_price)
            item.is_excluded = False

    stale_auto_ids = [
        item.id
        for item in existing_items
        if item.source == "auto" and item.photo_id is not None and item.photo_id not in current_photo_ids
    ]
    if stale_auto_ids:
        await db.execute(delete(ProjectBillingItem).where(ProjectBillingItem.id.in_(stale_auto_ids)))

    await db.flush()
    await _recalculate_summary(db, summary)
    return len(current_photo_ids)


def _rule_response(rule: BillingPriceRule) -> BillingPriceRuleResponse:
    return BillingPriceRuleResponse(
        id=rule.id,
        client_id=rule.client_id,
        base_category_type=rule.base_category_type,
        production_type=rule.production_type,
        production_name=rule.production_name,
        unit_price=float(rule.unit_price or 0),
        is_default=rule.is_default,
        is_active=rule.is_active,
        created_at=rule.created_at.isoformat(),
        updated_at=rule.updated_at.isoformat(),
    )


async def _billing_response(
    db: AsyncSession,
    project: Project,
    summary: ProjectBillingSummary,
) -> ProjectBillingResponse:
    rows = (await db.execute(
        select(ProjectBillingItem, Photo, ProjectTarget)
        .outerjoin(Photo, ProjectBillingItem.photo_id == Photo.id)
        .outerjoin(ProjectTarget, ProjectBillingItem.target_id == ProjectTarget.id)
        .where(ProjectBillingItem.project_id == project.id)
        .order_by(ProjectBillingItem.source, ProjectBillingItem.id)
    )).all()

    items = [
        ProjectBillingItemResponse(
            id=item.id,
            project_id=item.project_id,
            photo_id=item.photo_id,
            target_id=item.target_id,
            target_name=target.name if target else None,
            display_id=photo.display_id if photo else None,
            thumbnail_path=photo.thumbnail_path if photo else None,
            original_path=photo.original_path if photo else None,
            base_category_type=item.base_category_type,
            production_type=item.production_type,
            production_name=item.production_name,
            quantity=float(item.quantity or 0),
            unit_price=float(item.unit_price or 0),
            amount=float(item.amount or 0),
            source=item.source,
            notes=item.notes,
            is_excluded=item.is_excluded,
            created_at=item.created_at.isoformat(),
            updated_at=item.updated_at.isoformat(),
        )
        for item, photo, target in rows
    ]

    final_photo_count = len([item for item in items if item.source == "auto" and not item.is_excluded])
    rules = await _price_rules_for_client(db, project.client_id)
    work_completed = project.project_status.value == "completed"
    payment_completed = summary.billing_status == "paid"
    return ProjectBillingResponse(
        summary=ProjectBillingSummaryResponse(
            project_id=project.id,
            subtotal_amount=float(summary.subtotal_amount or 0),
            adjustment_amount=float(summary.adjustment_amount or 0),
            total_amount=float(summary.total_amount or 0),
            billing_status=summary.billing_status,
            confirmed_at=summary.confirmed_at.isoformat() if summary.confirmed_at else None,
            paid_at=summary.paid_at.isoformat() if summary.paid_at else None,
            paid_by=summary.paid_by,
            notes=summary.notes,
            work_status=project.project_status.value,
            work_completed=work_completed,
            payment_completed=payment_completed,
        ),
        items=items,
        price_rules=[_rule_response(rule) for rule in rules],
        final_photo_count=final_photo_count,
    )


async def _ensure_editable_summary(db: AsyncSession, project_id: int) -> ProjectBillingSummary:
    summary = await _ensure_summary(db, project_id)
    if summary.billing_status == "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="账目已收款，不能修改")
    return summary


@router.get("/clients/{client_id}/billing-rules", response_model=BillingPriceRuleListResponse)
async def list_billing_price_rules(
    client_id: int,
    current_user: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> BillingPriceRuleListResponse:
    client = await db.get(Client, client_id)
    if client is None or client.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户不存在")
    rules = await _price_rules_for_client(db, client_id)
    await db.commit()
    return BillingPriceRuleListResponse(items=[_rule_response(rule) for rule in rules], total=len(rules))


@router.post("/clients/{client_id}/billing-rules", response_model=BillingPriceRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_billing_price_rule(
    client_id: int,
    body: BillingPriceRuleCreate,
    current_user: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> BillingPriceRuleResponse:
    client = await db.get(Client, client_id)
    if client is None or client.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="客户不存在")
    existing = await db.scalar(select(BillingPriceRule).where(
        BillingPriceRule.client_id == client_id,
        BillingPriceRule.base_category_type == body.base_category_type,
        BillingPriceRule.production_type == body.production_type,
    ))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="该制作类型已存在")

    if body.is_default:
        current_default = await db.execute(select(BillingPriceRule).where(
            BillingPriceRule.client_id == client_id,
            BillingPriceRule.base_category_type == body.base_category_type,
            BillingPriceRule.is_default.is_(True),
        ))
        for rule in current_default.scalars().all():
            rule.is_default = False

    rule = BillingPriceRule(client_id=client_id, **body.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return _rule_response(rule)


@router.patch("/clients/{client_id}/billing-rules/{rule_id}", response_model=BillingPriceRuleResponse)
async def update_billing_price_rule(
    client_id: int,
    rule_id: int,
    body: BillingPriceRuleUpdate,
    current_user: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> BillingPriceRuleResponse:
    rule = await db.get(BillingPriceRule, rule_id)
    if rule is None or rule.client_id != client_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="计费规则不存在")

    update_data = body.model_dump(exclude_unset=True)
    if update_data.get("is_default") is True:
        current_default = await db.execute(select(BillingPriceRule).where(
            BillingPriceRule.client_id == client_id,
            BillingPriceRule.base_category_type == rule.base_category_type,
            BillingPriceRule.id != rule.id,
            BillingPriceRule.is_default.is_(True),
        ))
        for other in current_default.scalars().all():
            other.is_default = False

    for field, value in update_data.items():
        setattr(rule, field, value)
    await db.commit()
    await db.refresh(rule)
    return _rule_response(rule)


@router.delete("/clients/{client_id}/billing-rules/{rule_id}")
async def delete_billing_price_rule(
    client_id: int,
    rule_id: int,
    current_user: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
):
    rule = await db.get(BillingPriceRule, rule_id)
    if rule is None or rule.client_id != client_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="计费规则不存在")

    used = await db.scalar(
        select(ProjectBillingItem.id)
        .join(Project, ProjectBillingItem.project_id == Project.id)
        .where(
            Project.client_id == client_id,
            ProjectBillingItem.base_category_type == rule.base_category_type,
            ProjectBillingItem.production_type == rule.production_type,
        )
        .limit(1)
    )
    if used is not None:
        rule.is_active = False
        await db.commit()
        return {"code": 200, "msg": "计费规则已有历史账目使用，已停用", "data": _rule_response(rule).model_dump()}

    await db.delete(rule)
    await db.commit()
    return {"code": 200, "msg": "计费规则已删除"}


@router.get("/projects/{project_id}/billing", response_model=ProjectBillingResponse)
async def get_project_billing(
    project_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectBillingResponse:
    project = await _get_project_for_user(db, project_id, current_user)
    summary = await db.get(ProjectBillingSummary, project_id)

    if not _is_super_admin(current_user):
        if summary is None or summary.billing_status not in READABLE_BILLING_STATUS:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账目未锁定，暂无查看权限")
        return await _billing_response(db, project, summary)

    summary = await _ensure_summary(db, project_id)
    if summary.billing_status == "draft":
        await _sync_final_photo_items(db, project, summary)
        await db.commit()
        await db.refresh(summary)
    return await _billing_response(db, project, summary)


@router.post("/projects/{project_id}/billing/sync", response_model=ProjectBillingResponse)
async def sync_project_billing(
    project_id: int,
    current_user: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectBillingResponse:
    project = await _get_project_for_user(db, project_id, current_user)
    summary = await _ensure_editable_summary(db, project_id)
    await _sync_final_photo_items(db, project, summary)
    await db.commit()
    await db.refresh(summary)
    return await _billing_response(db, project, summary)


@router.post("/projects/{project_id}/billing/items", response_model=ProjectBillingResponse, status_code=status.HTTP_201_CREATED)
async def create_project_billing_item(
    project_id: int,
    body: ProjectBillingItemCreate,
    current_user: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectBillingResponse:
    project = await _get_project_for_user(db, project_id, current_user)
    summary = await _ensure_editable_summary(db, project_id)
    amount = _item_amount(body.quantity, body.unit_price)
    db.add(ProjectBillingItem(
        project_id=project_id,
        base_category_type=body.base_category_type,
        production_type=body.production_type,
        production_name=body.production_name,
        quantity=_money(body.quantity),
        unit_price=_money(body.unit_price),
        amount=amount,
        source="manual",
        notes=body.notes,
    ))
    if summary.billing_status == "confirmed":
        summary.billing_status = "draft"
        summary.confirmed_at = None
    await db.flush()
    await _recalculate_summary(db, summary)
    await db.commit()
    await db.refresh(summary)
    return await _billing_response(db, project, summary)


@router.patch("/projects/{project_id}/billing/items/{item_id}", response_model=ProjectBillingResponse)
async def update_project_billing_item(
    project_id: int,
    item_id: int,
    body: ProjectBillingItemUpdate,
    current_user: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectBillingResponse:
    project = await _get_project_for_user(db, project_id, current_user)
    summary = await _ensure_editable_summary(db, project_id)
    item = await db.get(ProjectBillingItem, item_id)
    if item is None or item.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账目明细不存在")

    update_data = body.model_dump(exclude_unset=True)
    explicit_unit_price = "unit_price" in update_data
    explicit_production_name = "production_name" in update_data
    for field, value in update_data.items():
        setattr(item, field, value)

    if "base_category_type" in update_data or "production_type" in update_data:
        rule = await _find_active_rule(db, project.client_id, item.base_category_type, item.production_type)
        if rule is not None:
            if not explicit_production_name:
                item.production_name = rule.production_name
            if not explicit_unit_price:
                item.unit_price = _money(rule.unit_price)

    item.amount = _item_amount(item.quantity, item.unit_price)
    if summary.billing_status == "confirmed":
        summary.billing_status = "draft"
        summary.confirmed_at = None
    await _recalculate_summary(db, summary)
    await db.commit()
    await db.refresh(summary)
    return await _billing_response(db, project, summary)


@router.delete("/projects/{project_id}/billing/items/{item_id}", response_model=ProjectBillingResponse)
async def delete_project_billing_item(
    project_id: int,
    item_id: int,
    current_user: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectBillingResponse:
    project = await _get_project_for_user(db, project_id, current_user)
    summary = await _ensure_editable_summary(db, project_id)
    item = await db.get(ProjectBillingItem, item_id)
    if item is None or item.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账目明细不存在")
    await db.delete(item)
    if summary.billing_status == "confirmed":
        summary.billing_status = "draft"
        summary.confirmed_at = None
    await db.flush()
    await _recalculate_summary(db, summary)
    await db.commit()
    await db.refresh(summary)
    return await _billing_response(db, project, summary)


@router.post("/projects/{project_id}/billing/confirm", response_model=ProjectBillingResponse)
async def confirm_project_billing(
    project_id: int,
    body: BillingConfirmRequest,
    current_user: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectBillingResponse:
    project = await _get_project_for_user(db, project_id, current_user)
    summary = await _ensure_summary(db, project_id)
    await _recalculate_summary(db, summary)
    summary.billing_status = "confirmed"
    summary.confirmed_at = datetime.now(timezone.utc)
    summary.notes = body.notes
    await db.commit()
    await db.refresh(summary)
    return await _billing_response(db, project, summary)


@router.post("/projects/{project_id}/billing/mark-paid", response_model=ProjectBillingResponse)
async def mark_project_billing_paid(
    project_id: int,
    body: BillingConfirmRequest,
    current_user: SuperAdminUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectBillingResponse:
    project = await _get_project_for_user(db, project_id, current_user)
    summary = await _ensure_summary(db, project_id)
    await _recalculate_summary(db, summary)
    now = datetime.now(timezone.utc)
    if summary.billing_status == "draft":
        summary.confirmed_at = now
    summary.billing_status = "paid"
    summary.paid_at = now
    summary.paid_by = current_user.id
    summary.notes = body.notes if body.notes is not None else summary.notes
    await db.commit()
    await db.refresh(summary)
    return await _billing_response(db, project, summary)
