"""
migrate_paths.py — 一次性迁移：将 photos 和 system_images 表中的绝对路径转为 NAS 相对路径。
运行方式：cd app && python migrate_paths.py
"""
import asyncio
import os
from pathlib import Path, PureWindowsPath, PurePosixPath

from sqlalchemy import text

from database import AsyncSessionLocal

NAS_ROOT = Path(os.environ.get("NAS_MOUNT_PATH", "/mnt/nas_data")).resolve()


def to_relative(abs_path: str | None) -> str | None:
    if not abs_path:
        return abs_path
    normalized = abs_path.replace("\\", "/")
    p = Path(normalized)
    if not p.is_absolute():
        return abs_path
    try:
        resolved = p.resolve() if p.exists() else p
        rel = resolved.relative_to(NAS_ROOT)
        return str(PurePosixPath(rel))
    except (ValueError, OSError):
        nas_str = str(NAS_ROOT).replace("\\", "/")
        norm = normalized
        if norm.startswith(nas_str):
            return norm[len(nas_str):].lstrip("/")
        if "mnt/nas_data/" in norm:
            idx = norm.index("mnt/nas_data/") + len("mnt/nas_data/")
            return norm[idx:]
        return abs_path


async def migrate():
    async with AsyncSessionLocal() as db:
        photos = (await db.execute(text("SELECT id, original_path, thumbnail_path FROM photos"))).fetchall()
        updated = 0
        for row in photos:
            pid, orig, thumb = row
            new_orig = to_relative(orig)
            new_thumb = to_relative(thumb)
            if new_orig != orig or new_thumb != thumb:
                await db.execute(
                    text("UPDATE photos SET original_path = :o, thumbnail_path = :t WHERE id = :id"),
                    {"o": new_orig, "t": new_thumb, "id": pid},
                )
                updated += 1
        print(f"[photos] Updated {updated}/{len(photos)} rows")

        images = (await db.execute(text("SELECT id, original_path, thumbnail_path FROM system_images"))).fetchall()
        img_updated = 0
        for row in images:
            sid, orig, thumb = row
            new_orig = to_relative(orig)
            new_thumb = to_relative(thumb)
            if new_orig != orig or new_thumb != thumb:
                await db.execute(
                    text("UPDATE system_images SET original_path = :o, thumbnail_path = :t WHERE id = :id"),
                    {"o": new_orig, "t": new_thumb, "id": sid},
                )
                img_updated += 1
        print(f"[system_images] Updated {img_updated}/{len(images)} rows")

        # Also migrate project cover_image
        projects = (await db.execute(text("SELECT id, cover_image FROM projects WHERE cover_image IS NOT NULL"))).fetchall()
        proj_updated = 0
        for row in projects:
            proj_id, cover = row
            new_cover = to_relative(cover)
            if new_cover != cover:
                await db.execute(
                    text("UPDATE projects SET cover_image = :c WHERE id = :id"),
                    {"c": new_cover, "id": proj_id},
                )
                proj_updated += 1
        print(f"[projects.cover_image] Updated {proj_updated}/{len(projects)} rows")

        await db.commit()
        print("[OK] Migration complete")


if __name__ == "__main__":
    asyncio.run(migrate())
