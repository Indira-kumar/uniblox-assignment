"""Reward configuration and generated coupon records."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RewardPolicy(Base):
    __tablename__ = "reward_policy"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_reward_policy_singleton"),
        CheckConstraint("orders_per_coupon > 0", name="ck_reward_policy_interval_positive"),
        CheckConstraint(
            "discount_percent BETWEEN 1 AND 100", name="ck_reward_policy_discount_percent"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    orders_per_coupon: Mapped[int] = mapped_column(Integer, nullable=False)
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False)


class Coupon(Base):
    __tablename__ = "coupons"
    __table_args__ = (
        CheckConstraint("milestone_number > 0", name="ck_coupons_milestone_positive"),
        CheckConstraint("discount_percent BETWEEN 1 AND 100", name="ck_coupons_discount_percent"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    milestone_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    discount_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
