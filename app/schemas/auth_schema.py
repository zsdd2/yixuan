"""
认证相关 Schema
"""

from pydantic import BaseModel, Field

from app.models import UserRole


class LoginRequest(BaseModel):
    """登录请求"""

    username: str = Field(..., min_length=1, max_length=64, description="用户名")
    password: str = Field(..., min_length=1, max_length=128, description="密码")


class LoginResponse(BaseModel):
    """登录响应"""

    access_token: str = Field(..., description="JWT Token")
    token_type: str = Field(default="bearer", description="Token 类型")
    user_id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    display_name: str | None = Field(None, description="显示名称")
    role: UserRole = Field(..., description="用户角色")


class ChangePasswordRequest(BaseModel):
    """修改密码请求"""

    old_password: str = Field(..., min_length=1, max_length=128, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码（至少 6 位）")


class UserInfoResponse(BaseModel):
    """当前用户信息响应"""

    user_id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    display_name: str | None = Field(None, description="显示名称")
    role: UserRole = Field(..., description="用户角色")
    is_active: bool = Field(..., description="是否激活")
