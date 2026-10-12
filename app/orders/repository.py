"""Order reads through a caller-owned session."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.orders.models import Order, OrderLine


def get_by_id(session: Session, order_id: UUID) -> Order | None:
    return session.get(Order, order_id)


def get_by_cart(session: Session, cart_id: UUID) -> Order | None:
    return session.scalar(select(Order).where(Order.cart_id == cart_id))


def list_lines(session: Session, order_id: UUID) -> list[OrderLine]:
    statement = (
        select(OrderLine).where(OrderLine.order_id == order_id).order_by(OrderLine.product_id)
    )
    return list(session.scalars(statement))
