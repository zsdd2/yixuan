from pydantic import BaseModel, Field


# ── 全局标签 ──────────────────────────────────────────────

class SystemTagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    color: str = Field("#409eff", max_length=20)
    sort_order: int = 0


class SystemTagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    color: str | None = Field(None, max_length=20)
    sort_order: int | None = None


class SystemTagResponse(BaseModel):
    id: int
    name: str
    color: str
    sort_order: int
    created_at: str
    model_config = {"from_attributes": True}


class SystemTagListResponse(BaseModel):
    total: int
    items: list[SystemTagResponse]


# ── 系统图库 ──────────────────────────────────────────────

class SystemImageResponse(BaseModel):
    id: int
    category: str
    name: str
    tags: str | None = None
    original_path: str
    thumbnail_path: str | None = None
    created_at: str
    model_config = {"from_attributes": True}


class SystemImageListResponse(BaseModel):
    total: int
    items: list[SystemImageResponse]


# ── 目标名称字典 ──────────────────────────────────────────

class DictEntryItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    category_type: str = Field("white")


class DictEntryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    category_type: str = Field("white")


class DictEntryResponse(BaseModel):
    id: int
    name: str
    category_type: str
    is_system: bool = True
    created_at: str
    model_config = {"from_attributes": True}


class DictEntryListResponse(BaseModel):
    total: int
    items: list[DictEntryResponse]


# ── 项目模板 ──────────────────────────────────────────────

class TemplateTargetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    category_type: str = Field("white")
    sample_image_id: int | None = None
    requirement_desc: str | None = None
    sort_order: int = 0


class TemplateTargetResponse(BaseModel):
    id: int
    template_id: int
    name: str
    category_type: str
    sample_image_id: int | None = None
    sample_thumbnail: str | None = None
    requirement_desc: str | None = None
    sort_order: int
    model_config = {"from_attributes": True}


class TemplateCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    description: str | None = None
    targets: list[TemplateTargetCreate] = Field(default_factory=list)
    target_dictionary: list[DictEntryItem] = Field(default_factory=list)


class TemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    description: str | None = None
    target_dictionary: list[DictEntryItem] | None = None


class TemplateResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_builtin: bool = False
    target_count: int = 0
    created_at: str
    model_config = {"from_attributes": True}


class TemplateDetailResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    is_builtin: bool = False
    targets: list[TemplateTargetResponse] = []
    target_dictionary: list[DictEntryItem] = []
    created_at: str
    model_config = {"from_attributes": True}


class TemplateListResponse(BaseModel):
    total: int
    items: list[TemplateResponse]


# ── 用户管理 ──────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=1, max_length=64)
    display_name: str | None = Field(None, max_length=64)
    password: str | None = Field(None, description="暂不启用认证")
    role: str = Field("staff")


class UserUpdate(BaseModel):
    display_name: str | None = None
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str | None = None
    role: str
    is_active: bool = True
    created_at: str
    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    total: int
    items: list[UserResponse]


class UserAccessUpdate(BaseModel):
    project_ids: list[int] = Field(default_factory=list)


class UserAccessResponse(BaseModel):
    user_id: int
    project_ids: list[int]
