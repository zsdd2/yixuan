from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import decode_access_token
from app.database import get_db
from app.models import User, UserRole

# HTTP Bearer Token 认证方案
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    从 JWT Token 中解析当前用户

    Args:
        credentials: HTTP Authorization Header (Bearer Token)
        db: 数据库会话

    Returns:
        当前登录用户对象

    Raises:
        HTTPException: Token 无效或用户不存在
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id: int | None = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token 荷载缺失 user_id",
        )

    # 从数据库查询用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被禁用",
        )

    return user


def require_roles(*allowed_roles: UserRole):
    """
    角色权限装饰器工厂

    用法:
        @router.get("/admin-only")
        async def admin_endpoint(current_user: User = Depends(require_roles(UserRole.super_admin, UserRole.admin))):
            ...

    Args:
        allowed_roles: 允许访问的角色列表

    Returns:
        依赖注入函数
    """

    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足，需要角色: {', '.join([r.value for r in allowed_roles])}",
            )
        return current_user

    return role_checker


# 注入快捷类型别名
CurrentUser = Annotated[User, Depends(get_current_user)]
SuperAdminUser = Annotated[User, Depends(require_roles(UserRole.super_admin))]
AdminUser = Annotated[User, Depends(require_roles(UserRole.super_admin, UserRole.admin))]
AdminUser = Annotated[User, Depends(require_roles(UserRole.super_admin, UserRole.admin))]
