"""add review session stage

Revision ID: 4f6e9a0b1c2d
Revises: f3a9d2c1e4b5
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "4f6e9a0b1c2d"
down_revision = "f3a9d2c1e4b5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "review_sessions",
        sa.Column("review_stage", sa.String(length=32), nullable=False, server_default="raw"),
    )
    op.execute(
        """
        UPDATE review_sessions
        SET review_stage = CASE
            WHEN selected_photos->>'review_stage' IN ('raw', 'retouched', 'final')
            THEN selected_photos->>'review_stage'
            ELSE 'raw'
        END
        """
    )
    op.create_index(
        "ix_review_sessions_project_stage",
        "review_sessions",
        ["project_id", "review_stage"],
    )


def downgrade() -> None:
    op.drop_index("ix_review_sessions_project_stage", table_name="review_sessions")
    op.drop_column("review_sessions", "review_stage")
