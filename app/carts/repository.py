"""Cart persistence operations; the service controls transactions."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.carts.models import Cart, CartItem
from app.catalog.models import Product


def get_cart(session: Session, cart_id: UUID, *, for_update: bool = False) -> Cart | None:
    statement = select(Cart).where(Cart.id == cart_id)
    if for_update:
        statement = statement.with_for_update()
    return session.scalar(statement)


def list_cart_rows(
    session: Session, cart_id: UUID
) -> list[tuple[Cart, CartItem | None, Product | None]]:
    statement = (
        select(Cart, CartItem, Product)
        .outerjoin(CartItem, CartItem.cart_id == Cart.id)
        .outerjoin(Product, Product.id == CartItem.product_id)
        .where(Cart.id == cart_id)
        .order_by(CartItem.product_id)
    )
    return list(session.execute(statement).all())


def get_item(session: Session, cart_id: UUID, product_id: int) -> CartItem | None:
    return session.get(CartItem, (cart_id, product_id))
