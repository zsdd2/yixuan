"""
logic/status_manager.py —— 项目状态自动计算与目标状态管理逻辑封装

核心职责：
1. compute_project_status() - 根据照片 process_state 自动计算项目状态
2. compute_target_status() - 根据照片数量自动计算目标状态
3. should_skip_auto_compute() - 判断是否跳过自动计算（手动设置优先）
"""
from sqlalchemy import select, func as sa_func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Photo, PhotoStatus, ProcessState, Project, ProjectStatus, ProjectTarget, TargetStatus


async def compute_project_status(db: AsyncSession, project_id: int) -> None:
    """
    根据照片 process_state 自动计算并更新项目状态（completed 仅手动设置）。

    状态优先级：手动设置 > 自动计算
    一旦手动设置过 project_status 为 completed，此函数会跳过自动计算。

    计算规则：
    - 无任何照片 → not_started
    - 仅有 raw 照片 → shooting
    - 有 retouched 或 final 照片 → retouching
    - completed 状态仅可手动设置
    """
    project = await db.get(Project, project_id)
    if project is None or project.project_status == ProjectStatus.completed:
        return

    counts = dict(
        (await db.execute(
            select(Photo.process_state, sa_func.count(Photo.id))
            .where(Photo.project_id == project_id, Photo.status != PhotoStatus.deleted)
            .group_by(Photo.process_state)
        )).all()
    )
    total = sum(counts.values())
    retouched = counts.get(ProcessState.retouched, 0)
    final = counts.get(ProcessState.final, 0)

    if total == 0:
        new_status = ProjectStatus.not_started
    elif retouched > 0 or final > 0:
        new_status = ProjectStatus.retouching
    else:
        new_status = ProjectStatus.shooting

    if project.project_status != new_status:
        project.project_status = new_status


async def compute_target_status(db: AsyncSession, target_id: int) -> None:
    """
    根据目标下照片数量自动计算目标状态（client_review 和 completed 仅手动设置）。

    状态优先级：手动设置 (is_manual=True) > 自动计算

    计算规则：
    - 无任何照片 → not_started
    - 仅有 raw 照片 → shooting
    - 有 retouched 或 final 照片 → retouching
    - client_review 和 completed 状态仅可手动设置
    """
    target = await db.get(ProjectTarget, target_id)
    if target is None or target.is_manual:
        return

    counts = dict(
        (await db.execute(
            select(Photo.process_state, sa_func.count(Photo.id))
            .where(Photo.target_id == target_id, Photo.status != PhotoStatus.deleted)
            .group_by(Photo.process_state)
        )).all()
    )
    total = sum(counts.values())
    retouched = counts.get(ProcessState.retouched, 0)
    final = counts.get(ProcessState.final, 0)

    if total == 0:
        new_status = TargetStatus.not_started
    elif retouched > 0 or final > 0:
        new_status = TargetStatus.retouching
    else:
        new_status = TargetStatus.shooting

    if target.target_status != new_status:
        target.target_status = new_status


def should_skip_auto_compute_project(project: Project) -> bool:
    """
    判断项目是否应跳过自动状态计算。

    跳过条件：
    - 项目状态为 completed（手动设置）
    """
    return project.project_status == ProjectStatus.completed


def should_skip_auto_compute_target(target: ProjectTarget) -> bool:
    """
    判断目标是否应跳过自动状态计算。

    跳过条件：
    - is_manual 为 True（手动设置过状态）
    - target_status 为 client_review 或 completed（仅手动设置）
    """
    return target.is_manual or target.target_status in (
        TargetStatus.client_review,
        TargetStatus.completed,
    )
