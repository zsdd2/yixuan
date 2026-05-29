"""add project billing

Revision ID: 7e8f9a0b1c2d
Revises: 6d7e8f9a0b1c
Create Date: 2026-05-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7e8f9a0b1c2d"
down_revision: Union[str, None] = "6d7e8f9a0b1c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_price_rules",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("client_id", sa.BigInteger(), nullable=False),
        sa.Column("base_category_type", sa.String(length=32), nullable=False),
        sa.Column("production_type", sa.String(length=32), nullable=False),
        sa.Column("production_name", sa.String(length=64), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_id", "base_category_type", "production_type", name="uq_billing_price_client_production"),
    )
    op.create_index("ix_billing_price_rules_client_id", "billing_price_rules", ["client_id"])

    op.create_table(
        "project_billing_summaries",
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("subtotal_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("adjustment_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("total_amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("billing_status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_by", sa.BigInteger(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["paid_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id"),
    )

    op.create_table(
        "project_billing_items",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.BigInteger(), nullable=False),
        sa.Column("photo_id", sa.BigInteger(), nullable=True),
        sa.Column("target_id", sa.BigInteger(), nullable=True),
        sa.Column("base_category_type", sa.String(length=32), nullable=False),
        sa.Column("production_type", sa.String(length=32), nullable=False),
        sa.Column("production_name", sa.String(length=64), nullable=False),
        sa.Column("quantity", sa.Numeric(10, 2), server_default="1", nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), server_default="0", nullable=False),
        sa.Column("source", sa.String(length=20), server_default="manual", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_excluded", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["photo_id"], ["photos.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["project_targets.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "photo_id", name="uq_project_billing_item_photo"),
    )
    op.create_index("ix_project_billing_items_project_id", "project_billing_items", ["project_id"])
    op.create_index("ix_project_billing_items_photo_id", "project_billing_items", ["photo_id"])


def downgrade() -> None:
    op.drop_index("ix_project_billing_items_photo_id", table_name="project_billing_items")
    op.drop_index("ix_project_billing_items_project_id", table_name="project_billing_items")
    op.drop_table("project_billing_items")
    op.drop_table("project_billing_summaries")
    op.drop_index("ix_billing_price_rules_client_id", table_name="billing_price_rules")
    op.drop_table("billing_price_rules")
