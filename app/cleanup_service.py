"""
cleanup_service.py —— 回收站物理清理服务

业务规则：
  对于已归档（archived_at 非空）且归档时间超过 RETENTION_DAYS（默认 15 天）
  的项目，将其回收站中的照片（deleted_at IS NOT NULL）执行：
    1. 物理删除磁盘上的原图与缩略图
    2. 从 photos 表中硬删除该行记录

  注意：倒计时基于 Project.archived_at，而不是 Photo.deleted_at。
       未归档的项目永远不会被清理。

可作为独立脚本运行（在容器内）：
    python -m cleanup_service
也可由 /api/v1/system/trigger-cleanup 临时接口同步调用。
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Photo, Project

# 归档保留天数（超过该天数的归档项目会被清理回收站）
RETENTION_DAYS = 15


@dataclass
class CleanupReport:
    scanned_projects: int = 0
    eligible_projects: list[int] = field(default_factory=list)
    files_deleted: int = 0
    files_missing: int = 0
    rows_deleted: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "scanned_projects": self.scanned_projects,
            "eligible_projects": self.eligible_projects,
            "files_deleted": self.files_deleted,
            "files_missing": self.files_missing,
            "rows_deleted": self.rows_deleted,
            "errors": self.errors,
        }


def _delete_file(path_str: str | None, report: CleanupReport) -> None:
    """物理删除单个文件，统计到 report。"""
    if not path_str:
        return
    p = Path(path_str)
    try:
        if p.is_file():
            p.unlink()
            report.files_deleted += 1
        else:
            report.files_missing += 1
    except OSError as exc:
        report.errors.append(f"删除文件失败 {path_str}: {exc}")


async def run_cleanup(session: AsyncSession, retention_days: int = RETENTION_DAYS) -> CleanupReport:
    """
    执行一次清理：
      1. 找到 archived_at <= now - retention_days 的项目
      2. 对每个项目，找出 deleted_at IS NOT NULL 的照片
      3. 物理删除文件 → 硬删除 DB 记录
    返回结构化报告。
    """
    report = CleanupReport()
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

    # 1. 找符合归档条件的项目
    proj_stmt = select(Project).where(
        Project.archived_at.is_not(None),
        Project.archived_at <= cutoff,
    )
    projects = (await session.execute(proj_stmt)).scalars().all()
    report.scanned_projects = len(projects)
    report.eligible_projects = [p.id for p in projects]

    if not projects:
        return report

    project_ids = [p.id for p in projects]

    # 2. 找这些项目里所有已软删除的照片
    photo_stmt = select(Photo).where(
        Photo.project_id.in_(project_ids),
        Photo.deleted_at.is_not(None),
    )
    trash_photos = (await session.execute(photo_stmt)).scalars().all()

    # 3. 物理删除文件 + 硬删除行
    for photo in trash_photos:
        _delete_file(photo.original_path, report)
        _delete_file(photo.thumbnail_path, report)
        await session.delete(photo)
        report.rows_deleted += 1

    await session.commit()
    return report


async def main() -> None:
    """脚本入口：使用独立 session 执行一次清理。"""
    async with AsyncSessionLocal() as session:
        report = await run_cleanup(session)
    print("=" * 50)
    print("[CLEANUP REPORT]")
    for k, v in report.to_dict().items():
        print(f"  {k}: {v}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
