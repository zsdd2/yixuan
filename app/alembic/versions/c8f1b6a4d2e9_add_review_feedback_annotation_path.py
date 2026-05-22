"""add_review_feedback_annotation_path

Revision ID: c8f1b6a4d2e9
Revises: b7e2c9d4a1f0
Create Date: 2026-05-22 17:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "c8f1b6a4d2e9"
down_revision = "b7e2c9d4a1f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("review_feedbacks")}
    if "annotation_path" not in columns:
        op.add_column("review_feedbacks", sa.Column("annotation_path", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("review_feedbacks", "annotation_path")
