"""update billing rule uniqueness to production name

Revision ID: 0c4d5e6f7a8b
Revises: 7e8f9a0b1c2d
Create Date: 2026-05-30
"""
from alembic import op


revision = "0c4d5e6f7a8b"
down_revision = "7e8f9a0b1c2d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    op.execute(
        """
        UPDATE billing_price_rules
        SET production_name = CASE
            WHEN base_category_type = 'white' THEN '默认白图'
            WHEN base_category_type = 'scene' THEN '默认场景图'
            ELSE production_name
        END
        WHERE production_name = '默认制作'
        """
    )

    if dialect == "postgresql":
        op.execute(
            """
            WITH ranked AS (
                SELECT id,
                       production_name,
                       ROW_NUMBER() OVER (
                           PARTITION BY client_id, production_name
                           ORDER BY id
                       ) AS rn
                FROM billing_price_rules
            )
            UPDATE billing_price_rules AS b
            SET production_name = ranked.production_name || '-' || ranked.rn
            FROM ranked
            WHERE b.id = ranked.id AND ranked.rn > 1
            """
        )
        op.drop_constraint("uq_billing_price_client_production", "billing_price_rules", type_="unique")
        op.create_unique_constraint(
            "uq_billing_price_client_production_name",
            "billing_price_rules",
            ["client_id", "production_name"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("uq_billing_price_client_production_name", "billing_price_rules", type_="unique")
        op.create_unique_constraint(
            "uq_billing_price_client_production",
            "billing_price_rules",
            ["client_id", "base_category_type", "production_type"],
        )
