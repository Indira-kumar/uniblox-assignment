"""Coupon queries using caller-owned transactions."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.orders.models import Order
from app.rewards.models import Coupon, RewardPolicy


def get_policy(session: Session, *, for_update: bool = False) -> RewardPolicy | None:
    statement = select(RewardPolicy).where(RewardPolicy.id == 1)
    if for_update:
        statement = statement.with_for_update()
    return session.scalar(statement)


def placed_order_count(session: Session) -> int:
    return session.scalar(select(func.count(Order.id))) or 0


def next_milestone_number(session: Session) -> int:
    return (session.scalar(select(func.max(Coupon.milestone_number))) or 0) + 1


def get_coupon_by_code(session: Session, code: str, *, for_update: bool = False) -> Coupon | None:
    statement = select(Coupon).where(Coupon.code == code)
    if for_update:
        statement = statement.with_for_update()
    return session.scalar(statement)


def get_coupon(session: Session, coupon_id: object) -> Coupon | None:
    return session.get(Coupon, coupon_id)


def is_redeemed(session: Session, coupon_id: object) -> bool:
    statement = select(Order.id).where(Order.coupon_id == coupon_id)
    return session.scalar(statement) is not None
