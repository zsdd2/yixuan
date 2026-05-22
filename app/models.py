import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    Sequence,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ── 枚举类型 ──────────────────────────────────────────────

class UserRole(str, enum.Enum):
    super_admin = "super_admin"
    admin = "admin"
    staff = "staff"
    client = "client"


class PhotoStatus(str, enum.Enum):
    pending = "pending"
    selected = "selected"
    deleted = "deleted"


class CategoryType(str, enum.Enum):
    white = "white"
    scene = "scene"


class TargetStatus(str, enum.Enum):
    not_started = "not_started"
    shooting = "shooting"
    retouching = "retouching"
    client_review = "client_review"
    completed = "completed"


class ProjectStatus(str, enum.Enum):
    not_started = "not_started"
    shooting = "shooting"
    retouching = "retouching"
    client_review = "client_review"
    completed = "completed"


class ProcessState(str, enum.Enum):
    raw = "raw"
    retouched = "retouched"
    final = "final"


class ZipStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


# ── 模型定义 ──────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), nullable=False, default=UserRole.staff
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    projects_created: Mapped[list["Project"]] = relationship(
        "Project", foreign_keys="Project.created_by", back_populates="creator"
    )
    projects_as_customer: Mapped[list["Project"]] = relationship(
        "Project", foreign_keys="Project.customer_id", back_populates="customer"
    )


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    prefix: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    company: Mapped[str | None] = mapped_column(String(128), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    license_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    avatar: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    projects: Mapped[list["Project"]] = relationship(
        "Project", foreign_keys="Project.client_id", back_populates="client"
    )


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    cover_image: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)

    client_prefix: Mapped[str] = mapped_column(String(10), nullable=False, default="")
    serial_number: Mapped[int] = mapped_column(
        Integer,
        Sequence("project_serial_seq"),
        unique=True,
        nullable=False,
    )
    estimated_end_time: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    white_target: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    scene_target: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    shooting_type: Mapped[str | None] = mapped_column(String(64), nullable=True)

    template_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("project_templates.id", ondelete="SET NULL"), nullable=True
    )
    client_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False
    )
    customer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True,
        comment="关联客户用户账号（role=client）"
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    project_status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"),
        nullable=False, default=ProjectStatus.not_started,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    has_shared: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )
    zip_path: Mapped[str | None] = mapped_column(
        String(512), nullable=True, default=None
    )
    zip_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    zip_generated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    @hybrid_property
    def display_id(self) -> str:
        prefix = self.client_prefix or ""
        return f"{prefix}{self.serial_number:06d}"

    client: Mapped["Client"] = relationship("Client", foreign_keys=[client_id], back_populates="projects")
    customer: Mapped["User | None"] = relationship("User", foreign_keys=[customer_id], back_populates="projects_as_customer")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by], back_populates="projects_created")
    template: Mapped["ProjectTemplate | None"] = relationship("ProjectTemplate", foreign_keys=[template_id])
    targets: Mapped[list["ProjectTarget"]] = relationship("ProjectTarget", back_populates="project", cascade="all, delete-orphan")
    photos: Mapped[list["Photo"]] = relationship("Photo", back_populates="project", cascade="all, delete-orphan")
    tags_list: Mapped[list["ProjectTag"]] = relationship("ProjectTag", back_populates="project", cascade="all, delete-orphan")


class ProjectTarget(Base):
    __tablename__ = "project_targets"
    __table_args__ = (
        UniqueConstraint('project_id', 'name', name='uq_project_target_name'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category_type: Mapped[CategoryType] = mapped_column(
        Enum(CategoryType, name="category_type"), nullable=False, default=CategoryType.white
    )
    target_status: Mapped[TargetStatus] = mapped_column(
        Enum(TargetStatus, name="target_status"), nullable=False, default=TargetStatus.not_started
    )
    folder_path: Mapped[str | None] = mapped_column(
        String(512), nullable=True, index=True,
        comment="NAS相对路径，用于照片自动关联"
    )
    sample_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    requirement_desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_manual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, index=True
    )

    project: Mapped["Project"] = relationship("Project", back_populates="targets")
    photos: Mapped[list["Photo"]] = relationship("Photo", back_populates="target")


class TargetReferenceAsset(Base):
    __tablename__ = "target_reference_assets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    target_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("project_targets.id", ondelete="CASCADE"), nullable=False, index=True
    )
    asset_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    photo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    target: Mapped["ProjectTarget"] = relationship("ProjectTarget")
    photo: Mapped["Photo"] = relationship("Photo")


# ── 标签系统 ──────────────────────────────────────────────

