from pydantic import BaseModel, Field


class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="标签名称")
    color: str = Field("#409eff", max_length=20, description="标签颜色")
    sort_order: int = Field(0, description="排序权重")
    scope: str = Field("project", description="project=项目临时标签，system=通用标签同步标签")


class TagUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    color: str | None = Field(None, max_length=20)
    sort_order: int | None = None


class TagResponse(BaseModel):
    id: int
    project_id: int
    name: str
    color: str
    scope: str = "project"
    sort_order: int
    created_at: str

    model_config = {"from_attributes": True}


class TagListResponse(BaseModel):
    items: list[TagResponse]
    total: int


class ProjectTagUsageItem(BaseModel):
    name: str
    color: str
    project_count: int
    photo_count: int


class ProjectTagUsageResponse(BaseModel):
    items: list[ProjectTagUsageItem]
    total: int


class PromoteProjectTagRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    color: str = Field("#409eff", max_length=20)
