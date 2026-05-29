"""add_retouch_batch_id_to_photos

Revision ID: b7e2c9d4a1f0
Revises: a6c3f8d1e2b4
Create Date: 2026-05-22 16:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "b7e2c9d4a1f0"
down_revision = "a6c3f8d1e2b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("photos", sa.Column("retouch_batch_id", sa.String(length=64), nullable=True))
    op.create_index("ix_photos_retouch_batch_id", "photos", ["retouch_batch_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_photos_retouch_batch_id", table_name="photos")
    op.drop_column("photos", "retouch_batch_id")
