from datetime import datetime

from pydantic import BaseModel, Field


class DeliverySessionCreate(BaseModel):
    project_id: int = Field(..., description="项目ID")
    expired_days: int = Field(30, ge=1, le=90, description="有效期天数（1-90天）")


class DeliverySessionResponse(BaseModel):
    token: str
    share_url: str
    expired_at: datetime
    zip_status: str
    zip_path: str | None = None

    model_config = {"from_attributes": True}


class DeliveryPageData(BaseModel):
    project_id: int
    project_name: str
    project_display_id: str
    client_name: str
    expired_at: datetime
    is_expired: bool
    zip_status: str
    zip_path: str | None = None
    zip_size: int | None = None  # 字节
    photo_count: int

    model_config = {"from_attributes": True}


class DeliverySessionInList(BaseModel):
    id: int
    token: str
    created_by_name: str | None = None
    created_at: datetime
    expired_at: datetime
    is_disabled: bool
    zip_status: str

    model_config = {"from_attributes": True}


class DeliverySessionListResponse(BaseModel):
    total: int
    items: list[DeliverySessionInList]
