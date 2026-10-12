"""Create carts and cart items.

Revision ID: 0002_carts
Revises: 0001_catalog
"""

import sqlalchemy as sa
from alembic import op

revision = "0002_carts"
down_revision = "0001_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "carts",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.CheckConstraint("status IN ('OPEN', 'CHECKED_OUT')", name="ck_carts_status"),
        sa.CheckConstraint("version >= 1", name="ck_carts_version_positive"),
    )
    op.create_table(
        "cart_items",
        sa.Column(
            "cart_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("carts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_cart_items_quantity_positive"),
    )


def downgrade() -> None:
    op.drop_table("cart_items")
    op.drop_table("carts")
