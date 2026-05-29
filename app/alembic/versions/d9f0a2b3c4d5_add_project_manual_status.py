"""add_project_manual_status

Revision ID: d9f0a2b3c4d5
Revises: c8f1b6a4d2e9
Create Date: 2026-05-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "d9f0a2b3c4d5"
down_revision = "c8f1b6a4d2e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("projects")}
    if "is_manual" not in columns:
        op.add_column(
            "projects",
            sa.Column("is_manual", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )


def downgrade() -> None:
    columns = {column["name"] for column in inspect(op.get_bind()).get_columns("projects")}
    if "is_manual" in columns:
        op.drop_column("projects", "is_manual")
