"""add project customer product code

Revision ID: 4d9e0f1a2b3c
Revises: 3c8d9e0f1a2b
Create Date: 2026-05-31 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "4d9e0f1a2b3c"
down_revision: Union[str, None] = "3c8d9e0f1a2b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "projects",
        sa.Column("customer_product_code", sa.String(length=128), nullable=True),
    )
    op.create_index(
        "ix_projects_customer_product_code",
        "projects",
        ["customer_product_code"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_projects_customer_product_code", table_name="projects")
    op.drop_column("projects", "customer_product_code")
