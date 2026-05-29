"""User management schemas."""

from pydantic import BaseModel, Field

from app.models import UserRole


class UserInList(BaseModel):
    id: int
    username: str
    display_name: str | None
    role: UserRole
    can_delete_projects: bool = False
    project_ids: list[int] = Field(default_factory=list)
    is_active: bool
    last_login_at: str | None = None
    created_at: str


class UserListResponse(BaseModel):
    total: int
    items: list[UserInList]
    skip: int
    limit: int


class UserCreateRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    display_name: str | None = Field(None, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    role: UserRole = Field(default=UserRole.staff)
    can_delete_projects: bool = False
    project_ids: list[int] = Field(default_factory=list)
    is_active: bool = True


class UserUpdateRequest(BaseModel):
    display_name: str | None = Field(None, max_length=64)
    password: str | None = Field(None, min_length=6, max_length=128)
    role: UserRole | None = None
    can_delete_projects: bool | None = None
    project_ids: list[int] | None = None
    is_active: bool | None = None


class UserDetailResponse(BaseModel):
    id: int
    username: str
    display_name: str | None
    role: UserRole
    can_delete_projects: bool = False
    project_ids: list[int] = Field(default_factory=list)
    is_active: bool
    last_login_at: str | None
    created_at: str
