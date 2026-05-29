"""
schemas/review_schema.py —— 客户审核系统 Schema
"""
from pydantic import BaseModel, Field, ConfigDict


# ── 创建审核会话 ──────────────────────────────────────────

class PhotoSelection(BaseModel):
    photo_id: int
    version: int | None = None
    category_type: str
    target_name: str


class CreateReviewRequest(BaseModel):
    project_id: int
    photo_selections: list[PhotoSelection]
    review_stage: str = Field(default="raw", description="Review stage: raw/retouched/final")
    expired_days: int = Field(default=7, ge=1, le=30, description="过期天数（1-30天）")


class CreateReviewResponse(BaseModel):
    token: str
    share_url: str
    expired_at: str


# ── 获取审核页面数据 ──────────────────────────────────────

class ReviewPhotoItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    display_id: int
    original_filename: str | None
    thumbnail_path: str
    version: int | None
    parent_id: int | None
    process_state: str
    target_name: str
    feedback: dict | None = None


class ReviewTargetGroup(BaseModel):
    target_name: str
    photos: list[ReviewPhotoItem]
    confirmed_count: int = 0
    total_count: int = 0


class ReviewCategoryGroup(BaseModel):
    category_type: str
    category_label: str
    targets: list[ReviewTargetGroup]


class ReviewSessionData(BaseModel):
    project_id: int
    project_name: str
    project_display_id: str
    cover_image: str | None
    client_name: str | None
    expired_at: str
    is_expired: bool
    review_stage: str = "raw"
    review_stage_label: str = "原图审核"
    categories: list[ReviewCategoryGroup]


# ── 提交反馈 ──────────────────────────────────────────────

class SubmitFeedbackRequest(BaseModel):
    photo_id: int
    is_confirmed: bool
    feedback_status: str | None = Field(default=None, description="approved/revision/discarded")
    comment: str | None = None
    annotation_image: str | None = None
    mark_as_final: bool = False  # 是否标记为最终成图（仅精修图可用）


# ── 反馈列表（Admin 端查询） ──────────────────────────────────

class FeedbackItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    photo_id: int
    is_confirmed: bool
    feedback_status: str | None = None
    comment: str | None
    annotation_path: str | None = None
    created_at: str


class SessionFeedbackResponse(BaseModel):
    session_id: int
    token: str
    is_viewed: bool
    viewed_at: str | None
    feedbacks: list[FeedbackItem]


# ── 会话管理（Admin 端） ──────────────────────────────────

class SessionStatistics(BaseModel):
    raw_confirmed: int = 0
    retouched_confirmed: int = 0
    final_confirmed: int = 0
    reviewed_total: int = 0
    approved_total: int = 0
    revision_total: int = 0
    discarded_total: int = 0


class ReviewSessionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    token: str
    created_by_name: str | None
    created_at: str
    expired_at: str
    is_viewed: bool
    viewed_at: str | None
    is_disabled: bool
    review_stage: str = "raw"
    review_stage_label: str = "原图审核"
    statistics: SessionStatistics


class SessionListResponse(BaseModel):
    sessions: list[ReviewSessionItem]