photo_tags = Table(
    "photo_tags",
    Base.metadata,
    Column("photo_id", BigInteger, ForeignKey("photos.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", BigInteger, ForeignKey("project_tags.id", ondelete="CASCADE"), primary_key=True),
)


class ProjectTag(Base):
    __tablename__ = "project_tags"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#409eff")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project: Mapped["Project"] = relationship("Project", back_populates="tags_list")
    photos: Mapped[list["Photo"]] = relationship("Photo", secondary=photo_tags, back_populates="tags")


class Photo(Base):
    __tablename__ = "photos"
    __table_args__ = (
        UniqueConstraint('project_id', 'display_id', name='uq_project_photo_display_id'),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("project_targets.id", ondelete="SET NULL"), nullable=True
    )
    parent_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("photos.id", ondelete="SET NULL"), nullable=True
    )
    display_id: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="项目内自增展示编号"
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="客户确认后锁定，防止误删")
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    file_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    thumbnail_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PhotoStatus] = mapped_column(
        Enum(PhotoStatus, name="photo_status"),
        nullable=False,
        default=PhotoStatus.pending,
    )
    process_state: Mapped[ProcessState] = mapped_column(
        Enum(ProcessState, name="process_state"),
        nullable=False,
        default=ProcessState.raw,
    )
    client_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None,
    )
    revision_notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None,
    )
    retouch_quality: Mapped[str | None] = mapped_column(
        String(32), nullable=True, default=None,
    )
    retouch_batch_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default=None, index=True,
    )
    shot_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project: Mapped["Project"] = relationship("Project", back_populates="photos")
    target: Mapped["ProjectTarget | None"] = relationship("ProjectTarget", back_populates="photos")
    tags: Mapped[list["ProjectTag"]] = relationship("ProjectTag", secondary=photo_tags, back_populates="photos")
    parent: Mapped["Photo | None"] = relationship("Photo", remote_side="Photo.id", foreign_keys=[parent_id])
    children: Mapped[list["Photo"]] = relationship("Photo", foreign_keys=[parent_id])


# ── 全局标签 ──────────────────────────────────────────────

class SystemTag(Base):
    __tablename__ = "system_tags"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(20), nullable=False, default="#409eff")
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ── 系统图库 ──────────────────────────────────────────────

class SystemImage(Base):
    __tablename__ = "system_images"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(32), nullable=False, default="other")
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    tags: Mapped[str | None] = mapped_column(String(512), nullable=True)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    thumbnail_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


# ── 项目模板系统 ──────────────────────────────────────────

class SystemTargetDictionary(Base):
    __tablename__ = "system_target_dictionary"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    category_type: Mapped[CategoryType] = mapped_column(
        Enum(CategoryType, name="category_type", create_type=False),
        nullable=False, default=CategoryType.white,
    )
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ProjectTemplate(Base):
    __tablename__ = "project_templates"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    target_dictionary: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    targets: Mapped[list["TemplateTarget"]] = relationship(
        "TemplateTarget", back_populates="template", cascade="all, delete-orphan"
    )


class TemplateTarget(Base):
    __tablename__ = "template_targets"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    template_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("project_templates.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    category_type: Mapped[CategoryType] = mapped_column(
        Enum(CategoryType, name="category_type", create_type=False), nullable=False, default=CategoryType.white
    )
    sample_image_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("system_images.id", ondelete="SET NULL"), nullable=True
    )
    requirement_desc: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    template: Mapped["ProjectTemplate"] = relationship("ProjectTemplate", back_populates="targets")
    sample_image: Mapped["SystemImage | None"] = relationship("SystemImage")


# ── 用户项目权限 ──────────────────────────────────────────

user_project_access = Table(
    "user_project_access",
    Base.metadata,
    Column("user_id", BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("project_id", BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True),
)


# ── 客户审核系统 ──────────────────────────────────────────

class ReviewSession(Base):
    __tablename__ = "review_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    created_by: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    selected_photos: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_viewed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_disabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project: Mapped["Project"] = relationship("Project", foreign_keys=[project_id])
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])
    feedbacks: Mapped[list["ReviewFeedback"]] = relationship(
        "ReviewFeedback", back_populates="session", cascade="all, delete-orphan"
    )


class ReviewFeedback(Base):
    __tablename__ = "review_feedbacks"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("review_sessions.id", ondelete="CASCADE"), nullable=False
    )
    photo_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("photos.id", ondelete="CASCADE"), nullable=False
    )
    is_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    annotation_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["ReviewSession"] = relationship("ReviewSession", back_populates="feedbacks")
    photo: Mapped["Photo"] = relationship("Photo")


# ── 交付分享系统 ──────────────────────────────────────────────

class DeliverySession(Base):
    __tablename__ = "delivery_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    token: Mapped[str] = mapped_column(String(36), unique=True, nullable=False, index=True)
    project_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expired_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_disabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    project: Mapped["Project"] = relationship("Project")
    creator: Mapped["User | None"] = relationship("User")


class SystemConfig(Base):
    __tablename__ = "system_configs"

    config_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    config_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

