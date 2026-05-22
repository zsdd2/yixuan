"""
init_db.py —— 数据库种子数据初始化

注意：
- 数据库表由 Alembic 迁移创建，不在此处执行 create_all()
- 种子数据分为两部分：
  1. 字典数据（seed_target_dictionary）：在 entrypoint.sh 中执行
  2. 管理员和模板（seed_admin_user, seed_builtin_templates）：在 main.py lifespan 中执行
- 本文件提供独立的种子数据函数供其他模块导入使用
"""
import asyncio
import sys

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from app.database import engine, AsyncSessionLocal
from app import models  # 用于访问 models.User, models.UserRole 等


async def seed_admin_user() -> None:
    print("[init] seeding admin user...")
    async with AsyncSessionLocal() as session:
        # 幂等检查：已存在则跳过
        result = await session.execute(
            select(models.User).where(models.User.id == 1)
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"   user id=1 ({existing.username}) exists, skip.")
            return

        admin = models.User(
            id=1,
            username="Admin",
            role=models.UserRole.staff,
            is_active=True,
        )
        session.add(admin)
        try:
            await session.commit()
            print("   admin user (id=1) inserted.")
        except IntegrityError:
            await session.rollback()
            print("   conflict, user exists, rolled back.")


async def seed_builtin_templates() -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(models.ProjectTemplate).where(models.ProjectTemplate.is_builtin == True)
        )
        if existing:
            return

        PRESETS = [
            ("家具类", [
                ("白底正面", "white", 0), ("白底侧面", "white", 1),
                ("白底细节", "white", 2), ("场景搭配", "scene", 3),
            ]),
            ("服装类", [
                ("白底全身正面", "white", 0), ("白底全身背面", "white", 1),
                ("白底细节", "white", 2), ("场景街拍", "scene", 3), ("场景室内", "scene", 4),
            ]),
            ("食品类", [
                ("白底主体", "white", 0), ("白底组合", "white", 1),
                ("场景桌面", "scene", 2), ("场景手持", "scene", 3),
            ]),
        ]
        for tpl_name, targets in PRESETS:
            tpl = models.ProjectTemplate(name=tpl_name, is_builtin=True)
            session.add(tpl)
            await session.flush()
            for t_name, t_cat, t_order in targets:
                session.add(models.TemplateTarget(
                    template_id=tpl.id, name=t_name,
                    category_type=models.CategoryType(t_cat), sort_order=t_order,
                ))
        await session.commit()


async def seed_target_dictionary() -> None:
    async with AsyncSessionLocal() as session:
        existing = await session.scalar(
            select(models.SystemTargetDictionary).limit(1)
        )
        if existing:
            return

        ENTRIES = [
            ("正面全景", "white"), ("背面全景", "white"),
            ("侧面半身", "white"), ("45度视角", "white"),
            ("产品特写", "white"), ("材质细节", "white"),
            ("白底组合", "white"), ("场景搭配", "scene"),
            ("场景氛围", "scene"), ("街拍场景", "scene"),
            ("室内场景", "scene"), ("手持展示", "scene"),
        ]
        for name, cat in ENTRIES:
            session.add(models.SystemTargetDictionary(
                name=name,
                category_type=models.CategoryType(cat),
                is_system=True,
            ))
        await session.commit()


async def main() -> None:
    """手动执行所有种子数据初始化（仅用于开发/测试）。

    注意：生产环境中，种子数据通过 entrypoint.sh 和 main.py lifespan 自动执行。
    """
    try:
        print("[init] Starting seed data initialization...")
        await seed_admin_user()
        await seed_builtin_templates()
        await seed_target_dictionary()
        print("\n[init] Seed data initialization complete.")
    except Exception as exc:
        print(f"\n[init] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
