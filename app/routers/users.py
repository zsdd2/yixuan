"""
用户管理路由
提供用户列表、创建、更新、角色修改等接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete as sa_delete, func as sa_func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash
from app.database import get_db
from app.deps import AdminUser
from app.models import User, user_project_access
from app.schemas.user_schema import (
    UserCreateRequest,
    UserDetailResponse,
    UserInList,
    UserListResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/api/v1/users", tags=["用户管理"])


async def _project_ids_for_user(db: AsyncSession, user_id: int) -> list[int]:
    rows = (await db.execute(
        select(user_project_access.c.project_id).where(user_project_access.c.user_id == user_id)
    )).scalars().all()
    return list(rows)


@router.get("", response_model=UserListResponse, summary="获取用户列表")
async def list_users(
    current_user: AdminUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, description="搜索用户名或显示名称"),
    role_filter: str | None = Query(None, description="按角色过滤"),
    is_active: bool | None = Query(None, description="按激活状态过滤"),
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户列表

    需要权限：super_admin 或 admin
    """
    base_where = []

    if search:
        keyword = f"%{search}%"
        base_where.append(
            (User.username.ilike(keyword)) | (User.display_name.ilike(keyword))
        )

    if role_filter:
        base_where.append(User.role == role_filter)

    if is_active is not None:
        base_where.append(User.is_active == is_active)

    # 统计总数
    count_stmt = select(sa_func.count(User.id))
    if base_where:
        for w in base_where:
            count_stmt = count_stmt.where(w)
    total = (await db.execute(count_stmt)).scalar() or 0

    # 查询用户列表
    users_stmt = select(User).order_by(User.created_at.desc())
    if base_where:
        for w in base_where:
            users_stmt = users_stmt.where(w)
    users_stmt = users_stmt.offset(skip).limit(limit)
    users = (await db.execute(users_stmt)).scalars().all()
    access_rows = (await db.execute(select(user_project_access))).all()
    access_map: dict[int, list[int]] = {}
    for row in access_rows:
        access_map.setdefault(row._mapping["user_id"], []).append(row._mapping["project_id"])

    items = [
        UserInList(
            id=u.id,
            username=u.username,
            display_name=u.display_name,
            role=u.role,
            can_delete_projects=getattr(u, "can_delete_projects", False),
            project_ids=access_map.get(u.id, []),
            is_active=u.is_active,
            last_login_at=u.last_login_at.isoformat() if u.last_login_at else None,
            created_at=u.created_at.isoformat(),
        )
        for u in users
    ]

    return UserListResponse(total=total, items=items, skip=skip, limit=limit)


@router.post("", response_model=UserDetailResponse, summary="创建用户")
async def create_user(
    request: UserCreateRequest,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """
    创建新用户

    需要权限：super_admin 或 admin
    """
    # 检查用户名是否已存在
    existing = await db.execute(select(User).where(User.username == request.username))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"用户名 '{request.username}' 已存在",
        )

    # 创建用户
    new_user = User(
        username=request.username,
        display_name=request.display_name,
        password_hash=get_password_hash(request.password),
        role=request.role,
        can_delete_projects=request.can_delete_projects,
        is_active=request.is_active,
    )

    db.add(new_user)
    await db.flush()
    for pid in request.project_ids:
        await db.execute(user_project_access.insert().values(user_id=new_user.id, project_id=pid))
    try:
        await db.commit()
        await db.refresh(new_user)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户创建失败，用户名可能重复",
        )

    return UserDetailResponse(
        id=new_user.id,
        username=new_user.username,
        display_name=new_user.display_name,
        role=new_user.role,
        can_delete_projects=getattr(new_user, "can_delete_projects", False),
        project_ids=request.project_ids,
        is_active=new_user.is_active,
        last_login_at=new_user.last_login_at.isoformat() if new_user.last_login_at else None,
        created_at=new_user.created_at.isoformat(),
    )


@router.get("/{user_id}", response_model=UserDetailResponse, summary="获取用户详情")
async def get_user(
    user_id: int,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """
    获取用户详情

    需要权限：super_admin 或 admin
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 id={user_id} 不存在",
        )

    return UserDetailResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
        can_delete_projects=getattr(user, "can_delete_projects", False),
        project_ids=await _project_ids_for_user(db, user.id),
        is_active=user.is_active,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        created_at=user.created_at.isoformat(),
    )


@router.patch("/{user_id}", summary="更新用户信息")
async def update_user(
    user_id: int,
    request: UserUpdateRequest,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """
    更新用户信息（角色、显示名称、激活状态）

    需要权限：super_admin 或 admin
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 id={user_id} 不存在",
        )

    # 更新字段
    if request.display_name is not None:
        user.display_name = request.display_name
    if request.password is not None:
        user.password_hash = get_password_hash(request.password)
    if request.role is not None:
        user.role = request.role
    if request.can_delete_projects is not None:
        user.can_delete_projects = request.can_delete_projects
    if request.project_ids is not None:
        await db.execute(sa_delete(user_project_access).where(user_project_access.c.user_id == user_id))
        for pid in request.project_ids:
            await db.execute(user_project_access.insert().values(user_id=user_id, project_id=pid))
    if request.is_active is not None:
        user.is_active = request.is_active

    await db.commit()

    return {"code": 200, "msg": "用户信息更新成功", "data": None}


@router.delete("/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """
    删除用户

    需要权限：super_admin 或 admin
    注意：删除用户前需确保该用户没有关联的项目或其他数据
    """
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 id={user_id} 不存在",
        )

    # 防止删除自己
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除当前登录用户",
        )

    try:
        await db.execute(sa_delete(user_project_access).where(user_project_access.c.user_id == user_id))
        await db.delete(user)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="删除失败，该用户可能关联了项目或其他数据",
        )

    return {"code": 200, "msg": "用户删除成功", "data": None}
