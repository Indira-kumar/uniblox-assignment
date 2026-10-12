"""Read orders from immutable snapshots."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.orders import repository
from app.orders.schemas import OrderLineResponse, OrderResponse
from app.rewards import repository as reward_repository


def get_order(session: Session, order_id: UUID) -> OrderResponse:
    order = repository.get_by_id(session, order_id)
    if order is None:
        raise DomainError("ORDER_NOT_FOUND", "Order does not exist", 404)

    lines = [
        OrderLineResponse(
            product_id=line.product_id,
            product_name=line.product_name,
            quantity=line.quantity,
            unit_price_cents=line.unit_price_cents,
            line_total_cents=line.line_total_cents,
        )
        for line in repository.list_lines(session, order_id)
    ]
    return OrderResponse(
        id=order.id,
        cart_id=order.cart_id,
        coupon_code=(
            reward_repository.get_coupon(session, order.coupon_id).code if order.coupon_id else None
        ),
        lines=lines,
        gross_cents=order.gross_cents,
        discount_cents=order.discount_cents,
        net_cents=order.net_cents,
        created_at=order.created_at,
    )
