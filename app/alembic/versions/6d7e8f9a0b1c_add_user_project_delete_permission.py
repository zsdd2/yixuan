"""add user project delete permission

Revision ID: 6d7e8f9a0b1c
Revises: 4f6e9a0b1c2d
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "6d7e8f9a0b1c"
down_revision = "4f6e9a0b1c2d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("can_delete_projects", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute(
        """
        UPDATE users
        SET can_delete_projects = true
        WHERE role IN ('super_admin', 'admin')
        """
    )


def downgrade() -> None:
    op.drop_column("users", "can_delete_projects")
