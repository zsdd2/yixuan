"""add project tag scope

Revision ID: 1a2b3c4d5e6f
Revises: 0c4d5e6f7a8b
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa


revision = "1a2b3c4d5e6f"
down_revision = "0c4d5e6f7a8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "project_tags",
        sa.Column(
            "scope",
            sa.String(length=20),
            nullable=False,
            server_default="project",
            comment="project=项目临时标签，system=从通用标签同步到项目内使用",
        ),
    )
    op.create_index("ix_project_tags_scope", "project_tags", ["scope"])


def downgrade() -> None:
    op.drop_index("ix_project_tags_scope", table_name="project_tags")
    op.drop_column("project_tags", "scope")
