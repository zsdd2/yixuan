"""add_client_review_project_status

Revision ID: 8b8a6f9d2c10
Revises: 27480d37fafe
Create Date: 2026-05-21 21:05:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '8b8a6f9d2c10'
down_revision = '27480d37fafe'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE project_status ADD VALUE IF NOT EXISTS 'client_review'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be safely removed without rebuilding the type.
    pass
