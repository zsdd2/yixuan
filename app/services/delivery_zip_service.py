"""
交付 ZIP 打包服务

负责生成项目交付 ZIP 文件、标记脏数据、删除旧文件
"""
import io
import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, Photo, ProjectTarget, SystemConfig, ProcessState, CategoryType


# 环境变量
NAS_ROOT = Path(os.getenv("NAS_MOUNT_PATH", "/mnt/nas_data"))
STORAGE_ROOT = Path("storage/deliveries")


async def generate_delivery_zip(project_id: int, db: AsyncSession) -> dict:
    """
    生成项目交付 ZIP 文件

    返回: {"success": bool, "zip_path": str | None, "error": str | None}
    """
    try:
        # 1. 查询项目信息
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            return {"success": False, "zip_path": None, "error": "项目不存在"}

        # 2. 查询工作室名称配置
        config_stmt = select(SystemConfig).where(SystemConfig.config_key == "studio_name")
        config_result = await db.execute(config_stmt)
        config = config_result.scalar_one_or_none()
        studio_name = config.config_value if config and config.config_value else "工作室"

        # 3. 查询所有 final 照片
        photos_stmt = (
            select(Photo, ProjectTarget)
            .outerjoin(ProjectTarget, Photo.target_id == ProjectTarget.id)
            .where(
                Photo.project_id == project_id,
                Photo.process_state == ProcessState.final,
                Photo.deleted_at.is_(None)
            )
            .order_by(ProjectTarget.category_type, ProjectTarget.name, Photo.display_id)
        )
        photos_result = await db.execute(photos_stmt)
        photos_with_targets = photos_result.all()

        if not photos_with_targets:
            return {"success": False, "zip_path": None, "error": "项目无最终交付图"}

        # 4. 创建 ZIP 文件
        # 确保 deliveries 目录存在
        STORAGE_ROOT.mkdir(parents=True, exist_ok=True)

        # ZIP 文件名：{studio_name}_{project_name}_{YYYYMMDD}.zip
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        safe_project_name = project.name.replace('/', '_').replace('\\', '_').replace('..', '_')
        zip_filename = f"{studio_name}_{safe_project_name}_{date_str}.zip"
        zip_path = STORAGE_ROOT / zip_filename

        # 删除旧文件（如果存在）
        if zip_path.exists():
            zip_path.unlink()

        # 创建 ZIP
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 按分类统计
            white_counter = {}
            scene_counter = {}

            for photo, target in photos_with_targets:
                # 获取原图路径
                original_path = NAS_ROOT / photo.original_path

                # 路径安全校验
                if not original_path.resolve().is_relative_to(NAS_ROOT.resolve()):
                    continue

                if not original_path.is_file():
                    continue

                # 确定分类和目标名称
                if target:
                    category_label = "白图" if target.category_type == CategoryType.white else "场景图"
                    target_name = target.name
                    counter = white_counter if target.category_type == CategoryType.white else scene_counter
                else:
                    category_label = "未分类"
                    target_name = "其他"
                    counter = {}

                # 计数器
                key = target_name
                counter[key] = counter.get(key, 0) + 1
                idx = counter[key]

                # 文件扩展名
                suffix = original_path.suffix

                # 清理 target_name 特殊字符
                safe_target_name = target_name.replace('/', '_').replace('\\', '_').replace('..', '_')

                # ZIP 内路径：{分类}/{目标名称}{序号}.jpg
                zip_path_in_archive = f"{category_label}/{safe_target_name}{idx:02d}{suffix}"

                # 添加到 ZIP
                zf.write(original_path, zip_path_in_archive)

        # 5. 更新项目状态
        project.zip_path = str(zip_path.relative_to(Path("storage")))  # 存储相对路径
        project.zip_status = "completed"
        project.zip_generated_at = datetime.now(timezone.utc)

        await db.commit()

        return {
            "success": True,
            "zip_path": project.zip_path,
            "error": None
        }

    except Exception as exc:
        await db.rollback()
        # 更新失败状态
        try:
            stmt = select(Project).where(Project.id == project_id)
            result = await db.execute(stmt)
            project = result.scalar_one_or_none()
            if project:
                project.zip_status = "failed"
                await db.commit()
        except:
            pass

        return {
            "success": False,
            "zip_path": None,
            "error": f"ZIP 生成失败：{str(exc)}"
        }


async def mark_zip_dirty(project_id: int, db: AsyncSession):
    """
    标记 ZIP 为脏数据

    逻辑：
    1. 查询 project.zip_path
    2. 如果 zip_path 存在，物理删除文件
    3. 设置 zip_status = 'pending'
    4. 清空 zip_path 和 zip_generated_at
    """
    try:
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            return

        # 删除旧 ZIP 文件
        if project.zip_path:
            old_zip_path = Path("storage") / project.zip_path
            if old_zip_path.exists():
                try:
                    old_zip_path.unlink()
                except OSError:
                    pass  # 文件删除失败不影响状态更新

        # 更新状态
        project.zip_status = "pending"
        project.zip_path = None
        project.zip_generated_at = None

        await db.commit()

    except Exception:
        await db.rollback()


async def delete_old_zip(project_id: int, db: AsyncSession):
    """
    删除项目的 ZIP 文件（用于项目删除时清理）
    """
    try:
        stmt = select(Project).where(Project.id == project_id)
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project or not project.zip_path:
            return

        zip_path = Path("storage") / project.zip_path
        if zip_path.exists():
            try:
                zip_path.unlink()
            except OSError:
                pass

    except Exception:
        pass
