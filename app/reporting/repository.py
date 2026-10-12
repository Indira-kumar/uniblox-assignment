"""Aggregate immutable purchase and coupon records."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.orders.models import Order, OrderLine
from app.rewards.models import Coupon


def order_totals(session: Session) -> tuple[int, int, int, int]:
    statement = select(
        func.count(Order.id),
        func.coalesce(func.sum(Order.gross_cents), 0),
        func.coalesce(func.sum(Order.discount_cents), 0),
        func.coalesce(func.sum(Order.net_cents), 0),
    )
    return tuple(session.execute(statement).one())


def purchased_quantities(session: Session) -> list[tuple[int, int]]:
    statement = (
        select(OrderLine.product_id, func.sum(OrderLine.quantity))
        .group_by(OrderLine.product_id)
        .order_by(OrderLine.product_id)
    )
    return [(product_id, quantity) for product_id, quantity in session.execute(statement)]


def coupon_counts(session: Session) -> tuple[int, int]:
    statement = select(func.count(Coupon.id), func.count(Order.coupon_id)).outerjoin(
        Order, Order.coupon_id == Coupon.id
    )
    return tuple(session.execute(statement).one())
