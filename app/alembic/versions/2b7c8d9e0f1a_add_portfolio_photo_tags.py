"""add portfolio photo tags

Revision ID: 2b7c8d9e0f1a
Revises: 1a2b3c4d5e6f
Create Date: 2026-05-31
"""
from alembic import op
import sqlalchemy as sa


revision = "2b7c8d9e0f1a"
down_revision = "1a2b3c4d5e6f"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_photo_tags",
        sa.Column("photo_id", sa.BigInteger(), nullable=False),
        sa.Column("tag_id", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["system_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("photo_id", "tag_id"),
    )
    op.create_index("ix_portfolio_photo_tags_photo_id", "portfolio_photo_tags", ["photo_id"])
    op.create_index("ix_portfolio_photo_tags_tag_id", "portfolio_photo_tags", ["tag_id"])


def downgrade() -> None:
    op.drop_index("ix_portfolio_photo_tags_tag_id", table_name="portfolio_photo_tags")
    op.drop_index("ix_portfolio_photo_tags_photo_id", table_name="portfolio_photo_tags")
    op.drop_table("portfolio_photo_tags")
