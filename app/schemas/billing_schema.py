from pydantic import BaseModel, Field


class BillingPriceRuleBase(BaseModel):
    base_category_type: str = Field(..., min_length=1, max_length=32)
    production_type: str = Field(..., min_length=1, max_length=32)
    production_name: str = Field(..., min_length=1, max_length=64)
    unit_price: float = Field(0, ge=0)
    is_default: bool = False
    is_active: bool = True


class BillingPriceRuleCreate(BillingPriceRuleBase):
    pass


class BillingPriceRuleUpdate(BaseModel):
    production_name: str | None = Field(None, min_length=1, max_length=64)
    unit_price: float | None = Field(None, ge=0)
    is_default: bool | None = None
    is_active: bool | None = None


class BillingPriceRuleResponse(BillingPriceRuleBase):
    id: int
    client_id: int
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class BillingPriceRuleListResponse(BaseModel):
    items: list[BillingPriceRuleResponse]
    total: int


class ProjectBillingItemCreate(BaseModel):
    base_category_type: str = Field("manual", min_length=1, max_length=32)
    production_type: str = Field("manual", min_length=1, max_length=32)
    production_name: str = Field("手动费用", min_length=1, max_length=64)
    quantity: float = Field(1, gt=0)
    unit_price: float = 0
    notes: str | None = None


class ProjectBillingItemUpdate(BaseModel):
    base_category_type: str | None = Field(None, min_length=1, max_length=32)
    production_type: str | None = Field(None, min_length=1, max_length=32)
    production_name: str | None = Field(None, min_length=1, max_length=64)
    quantity: float | None = Field(None, gt=0)
    unit_price: float | None = None
    notes: str | None = None
    is_excluded: bool | None = None


class ProjectBillingItemResponse(BaseModel):
    id: int
    project_id: int
    photo_id: int | None = None
    target_id: int | None = None
    target_name: str | None = None
    display_id: int | None = None
    thumbnail_path: str | None = None
    original_path: str | None = None
    base_category_type: str
    production_type: str
    production_name: str
    quantity: float
    unit_price: float
    amount: float
    source: str
    notes: str | None = None
    is_excluded: bool
    created_at: str
    updated_at: str


class ProjectBillingSummaryResponse(BaseModel):
    project_id: int
    subtotal_amount: float
    adjustment_amount: float
    total_amount: float
    billing_status: str
    confirmed_at: str | None = None
    paid_at: str | None = None
    paid_by: int | None = None
    notes: str | None = None
    work_status: str
    work_completed: bool
    payment_completed: bool


class ProjectBillingResponse(BaseModel):
    summary: ProjectBillingSummaryResponse
    items: list[ProjectBillingItemResponse]
    price_rules: list[BillingPriceRuleResponse]
    final_photo_count: int


class BillingConfirmRequest(BaseModel):
    notes: str | None = None
