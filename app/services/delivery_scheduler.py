"""
交付 ZIP 定时任务调度器

使用 APScheduler 每天凌晨 2 点批量生成已完成项目的交付 ZIP
"""
from datetime import datetime, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal
from app.models import Project, ProjectStatus
from app.services.delivery_zip_service import generate_delivery_zip


# 创建调度器实例
scheduler = AsyncIOScheduler()


async def nightly_zip_generation():
    """
    每天凌晨 2 点执行的定时任务

    逻辑：
    1. 查询所有 project_status = 'completed'
       AND (zip_status = 'pending' OR zip_status = 'failed')
    2. 逐个调用 generate_delivery_zip()
    3. 记录成功/失败统计
    """
    print(f"[{datetime.now(timezone.utc)}] 开始执行交付 ZIP 生成任务...")

    success_count = 0
    failed_count = 0
    skipped_count = 0

    async with AsyncSessionLocal() as db:
        try:
            # 查询待处理项目
            stmt = select(Project).where(
                Project.project_status == ProjectStatus.completed,
                Project.zip_status.in_(["pending", "failed"])
            )
            result = await db.execute(stmt)
            projects = result.scalars().all()

            print(f"找到 {len(projects)} 个待处理项目")

            for project in projects:
                print(f"处理项目 #{project.id} ({project.name})...")

                # 更新状态为 processing
                project.zip_status = "processing"
                await db.commit()

                # 生成 ZIP
                result = await generate_delivery_zip(project.id, db)

                if result["success"]:
                    success_count += 1
                    print(f"  ✓ 成功生成 ZIP: {result['zip_path']}")
                else:
                    failed_count += 1
                    print(f"  ✗ 失败: {result['error']}")

        except Exception as exc:
            print(f"任务执行异常: {exc}")
            failed_count += 1

    print(f"[{datetime.now(timezone.utc)}] 任务完成 - 成功: {success_count}, 失败: {failed_count}, 跳过: {skipped_count}")


def start_scheduler():
    """
    启动调度器（在 FastAPI 启动时调用）
    """
    # 注册定时任务：每天凌晨 2 点执行
    scheduler.add_job(
        nightly_zip_generation,
        trigger=CronTrigger(hour=2, minute=0),
        id="nightly_zip_generation",
        name="每日交付 ZIP 生成",
        replace_existing=True
    )

    scheduler.start()
    print("交付 ZIP 调度器已启动（每天凌晨 2:00 执行）")


def stop_scheduler():
    """
    停止调度器（在 FastAPI 关闭时调用）
    """
    if scheduler.running:
        scheduler.shutdown()
        print("交付 ZIP 调度器已停止")


# 手动触发任务（用于测试）
async def trigger_manual_generation():
    """
    手动触发 ZIP 生成任务（用于开发测试）
    """
    await nightly_zip_generation()
