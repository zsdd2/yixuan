from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import AdminUser, CurrentUser
from app.models import BillingPriceRule, Client, Project, ProjectBillingSummary
from app.schemas.client_schema import (
    ClientCreate,
    ClientInList,
    ClientListResponse,
    ClientResponse,
    ClientUpdate,
)

router = APIRouter(prefix="/api/v1/clients", tags=["clients"])


@router.get("", response_model=ClientListResponse, summary="客户列表")
async def list_clients(
    current_user: CurrentUser,
    search: str | None = Query(None, description="按名称/前缀搜索"),
    db: AsyncSession = Depends(get_db),
) -> ClientListResponse:
    base = select(Client).where(Client.deleted_at.is_(None))
    if search:
        pattern = f"%{search}%"
        base = base.where(Client.name.ilike(pattern) | Client.prefix.ilike(pattern))
    base = base.order_by(Client.created_at.desc())

    clients = (await db.execute(base)).scalars().all()

    client_ids = [c.id for c in clients]
    project_totals: dict[int, int] = {}
    active_counts: dict[int, int] = {}
    completed_counts: dict[int, int] = {}
    total_amounts: dict[int, float] = {}

    if client_ids:
        pt_stmt = (
            select(Project.client_id, sa_func.count(Project.id))
            .where(Project.client_id.in_(client_ids), Project.deleted_at.is_(None))
            .group_by(Project.client_id)
        )
        project_totals = dict((await db.execute(pt_stmt)).all())

        ac_stmt = (
            select(Project.client_id, sa_func.count(Project.id))
            .where(
                Project.client_id.in_(client_ids),
                Project.deleted_at.is_(None),
                Project.archived_at.is_(None),
            )
            .group_by(Project.client_id)
        )
        active_counts = dict((await db.execute(ac_stmt)).all())

        cc_stmt = (
            select(Project.client_id, sa_func.count(Project.id))
            .where(
                Project.client_id.in_(client_ids),
                Project.deleted_at.is_(None),
                Project.archived_at.isnot(None),
            )
            .group_by(Project.client_id)
        )
        completed_counts = dict((await db.execute(cc_stmt)).all())

        amount_stmt = (
            select(Project.client_id, sa_func.coalesce(sa_func.sum(ProjectBillingSummary.total_amount), 0))
            .join(ProjectBillingSummary, ProjectBillingSummary.project_id == Project.id)
            .where(Project.client_id.in_(client_ids), Project.deleted_at.is_(None))
            .group_by(Project.client_id)
        )
        total_amounts = dict((await db.execute(amount_stmt)).all())

    items = [
        ClientInList(
            id=c.id,
            name=c.name,
            prefix=c.prefix,
            phone=c.phone,
            company=c.company,
            avatar=c.avatar,
            project_total=project_totals.get(c.id, 0),
            active_projects=active_counts.get(c.id, 0),
            completed_projects=completed_counts.get(c.id, 0),
            total_amount=float(total_amounts.get(c.id, 0) or 0),
            created_at=c.created_at.isoformat(),
        )
        for c in clients
    ]
    return ClientListResponse(total=len(items), items=items)


@router.post(
    "",
    response_model=ClientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="新建客户",
)
async def create_client(
    body: ClientCreate,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> ClientResponse:
    existing = await db.scalar(
        select(Client).where(Client.prefix == body.prefix.upper(), Client.deleted_at.is_(None))
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"客户前缀 '{body.prefix.upper()}' 已存在",
        )

    client = Client(
        name=body.name,
        prefix=body.prefix.upper(),
        phone=body.phone,
        company=body.company,
        address=body.address,
        license_no=body.license_no,
    )
    db.add(client)
    await db.flush()
    db.add_all([
        BillingPriceRule(
            client_id=client.id,
            base_category_type="white",
            production_type="normal",
            production_name="默认白图",
            unit_price=0,
            is_default=True,
            is_active=True,
        ),
        BillingPriceRule(
            client_id=client.id,
            base_category_type="scene",
            production_type="normal",
            production_name="默认场景图",
            unit_price=0,
            is_default=True,
            is_active=True,
        ),
    ])
    await db.refresh(client)
    await db.commit()

    return ClientResponse(
        id=client.id,
        name=client.name,
        prefix=client.prefix,
        phone=client.phone,
        company=client.company,
        address=client.address,
        license_no=client.license_no,
        avatar=client.avatar,
        created_at=client.created_at.isoformat(),
    )


@router.get("/{client_id}", response_model=ClientResponse, summary="客户详情")
async def get_client(
    client_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ClientResponse:
    client = await db.get(Client, client_id)
    if client is None or client.deleted_at is not None:
        raise HTTPException(status_code=404, detail="客户不存在")
    return ClientResponse(
        id=client.id,
        name=client.name,
        prefix=client.prefix,
        phone=client.phone,
        company=client.company,
        address=client.address,
        license_no=client.license_no,
        avatar=client.avatar,
        created_at=client.created_at.isoformat(),
    )


@router.patch("/{client_id}", response_model=ClientResponse, summary="编辑客户")
async def update_client(
    client_id: int,
    body: ClientUpdate,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> ClientResponse:
    client = await db.get(Client, client_id)
    if client is None or client.deleted_at is not None:
        raise HTTPException(status_code=404, detail="客户不存在")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(client, field, value)

    await db.commit()
    await db.refresh(client)

    return ClientResponse(
        id=client.id,
        name=client.name,
        prefix=client.prefix,
        phone=client.phone,
        company=client.company,
        address=client.address,
        license_no=client.license_no,
        avatar=client.avatar,
        created_at=client.created_at.isoformat(),
    )


@router.delete("/{client_id}", summary="删除客户")
async def delete_client(
    client_id: int,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    client = await db.get(Client, client_id)
    if client is None or client.deleted_at is not None:
        raise HTTPException(status_code=404, detail="客户不存在")

    client.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    return {"code": 200, "msg": "客户已删除", "data": None}
