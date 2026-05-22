from pydantic import BaseModel, Field


class TargetCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="目标名称")
    category_type: str = Field("white", description="分类：white 或 scene")
    sample_path: str | None = Field(None, description="样图路径")
    requirement_desc: str | None = Field(None, description="文本要求")
    sort_order: int = Field(0, description="排序权重")


class TargetUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=128)
    category_type: str | None = None
    target_status: str | None = None
    sample_path: str | None = None
    requirement_desc: str | None = None
    sort_order: int | None = None


class TargetResponse(BaseModel):
    id: int
    project_id: int
    name: str
    category_type: str = "white"
    target_status: str = "not_started"
    is_manual: bool = False
    sample_path: str | None = None
    requirement_desc: str | None = None
    sort_order: int
    photo_count: int = 0
    raw_count: int = 0
    confirmed_count: int = 0
    retouched_count: int = 0
    final_count: int = 0
    created_at: str

    model_config = {"from_attributes": True}


class TargetListResponse(BaseModel):
    items: list[TargetResponse]
    total: int
