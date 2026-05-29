from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="项目名称")
    client_id: int = Field(..., description="客户ID")
    template_id: int | None = Field(None, description="项目模板ID，选择后自动生成目标")
    shooting_type: str | None = Field(None, max_length=64, description="拍摄类型（自由输入或模板名称）")
    estimated_end_time: datetime | None = Field(None, description="预估结束时间")
    description: str | None = Field(None, description="项目介绍与要求")


class ProjectUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    estimated_end_time: datetime | None = None
    cover_image: str | None = None
    description: str | None = None
    project_status: str | None = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    display_id: str
    created_by: int
    folder_path: str

    model_config = {"from_attributes": True}


class ProjectInList(BaseModel):
    id: int
    name: str
    display_id: str = ""
    cover_image: str | None = None
    client_name: str | None = None
    template_name: str | None = None
    shooting_type: str | None = None
    created_by: int
    photo_count: int = 0
    target_count: int = 0
    completed_target_count: int = 0
    white_target: int = 0
    scene_target: int = 0
    white_count: int = 0
    scene_count: int = 0
    white_completed: int = 0
    scene_completed: int = 0
    estimated_end_time: str | None = None
    archived_at: str | None = None
    deleted_at: str | None = None
    description: str | None = None
    project_status: str = "not_started"
    is_manual: bool = False
    created_at: str

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    total: int = Field(..., description="项目总数")
    items: list[ProjectInList] = Field(..., description="当前页项目列表")
    skip: int
    limit: int


class ProjectGroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="组合/批次/商品组名称")
    description: str | None = Field(None, description="组合说明")
    sort_order: int = Field(0, description="排序")


class ProjectGroupUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    description: str | None = None
    sort_order: int | None = None


class ProjectGroupResponse(BaseModel):
    id: int
    project_id: int
    name: str
    description: str | None = None
    sort_order: int = 0
    target_count: int = 0
    photo_count: int = 0
    created_at: str

    model_config = {"from_attributes": True}


class ProjectGroupListResponse(BaseModel):
    items: list[ProjectGroupResponse]
    total: int


class ArchiveResponse(BaseModel):
    project_id: int
    archived_at: str
    message: str


class ProjectDetailResponse(BaseModel):
    id: int
    name: str
    display_id: str = ""
    cover_image: str | None = None
    client_id: int
    client_name: str | None = None
    created_by: int
    white_target: int = 0
    scene_target: int = 0
    white_count: int = 0
    scene_count: int = 0
    estimated_end_time: str | None = None
    archived_at: str | None = None
    description: str | None = None
    created_at: str
    photo_count: int = 0
    target_count: int = 0
    project_status: str = "not_started"
    is_manual: bool = False

    model_config = {"from_attributes": True}
