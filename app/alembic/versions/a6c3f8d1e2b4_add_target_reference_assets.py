"""add_target_reference_assets

Revision ID: a6c3f8d1e2b4
Revises: 9d2f4a7c1b30
Create Date: 2026-05-22 12:05:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "a6c3f8d1e2b4"
down_revision = "9d2f4a7c1b30"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if inspect(op.get_bind()).has_table("target_reference_assets"):
        return

    op.create_table(
        "target_reference_assets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("target_id", sa.BigInteger(), nullable=False),
        sa.Column("asset_type", sa.String(length=32), nullable=False),
        sa.Column("photo_id", sa.BigInteger(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["project_targets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_target_reference_assets_target_id", "target_reference_assets", ["target_id"])
    op.create_index("ix_target_reference_assets_asset_type", "target_reference_assets", ["asset_type"])


def downgrade() -> None:
    op.drop_index("ix_target_reference_assets_asset_type", table_name="target_reference_assets")
    op.drop_index("ix_target_reference_assets_target_id", table_name="target_reference_assets")
    op.drop_table("target_reference_assets")
