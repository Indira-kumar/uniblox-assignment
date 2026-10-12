"""Create the product catalog.

Revision ID: 0001_catalog
Revises:
"""

import sqlalchemy as sa
from alembic import op

revision = "0001_catalog"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("price_cents", sa.BigInteger(), nullable=False),
        sa.Column("stock_quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("price_cents >= 0", name="ck_products_price_nonnegative"),
        sa.CheckConstraint("stock_quantity >= 0", name="ck_products_stock_nonnegative"),
    )


def downgrade() -> None:
    op.drop_table("products")
