"""
routers/settings.py —— 设置中心（系统图库 / 项目模板 / 用户管理）
"""
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from sqlalchemy import select, func as sa_func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_password_hash
from app.database import get_db
from app.deps import AdminUser, CurrentUser
from app.models import (
    CategoryType, Client, Project, ProjectTarget, ProjectTemplate,
    SystemImage, SystemTag, SystemTargetDictionary, TemplateTarget, User, UserRole,
    user_project_access,
)
from app.schemas.settings_schema import (
    DictEntryCreate, DictEntryListResponse, DictEntryResponse,
    SystemImageListResponse, SystemImageResponse,
    SystemTagCreate, SystemTagListResponse, SystemTagResponse, SystemTagUpdate,
    TemplateCreate, TemplateDetailResponse, TemplateListResponse,
    TemplateResponse, TemplateTargetCreate, TemplateTargetResponse,
    TemplateUpdate,
    UserAccessResponse, UserAccessUpdate,
    UserCreate, UserListResponse, UserResponse, UserUpdate,
)
from app.routers.photos import _save_and_thumbnail

import os
SYSTEM_ROOT = Path(os.environ.get("NAS_MOUNT_PATH", "/mnt/nas_data")) / "system"
NAS_ROOT = Path(os.environ.get("NAS_MOUNT_PATH", "/mnt/nas_data"))
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic"}

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


# ═══════════════════ 全局标签 ═══════════════════════════════

