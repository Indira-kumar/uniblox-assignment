"""Store immutable orders and their purchased lines.

Revision ID: 0003_orders
Revises: 0002_carts
"""

import sqlalchemy as sa
from alembic import op

revision = "0003_orders"
down_revision = "0002_carts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column(
            "cart_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("carts.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("gross_cents", sa.BigInteger(), nullable=False),
        sa.Column("discount_cents", sa.BigInteger(), nullable=False),
        sa.Column("net_cents", sa.BigInteger(), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("gross_cents >= 0", name="ck_orders_gross_nonnegative"),
        sa.CheckConstraint("discount_cents >= 0", name="ck_orders_discount_nonnegative"),
        sa.CheckConstraint("net_cents >= 0", name="ck_orders_net_nonnegative"),
        sa.CheckConstraint(
            "gross_cents = discount_cents + net_cents", name="ck_orders_total_reconciles"
        ),
    )
    op.create_table(
        "order_lines",
        sa.Column(
            "order_id",
            sa.Uuid(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("product_id", sa.Integer(), primary_key=True),
        sa.Column("product_name", sa.String(length=120), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_cents", sa.BigInteger(), nullable=False),
        sa.Column("line_total_cents", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_lines_quantity_positive"),
        sa.CheckConstraint("unit_price_cents >= 0", name="ck_order_lines_price_nonnegative"),
        sa.CheckConstraint("line_total_cents >= 0", name="ck_order_lines_total_nonnegative"),
        sa.CheckConstraint(
            "line_total_cents = quantity * unit_price_cents", name="ck_order_lines_total_reconciles"
        ),
    )


def downgrade() -> None:
    op.drop_table("order_lines")
    op.drop_table("orders")
