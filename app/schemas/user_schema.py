"""
用户管理相关 Schema
"""

from pydantic import BaseModel, Field

from app.models import UserRole


class UserInList(BaseModel):
    """用户列表项"""

    id: int
    username: str
    display_name: str | None
    role: UserRole
    is_active: bool
    last_login_at: str | None = None
    created_at: str


class UserListResponse(BaseModel):
    """用户列表响应"""

    total: int
    items: list[UserInList]
    skip: int
    limit: int


class UserCreateRequest(BaseModel):
    """创建用户请求"""

    username: str = Field(..., min_length=1, max_length=64, description="用户名（唯一）")
    display_name: str | None = Field(None, max_length=64, description="显示名称")
    password: str = Field(..., min_length=6, max_length=128, description="初始密码（至少 6 位）")
    role: UserRole = Field(default=UserRole.staff, description="用户角色")
    is_active: bool = Field(default=True, description="是否激活")


class UserUpdateRequest(BaseModel):
    """更新用户请求"""

    display_name: str | None = Field(None, max_length=64, description="显示名称")
    role: UserRole | None = Field(None, description="用户角色")
    is_active: bool | None = Field(None, description="是否激活")


class UserDetailResponse(BaseModel):
    """用户详情响应"""

    id: int
    username: str
    display_name: str | None
    role: UserRole
    is_active: bool
    last_login_at: str | None
    created_at: str
