"""add system tag taxonomy

Revision ID: 3c8d9e0f1a2b
Revises: 2b7c8d9e0f1a
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa


revision = "3c8d9e0f1a2b"
down_revision = "2b7c8d9e0f1a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "system_tags",
        sa.Column("tag_type", sa.String(length=32), nullable=False, server_default="general"),
    )
    op.add_column(
        "system_tags",
        sa.Column("category", sa.String(length=64), nullable=True),
    )
    op.create_index("ix_system_tags_tag_type", "system_tags", ["tag_type"])
    op.create_index("ix_system_tags_category", "system_tags", ["category"])
    op.execute(
        """
        UPDATE system_tags
        SET tag_type = 'portfolio'
        WHERE id IN (SELECT DISTINCT tag_id FROM portfolio_photo_tags)
        """
    )


def downgrade() -> None:
    op.drop_index("ix_system_tags_category", table_name="system_tags")
    op.drop_index("ix_system_tags_tag_type", table_name="system_tags")
    op.drop_column("system_tags", "category")
    op.drop_column("system_tags", "tag_type")
