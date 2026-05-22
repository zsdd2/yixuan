"""
认证路由
提供登录、修改密码、获取当前用户信息等接口
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import create_access_token, get_password_hash, verify_password
from app.database import get_db
from app.deps import CurrentUser
from app.models import User
from app.schemas.auth_schema import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    UserInfoResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.post("/login", response_model=LoginResponse, summary="用户登录")
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    用户登录接口

    - 验证用户名和密码
    - 返回 JWT Token 和用户基本信息
    """
    # 查询用户
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()

    # 验证用户存在且密码正确
    if user is None or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # 检查用户是否被禁用
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用，请联系管理员",
        )

    # 更新最后登录时间
    user.last_login_at = datetime.utcnow()
    await db.commit()

    # 生成 JWT Token
    token_data = {
        "user_id": user.id,
        "username": user.username,
        "role": user.role.value,
    }
    access_token = create_access_token(token_data)

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
    )


@router.get("/me", response_model=UserInfoResponse, summary="获取当前用户信息")
async def get_current_user_info(current_user: CurrentUser):
    """
    获取当前登录用户的基本信息

    需要认证：Bearer Token
    """
    return UserInfoResponse(
        user_id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        role=current_user.role,
        is_active=current_user.is_active,
    )


@router.put("/me/password", summary="修改当前用户密码")
async def change_password(
    request: ChangePasswordRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    修改当前用户密码

    - 需要验证旧密码
    - 新密码至少 6 位
    - 需要认证：Bearer Token
    """
    # 验证旧密码
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="当前用户未设置密码",
        )

    if not verify_password(request.old_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误",
        )

    # 更新密码
    current_user.password_hash = get_password_hash(request.new_password)
    await db.commit()

    return {"code": 200, "msg": "密码修改成功", "data": None}
