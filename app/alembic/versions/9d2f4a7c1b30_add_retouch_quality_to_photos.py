"""add_retouch_quality_to_photos

Revision ID: 9d2f4a7c1b30
Revises: 8b8a6f9d2c10
Create Date: 2026-05-22 11:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "9d2f4a7c1b30"
down_revision = "8b8a6f9d2c10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("photos", sa.Column("retouch_quality", sa.String(length=32), nullable=True))


def downgrade() -> None:
    op.drop_column("photos", "retouch_quality")
