"""Add milestone coupon configuration and single-use redemption.

Revision ID: 0004_rewards
Revises: 0003_orders
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_rewards"
down_revision = "0003_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "reward_policy",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("orders_per_coupon", sa.Integer(), nullable=False),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_reward_policy_singleton"),
        sa.CheckConstraint("orders_per_coupon > 0", name="ck_reward_policy_interval_positive"),
        sa.CheckConstraint(
            "discount_percent BETWEEN 1 AND 100", name="ck_reward_policy_discount_percent"
        ),
    )
    op.create_table(
        "coupons",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(length=32), nullable=False, unique=True),
        sa.Column("milestone_number", sa.Integer(), nullable=False, unique=True),
        sa.Column("discount_percent", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("milestone_number > 0", name="ck_coupons_milestone_positive"),
        sa.CheckConstraint(
            "discount_percent BETWEEN 1 AND 100", name="ck_coupons_discount_percent"
        ),
    )
    op.add_column("orders", sa.Column("coupon_id", sa.Uuid(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_orders_coupon_id_coupons",
        "orders",
        "coupons",
        ["coupon_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint("uq_orders_coupon_id", "orders", ["coupon_id"])


def downgrade() -> None:
    op.drop_constraint("uq_orders_coupon_id", "orders", type_="unique")
    op.drop_constraint("fk_orders_coupon_id_coupons", "orders", type_="foreignkey")
    op.drop_column("orders", "coupon_id")
    op.drop_table("coupons")
    op.drop_table("reward_policy")