@router.get("/tags", response_model=SystemTagListResponse, summary="全局标签列表")
async def list_system_tags(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> SystemTagListResponse:
    rows = (await db.execute(
        select(SystemTag).order_by(SystemTag.sort_order, SystemTag.id)
    )).scalars().all()
    items = [
        SystemTagResponse(
            id=r.id, name=r.name, color=r.color,
            sort_order=r.sort_order, created_at=r.created_at.isoformat(),
        ) for r in rows
    ]
    return SystemTagListResponse(total=len(items), items=items)


@router.post("/tags", response_model=SystemTagResponse, status_code=201, summary="新增全局标签")
async def create_system_tag(
    body: SystemTagCreate,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> SystemTagResponse:
    existing = await db.scalar(select(SystemTag).where(SystemTag.name == body.name))
    if existing:
        raise HTTPException(409, f"标签 '{body.name}' 已存在")
    tag = SystemTag(name=body.name, color=body.color, sort_order=body.sort_order)
    db.add(tag)
    await db.flush()
    await db.refresh(tag)
    await db.commit()
    return SystemTagResponse(
        id=tag.id, name=tag.name, color=tag.color,
        sort_order=tag.sort_order, created_at=tag.created_at.isoformat(),
    )


@router.patch("/tags/{tag_id}", response_model=SystemTagResponse, summary="编辑全局标签")
async def update_system_tag(
    tag_id: int,
    body: SystemTagUpdate,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> SystemTagResponse:
    tag = await db.get(SystemTag, tag_id)
    if tag is None:
        raise HTTPException(404, "标签不存在")
    if body.name is not None:
        dup = await db.scalar(select(SystemTag).where(SystemTag.name == body.name, SystemTag.id != tag_id))
        if dup:
            raise HTTPException(409, f"标签 '{body.name}' 已存在")
        tag.name = body.name
    if body.color is not None:
        tag.color = body.color
    if body.sort_order is not None:
        tag.sort_order = body.sort_order
    await db.commit()
    await db.refresh(tag)
    return SystemTagResponse(
        id=tag.id, name=tag.name, color=tag.color,
        sort_order=tag.sort_order, created_at=tag.created_at.isoformat(),
    )


@router.delete("/tags/{tag_id}", summary="删除全局标签")
async def delete_system_tag(
    tag_id: int,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    tag = await db.get(SystemTag, tag_id)
    if tag is None:
        raise HTTPException(404, "标签不存在")
    await db.delete(tag)
    await db.commit()
    return {"code": 200, "msg": "标签已删除", "data": None}


# ═══════════════════ 系统图库 ═══════════════════════════════

@router.post("/images/upload", response_model=SystemImageResponse, status_code=201, summary="上传系统图片")
async def upload_system_image(
    current_user: AdminUser,
    category: str = Form("other"),
    name: str | None = Form(None),
    tags: str | None = Form(None),
    file: UploadFile = ...,
    db: AsyncSession = Depends(get_db),
) -> SystemImageResponse:
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(400, "上传文件为空")

    suffix = Path(file.filename or "img.jpg").suffix.lower() or ".jpg"
    raw_dir = SYSTEM_ROOT / "raw"
    thumb_dir = SYSTEM_ROOT / "thumb"

    try:
        original_path, thumb_path, _ = await run_in_threadpool(
            _save_and_thumbnail, raw_dir, thumb_dir, file_bytes, suffix,
        )
    except Exception as exc:
        raise HTTPException(500, f"图片处理失败：{exc}")

    img = SystemImage(
        category=category,
        name=name or file.filename or "upload",
        tags=tags,
        original_path=str(original_path),
        thumbnail_path=str(thumb_path),
    )
    db.add(img)
    await db.flush()
    await db.refresh(img)
    await db.commit()

    return SystemImageResponse(
        id=img.id, category=img.category, name=img.name,
        tags=img.tags,
        original_path=img.original_path, thumbnail_path=img.thumbnail_path,
        created_at=img.created_at.isoformat(),
    )


@router.get("/images", response_model=SystemImageListResponse, summary="系统图片列表")
async def list_system_images(
    current_user: CurrentUser,
    category: str | None = Query(None),
    search: str | None = Query(None, description="按名称或标签搜索"),
    db: AsyncSession = Depends(get_db),
) -> SystemImageListResponse:
    stmt = select(SystemImage).order_by(SystemImage.created_at.desc())
    if category:
        stmt = stmt.where(SystemImage.category == category)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            SystemImage.name.ilike(pattern) | SystemImage.tags.ilike(pattern)
        )
    images = (await db.execute(stmt)).scalars().all()
    items = [
        SystemImageResponse(
            id=i.id, category=i.category, name=i.name,
            tags=i.tags,
            original_path=i.original_path, thumbnail_path=i.thumbnail_path,
            created_at=i.created_at.isoformat(),
        ) for i in images
    ]
    return SystemImageListResponse(total=len(items), items=items)


@router.delete("/images/{image_id}", summary="删除系统图片")
async def delete_system_image(
    image_id: int,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    img = await db.get(SystemImage, image_id)
    if img is None:
        raise HTTPException(404, "图片不存在")
    await db.delete(img)
    await db.commit()
    return {"code": 200, "msg": "图片已删除", "data": None}


class NasScanRequest(BaseModel):
    path: str
    category: str = "other"
    tags: str | None = None


class SystemImageBulkUpdateRequest(BaseModel):
    image_ids: list[int]
    category: str | None = None
    tags: str | None = None


@router.patch("/images/bulk-update", summary="批量更新系统图片分类")
async def bulk_update_system_images(
    body: SystemImageBulkUpdateRequest,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    image_ids = sorted(set(body.image_ids))
    if not image_ids:
        raise HTTPException(400, "请选择需要更新的图片")
    if body.category is None and body.tags is None:
        raise HTTPException(400, "请至少提供分类或标签")

    rows = (await db.execute(
        select(SystemImage).where(SystemImage.id.in_(image_ids))
    )).scalars().all()
    if not rows:
        raise HTTPException(404, "未找到可更新的图片")

    for img in rows:
        if body.category is not None:
            img.category = body.category
        if body.tags is not None:
            img.tags = body.tags

    await db.commit()
    return {"code": 200, "msg": f"已更新 {len(rows)} 张素材", "data": {"updated": len(rows)}}


@router.post("/images/scan-nas", summary="NAS扫描导入系统图库")
async def scan_nas_to_system_images(
    body: NasScanRequest,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    scan_dir = (NAS_ROOT / body.path).resolve()
    if not scan_dir.is_relative_to(NAS_ROOT.resolve()):
        raise HTTPException(403, "路径不在 NAS 挂载范围内")
    if not scan_dir.is_dir():
        raise HTTPException(404, f"目录不存在: {body.path}")

    files = [
        f for f in scan_dir.rglob("*")
        if f.is_file() and f.suffix.lower() in IMAGE_SUFFIXES
    ]
    if not files:
        return {"code": 200, "msg": "未找到图片文件", "data": {"uploaded": 0, "failed": 0}}

    raw_dir = SYSTEM_ROOT / "raw"
    thumb_dir = SYSTEM_ROOT / "thumb"
    uploaded = 0
    failed = 0

    for f in files:
        try:
            file_bytes = await run_in_threadpool(f.read_bytes)
            suffix = f.suffix.lower()
            original_path, thumb_path, _ = await run_in_threadpool(
                _save_and_thumbnail, raw_dir, thumb_dir, file_bytes, suffix,
            )
            img = SystemImage(
                category=body.category,
                name=f.name,
                tags=body.tags,
                original_path=str(original_path),
                thumbnail_path=str(thumb_path),
            )
            db.add(img)
            uploaded += 1
        except Exception:
            failed += 1

    if uploaded > 0:
        await db.commit()

    return {"code": 200, "msg": f"已导入 {uploaded} 张图片", "data": {"uploaded": uploaded, "failed": failed}}


# ═══════════════════ 目标名称字典（通用） ═══════════════════

@router.get("/target-dictionary", response_model=DictEntryListResponse, summary="通用目标词条列表")
async def list_target_dictionary(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> DictEntryListResponse:
    rows = (await db.execute(
        select(SystemTargetDictionary).order_by(SystemTargetDictionary.id)
    )).scalars().all()
    items = [
        DictEntryResponse(
            id=r.id, name=r.name, category_type=r.category_type.value,
            is_system=r.is_system, created_at=r.created_at.isoformat(),
        ) for r in rows
    ]
    return DictEntryListResponse(total=len(items), items=items)


@router.post("/target-dictionary", response_model=DictEntryResponse, status_code=201, summary="新增通用词条")
async def create_target_dictionary_entry(
    body: DictEntryCreate,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> DictEntryResponse:
    existing = await db.scalar(
        select(SystemTargetDictionary).where(SystemTargetDictionary.name == body.name)
    )
    if existing:
        raise HTTPException(409, f"词条 '{body.name}' 已存在")
    entry = SystemTargetDictionary(
        name=body.name,
        category_type=CategoryType(body.category_type),
        is_system=False,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    await db.commit()
    return DictEntryResponse(
        id=entry.id, name=entry.name, category_type=entry.category_type.value,
        is_system=entry.is_system, created_at=entry.created_at.isoformat(),
    )


@router.delete("/target-dictionary/{entry_id}", summary="删除通用词条")
async def delete_target_dictionary_entry(
    entry_id: int,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    entry = await db.get(SystemTargetDictionary, entry_id)
    if entry is None:
        raise HTTPException(404, "词条不存在")
    if entry.is_system:
        raise HTTPException(400, "系统内置词条不可删除")
    await db.delete(entry)
    await db.commit()
    return {"code": 200, "msg": "词条已删除", "data": None}


# ═══════════════════ 项目模板 ═══════════════════════════════

@router.get("/templates", response_model=TemplateListResponse, summary="模板列表")
async def list_templates(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TemplateListResponse:
    stmt = select(ProjectTemplate).order_by(ProjectTemplate.is_builtin.desc(), ProjectTemplate.created_at.desc())
    templates = (await db.execute(stmt)).scalars().all()

    tpl_ids = [t.id for t in templates]
    target_counts: dict[int, int] = {}
    if tpl_ids:
        tc_stmt = (
            select(TemplateTarget.template_id, sa_func.count(TemplateTarget.id))
            .where(TemplateTarget.template_id.in_(tpl_ids))
            .group_by(TemplateTarget.template_id)
        )
        target_counts = dict((await db.execute(tc_stmt)).all())

    items = [
        TemplateResponse(
            id=t.id, name=t.name, description=t.description,
            is_builtin=t.is_builtin, target_count=target_counts.get(t.id, 0),
            created_at=t.created_at.isoformat(),
        ) for t in templates
    ]
    return TemplateListResponse(total=len(items), items=items)


@router.post("/templates", response_model=TemplateDetailResponse, status_code=201, summary="创建模板")
async def create_template(
    body: TemplateCreate,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> TemplateDetailResponse:
    tpl = ProjectTemplate(
        name=body.name, description=body.description,
        target_dictionary=[d.model_dump() for d in body.target_dictionary] if body.target_dictionary else [],
    )
    db.add(tpl)
    await db.flush()

    target_items = []
    for i, t in enumerate(body.targets):
        tt = TemplateTarget(
            template_id=tpl.id, name=t.name,
            category_type=CategoryType(t.category_type),
            sample_image_id=t.sample_image_id,
            requirement_desc=t.requirement_desc,
            sort_order=t.sort_order or i,
        )
        db.add(tt)
        await db.flush()
        target_items.append(TemplateTargetResponse(
            id=tt.id, template_id=tpl.id, name=tt.name,
            category_type=tt.category_type.value,
            sample_image_id=tt.sample_image_id,
            requirement_desc=tt.requirement_desc, sort_order=tt.sort_order,
        ))

    await db.commit()
    await db.refresh(tpl)

    return TemplateDetailResponse(
        id=tpl.id, name=tpl.name, description=tpl.description,
        is_builtin=tpl.is_builtin, targets=target_items,
        target_dictionary=tpl.target_dictionary or [],
        created_at=tpl.created_at.isoformat(),
    )


@router.get("/templates/{template_id}", response_model=TemplateDetailResponse, summary="模板详情")
async def get_template(
    template_id: int,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> TemplateDetailResponse:
    tpl = await db.get(ProjectTemplate, template_id)
    if tpl is None:
        raise HTTPException(404, "模板不存在")

    stmt = select(TemplateTarget).where(TemplateTarget.template_id == template_id).order_by(TemplateTarget.sort_order)
    targets = (await db.execute(stmt)).scalars().all()

    img_ids = [t.sample_image_id for t in targets if t.sample_image_id]
    img_thumbs: dict[int, str] = {}
    if img_ids:
        rows = (await db.execute(
            select(SystemImage.id, SystemImage.thumbnail_path).where(SystemImage.id.in_(img_ids))
        )).all()
        img_thumbs = {r[0]: r[1] for r in rows if r[1]}

    items = [
        TemplateTargetResponse(
            id=t.id, template_id=t.template_id, name=t.name,
            category_type=t.category_type.value,
            sample_image_id=t.sample_image_id,
            sample_thumbnail=img_thumbs.get(t.sample_image_id) if t.sample_image_id else None,
            requirement_desc=t.requirement_desc, sort_order=t.sort_order,
        ) for t in targets
    ]
    return TemplateDetailResponse(
        id=tpl.id, name=tpl.name, description=tpl.description,
        is_builtin=tpl.is_builtin, targets=items,
        target_dictionary=tpl.target_dictionary or [],
        created_at=tpl.created_at.isoformat(),
    )


@router.patch("/templates/{template_id}", response_model=TemplateResponse, summary="编辑模板")
async def update_template(
    template_id: int,
    body: TemplateUpdate,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> TemplateResponse:
    tpl = await db.get(ProjectTemplate, template_id)
    if tpl is None:
        raise HTTPException(404, "模板不存在")
    if body.name is not None:
        tpl.name = body.name
    if body.description is not None:
        tpl.description = body.description
    if body.target_dictionary is not None:
        tpl.target_dictionary = [d.model_dump() for d in body.target_dictionary]
    await db.commit()
    await db.refresh(tpl)
    tc = (await db.execute(
        select(sa_func.count(TemplateTarget.id)).where(TemplateTarget.template_id == template_id)
    )).scalar() or 0
    return TemplateResponse(
        id=tpl.id, name=tpl.name, description=tpl.description,
        is_builtin=tpl.is_builtin, target_count=tc,
        created_at=tpl.created_at.isoformat(),
    )


@router.delete("/templates/{template_id}", summary="删除模板")
async def delete_template(
    template_id: int,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    tpl = await db.get(ProjectTemplate, template_id)
    if tpl is None:
        raise HTTPException(404, "模板不存在")
    await db.delete(tpl)
    await db.commit()
    return {"code": 200, "msg": "模板已删除", "data": None}


@router.post("/templates/{template_id}/targets", response_model=TemplateTargetResponse, status_code=201, summary="添加模板目标")
async def add_template_target(
    template_id: int,
    body: TemplateTargetCreate,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> TemplateTargetResponse:
    tpl = await db.get(ProjectTemplate, template_id)
    if tpl is None:
        raise HTTPException(404, "模板不存在")
    tt = TemplateTarget(
        template_id=template_id, name=body.name,
        category_type=CategoryType(body.category_type),
        sample_image_id=body.sample_image_id,
        requirement_desc=body.requirement_desc, sort_order=body.sort_order,
    )
    db.add(tt)
    await db.flush()
    await db.refresh(tt)
    await db.commit()
    return TemplateTargetResponse(
        id=tt.id, template_id=tt.template_id, name=tt.name,
        category_type=tt.category_type.value,
        sample_image_id=tt.sample_image_id,
        requirement_desc=tt.requirement_desc, sort_order=tt.sort_order,
    )


@router.delete("/templates/{template_id}/targets/{target_id}", summary="删除模板目标")
async def delete_template_target(
    template_id: int,
    target_id: int,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    tt = await db.get(TemplateTarget, target_id)
    if tt is None or tt.template_id != template_id:
        raise HTTPException(404, "目标不存在")
    await db.delete(tt)
    await db.commit()
    return {"code": 200, "msg": "目标已删除", "data": None}


# ═══════════════════ 用户管理 ═══════════════════════════════

async def _project_ids_for_user(db: AsyncSession, user_id: int) -> list[int]:
    rows = (await db.execute(
        select(user_project_access.c.project_id).where(user_project_access.c.user_id == user_id)
    )).scalars().all()
    return list(rows)


@router.get("/users", response_model=UserListResponse, summary="用户列表")
async def list_users(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    users = (await db.execute(select(User).order_by(User.id))).scalars().all()
    access_rows = (await db.execute(select(user_project_access))).all()
    access_map: dict[int, list[int]] = {}
    for row in access_rows:
        access_map.setdefault(row._mapping["user_id"], []).append(row._mapping["project_id"])
    items = [
        UserResponse(
            id=u.id, username=u.username, display_name=u.display_name,
            role=u.role.value,
            can_delete_projects=getattr(u, "can_delete_projects", False),
            project_ids=access_map.get(u.id, []),
            is_active=u.is_active,
            created_at=u.created_at.isoformat(),
        ) for u in users
    ]
    return UserListResponse(total=len(items), items=items)


@router.post("/users", response_model=UserResponse, status_code=201, summary="创建用户")
async def create_user(
    body: UserCreate,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    existing = await db.scalar(select(User).where(User.username == body.username))
    if existing:
        raise HTTPException(409, f"用户名 '{body.username}' 已存在")
    user = User(
        username=body.username,
        display_name=body.display_name,
        password_hash=get_password_hash(body.password),
        role=UserRole(body.role),
        can_delete_projects=body.can_delete_projects,
    )
    db.add(user)
    await db.flush()
    for pid in body.project_ids:
        await db.execute(user_project_access.insert().values(user_id=user.id, project_id=pid))
    await db.refresh(user)
    await db.commit()
    return UserResponse(
        id=user.id, username=user.username, display_name=user.display_name,
        role=user.role.value,
        can_delete_projects=getattr(user, "can_delete_projects", False),
        project_ids=body.project_ids,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.patch("/users/{user_id}", response_model=UserResponse, summary="编辑用户")
async def update_user(
    user_id: int,
    body: UserUpdate,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    if body.display_name is not None:
        user.display_name = body.display_name
    if body.password is not None:
        user.password_hash = get_password_hash(body.password)
    if body.role is not None:
        user.role = UserRole(body.role)
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.can_delete_projects is not None:
        user.can_delete_projects = body.can_delete_projects
    if body.project_ids is not None:
        await db.execute(sa_delete(user_project_access).where(user_project_access.c.user_id == user_id))
        for pid in body.project_ids:
            await db.execute(user_project_access.insert().values(user_id=user_id, project_id=pid))
    await db.commit()
    await db.refresh(user)
    return UserResponse(
        id=user.id, username=user.username, display_name=user.display_name,
        role=user.role.value,
        can_delete_projects=getattr(user, "can_delete_projects", False),
        project_ids=await _project_ids_for_user(db, user.id),
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


@router.delete("/users/{user_id}", summary="删除用户")
async def delete_user(
    user_id: int,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    await db.execute(sa_delete(user_project_access).where(user_project_access.c.user_id == user_id))
    await db.delete(user)
    await db.commit()
    return {"code": 200, "msg": "用户已删除", "data": None}


@router.get("/users/{user_id}/access", response_model=UserAccessResponse, summary="获取用户项目权限")
async def get_user_access(
    user_id: int,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> UserAccessResponse:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    rows = (await db.execute(
        select(user_project_access.c.project_id).where(user_project_access.c.user_id == user_id)
    )).scalars().all()
    return UserAccessResponse(user_id=user_id, project_ids=list(rows))


@router.put("/users/{user_id}/access", response_model=UserAccessResponse, summary="设置用户项目权限")
async def set_user_access(
    user_id: int,
    body: UserAccessUpdate,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> UserAccessResponse:
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(404, "用户不存在")
    await db.execute(sa_delete(user_project_access).where(user_project_access.c.user_id == user_id))
    for pid in body.project_ids:
        await db.execute(user_project_access.insert().values(user_id=user_id, project_id=pid))
    await db.commit()
    return UserAccessResponse(user_id=user_id, project_ids=body.project_ids)
