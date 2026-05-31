from pydantic import BaseModel, Field


class PhotoInList(BaseModel):
    id: int
    project_id: int
    group_id: int | None = None
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
    group_name: str | None = None
    target_name: str | None = None
    category_type: str | None = None
    reference_count: int = 0
    is_referenced: bool = False
    shot_at: str | None = None
    tag_ids: list[int] = Field(default_factory=list)
    portfolio_tag_ids: list[int] = Field(default_factory=list)
    deleted_at: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class PhotoListResponse(BaseModel):
    total: int
    items: list[PhotoInList]
    skip: int
    limit: int


class PhotoResponse(BaseModel):
    id: int
    project_id: int
    group_id: int | None = None
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
    group_name: str | None = None
    target_name: str | None = None

    model_config = {"from_attributes": True}


class FolderTagRule(BaseModel):
    path: str = Field(".", description="相对扫描根目录的文件夹路径，'.' 表示扫描根目录全部文件")
    tag_names: list[str] = Field(default_factory=list, description="该文件夹下文件自动挂载的标签名称")


class ScanNasRequest(BaseModel):
    project_id: int
    group_id: int | None = None
    target_id: int | None = None
    nas_path: str
    generate_thumbnails: bool = True
    process_state: str = "raw"
    tag_ids: list[int] = Field(default_factory=list)
    folder_tag_rules: list[FolderTagRule] = Field(default_factory=list)
    shot_date: str | None = None


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
    status: str | None = None
    group_id: int | None = None
    remove_from_group: bool = False
    target_id: int | None = None
    remove_from_target: bool = False
    process_state: str | None = None


class BulkUpdateResponse(BaseModel):
    updated: int
    message: str


class SoftDeleteRequest(BaseModel):
    photo_ids: list[int] = Field(..., min_length=1, max_length=500)


class SoftDeleteResponse(BaseModel):
    affected: int
    message: str


class HardDeleteResponse(BaseModel):
    deleted: int
    files_deleted: int = 0
    files_missing: int = 0
    errors: list[str] = Field(default_factory=list)


class BulkTagRequest(BaseModel):
    photo_ids: list[int] = Field(..., min_length=1, max_length=500)
    tag_ids: list[int] = Field(..., min_length=1)


class BulkTagResponse(BaseModel):
    affected: int
    message: str


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
    portfolio_tag_ids: list[int] = Field(default_factory=list)
    shot_at: str | None = None
    created_at: str


class PortfolioTagsUpdateRequest(BaseModel):
    tag_ids: list[int] = Field(default_factory=list, max_length=50)


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


class ConfirmRawRequest(BaseModel):
    photo_ids: list[int] = Field(..., min_length=1, max_length=500)


class UpdateNotesRequest(BaseModel):
    client_notes: str | None = None
    revision_notes: str | None = None
