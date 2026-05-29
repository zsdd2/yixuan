"""add review feedback status

Revision ID: f3a9d2c1e4b5
Revises: e2f5a7b8c9d0
Create Date: 2026-05-25 09:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "f3a9d2c1e4b5"
down_revision = "e2f5a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "review_feedbacks",
        sa.Column("feedback_status", sa.String(length=32), nullable=True),
    )
    op.execute(
        """
        UPDATE review_feedbacks
        SET feedback_status = CASE
            WHEN is_confirmed = true THEN 'approved'
            WHEN comment = '弃用' OR comment = '寮冪敤' THEN 'discarded'
            ELSE 'revision'
        END
        """
    )
    op.alter_column(
        "review_feedbacks",
        "feedback_status",
        existing_type=sa.String(length=32),
        nullable=False,
        server_default="revision",
    )


def downgrade() -> None:
    op.drop_column("review_feedbacks", "feedback_status")
