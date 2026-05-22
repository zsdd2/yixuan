from pydantic import BaseModel, Field


class ClientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, description="客户姓名")
    prefix: str = Field(..., min_length=1, max_length=10, pattern=r"^[A-Za-z]+$", description="客户前缀，仅英文字母")
    phone: str | None = Field(None, max_length=32)
    company: str | None = Field(None, max_length=128)
    address: str | None = None
    license_no: str | None = Field(None, max_length=64, description="营业执照号")


class ClientUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=64)
    phone: str | None = None
    company: str | None = None
    address: str | None = None
    license_no: str | None = None
    avatar: str | None = None


class ClientResponse(BaseModel):
    id: int
    name: str
    prefix: str
    phone: str | None = None
    company: str | None = None
    address: str | None = None
    license_no: str | None = None
    avatar: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class ClientInList(BaseModel):
    id: int
    name: str
    prefix: str
    phone: str | None = None
    company: str | None = None
    avatar: str | None = None
    project_total: int = 0
    active_projects: int = 0
    completed_projects: int = 0
    total_amount: float = 0.0
    created_at: str

    model_config = {"from_attributes": True}


class ClientListResponse(BaseModel):
    total: int
    items: list[ClientInList]
