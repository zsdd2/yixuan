"""add project groups

Revision ID: e2f5a7b8c9d0
Revises: d9f0a2b3c4d5
Create Date: 2026-05-24 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e2f5a7b8c9d0"
down_revision: Union[str, None] = "d9f0a2b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_groups",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_project_groups_project_id"), "project_groups", ["project_id"], unique=False)
    op.create_index(op.f("ix_project_groups_deleted_at"), "project_groups", ["deleted_at"], unique=False)

    op.add_column("project_targets", sa.Column("group_id", sa.BigInteger(), nullable=True))
    op.create_index(op.f("ix_project_targets_group_id"), "project_targets", ["group_id"], unique=False)
    op.create_foreign_key(
        "fk_project_targets_group_id_project_groups",
        "project_targets",
        "project_groups",
        ["group_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint("uq_project_target_name", "project_targets", type_="unique")
    op.create_unique_constraint(
        "uq_project_target_group_name",
        "project_targets",
        ["project_id", "group_id", "name"],
    )

    op.add_column("photos", sa.Column("group_id", sa.BigInteger(), nullable=True))
    op.create_index(op.f("ix_photos_group_id"), "photos", ["group_id"], unique=False)
    op.create_foreign_key(
        "fk_photos_group_id_project_groups",
        "photos",
        "project_groups",
        ["group_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_photos_group_id_project_groups", "photos", type_="foreignkey")
    op.drop_index(op.f("ix_photos_group_id"), table_name="photos")
    op.drop_column("photos", "group_id")

    op.drop_constraint("uq_project_target_group_name", "project_targets", type_="unique")
    op.create_unique_constraint("uq_project_target_name", "project_targets", ["project_id", "name"])
    op.drop_constraint("fk_project_targets_group_id_project_groups", "project_targets", type_="foreignkey")
    op.drop_index(op.f("ix_project_targets_group_id"), table_name="project_targets")
    op.drop_column("project_targets", "group_id")

    op.drop_index(op.f("ix_project_groups_deleted_at"), table_name="project_groups")
    op.drop_index(op.f("ix_project_groups_project_id"), table_name="project_groups")
    op.drop_table("project_groups")
