from pydantic import BaseModel, Field


class PhotoInList(BaseModel):
    id: int
    project_id: int
    target_id: int | None = None
    parent_id: int | None = None
    display_id: int = 0
    version: int = 1
    is_confirmed: bool = False
    original_path: str
    original_filename: str | None = None
    thumbnail_path: str | None = None
    status: str
    process_state: str = "raw"
    client_notes: str | None = None
    revision_notes: str | None = None
    retouch_quality: str | None = None
    retouch_batch_id: str | None = None
    shot_at: str | None = None
    tag_ids: list[int] = Field(default_factory=list)
    deleted_at: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class PhotoListResponse(BaseModel):
    total: int = Field(..., description="总照片数")
    items: list[PhotoInList] = Field(..., description="当前页照片列表")
    skip: int
    limit: int


class PhotoResponse(BaseModel):
    id: int
    project_id: int
    target_id: int | None = None
    parent_id: int | None = None
    display_id: int = 0
    version: int = 1
    is_confirmed: bool = False
    original_path: str
    original_filename: str | None = None
    thumbnail_path: str | None = None
    status: str
    process_state: str = "raw"
    client_notes: str | None = None
    revision_notes: str | None = None
    retouch_quality: str | None = None
    retouch_batch_id: str | None = None

    model_config = {"from_attributes": True}


class ScanNasRequest(BaseModel):
    project_id: int = Field(..., description="目标项目 ID")
    target_id: int | None = Field(None, description="目标槽位 ID（可为空）")
    nas_path: str = Field(
        ...,
        description="相对于 NAS 根目录的扫描路径",
        examples=["2024/client_a"],
    )
    generate_thumbnails: bool = Field(True, description="是否生成 WebP 缩略图")
    process_state: str = Field("raw", description="入库阶段: raw/retouched/final")
    tag_ids: list[int] = Field(default_factory=list, description="入库时附加的标签ID列表")
    shot_date: str | None = Field(None, description="手动指定拍摄日期 YYYY-MM-DD；为空时自动读取 EXIF")


class ScanNasResponse(BaseModel):
    task_id: str
    message: str
    status: str


class ScanTaskStatusResponse(BaseModel):
    task_id: str
    status: str
    total: int
    processed: int
    skipped: int
    failed_files: list[str]
    error: str | None = None


class BulkUpdateRequest(BaseModel):
    photo_ids: list[int] = Field(..., min_length=1, max_length=500)
    status: str | None = Field(None, description="目标状态")
    target_id: int | None = Field(None, description="目标槽位 ID（移入）")
    remove_from_target: bool = Field(False, description="设为 true 则将照片从当前 Target 移出（target_id 置空）")
    process_state: str | None = Field(None, description="处理阶段: raw/retouched/final")


class BulkUpdateResponse(BaseModel):
    updated: int = Field(..., description="实际更新的照片数量")
    message: str


class SoftDeleteRequest(BaseModel):
    photo_ids: list[int] = Field(..., min_length=1, max_length=500)


class SoftDeleteResponse(BaseModel):
    affected: int
    message: str


class HardDeleteResponse(BaseModel):
    deleted: int = Field(..., description="删除的数据库记录数")
    files_deleted: int = Field(0, description="物理删除的文件数")
    files_missing: int = Field(0, description="路径不存在或已被清理的文件数")
    errors: list[str] = Field(default_factory=list, description="删除过程中的错误")


class BulkTagRequest(BaseModel):
    photo_ids: list[int] = Field(..., min_length=1, max_length=500)
    tag_ids: list[int] = Field(..., min_length=1, description="要添加或移除的标签ID")


class BulkTagResponse(BaseModel):
    affected: int
    message: str


# ── 作品中心 (Portfolio) ──────────────────────────────────

class PortfolioItem(BaseModel):
    id: int
    project_id: int
    project_name: str = ""
    display_id: str = ""
    client_name: str = ""
    shooting_type: str | None = None
    target_name: str | None = None
    category_type: str | None = None
    thumbnail_path: str | None = None
    original_path: str
    original_filename: str | None = None
    process_state: str = "raw"
    shot_at: str | None = None
    created_at: str


class PortfolioListResponse(BaseModel):
    total: int
    items: list[PortfolioItem]


class PortfolioFilterOption(BaseModel):
    id: int
    name: str


class PortfolioFilterResponse(BaseModel):
    shooting_types: list[str]
    clients: list[PortfolioFilterOption]
    projects: list[PortfolioFilterOption]
    target_names: list[str]


# ── 确认原图 & 精修备注 ─────────────────────────────────────

class ConfirmRawRequest(BaseModel):
    photo_ids: list[int] = Field(..., min_length=1, max_length=500)


class UpdateNotesRequest(BaseModel):
    client_notes: str | None = None
    revision_notes: str | None = None
