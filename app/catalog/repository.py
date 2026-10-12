"""Catalog queries; transaction ownership stays with the caller."""

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.catalog.models import Product


def list_products(session: Session) -> list[Product]:
    statement = select(Product).order_by(Product.id)
    return list(session.scalars(statement))


def get_product(session: Session, product_id: int, *, for_update: bool = False) -> Product | None:
    statement = select(Product).where(Product.id == product_id)
    if for_update:
        statement = statement.with_for_update()
    return session.scalar(statement)


def decrement_stock(session: Session, product_id: int, quantity: int) -> bool:
    statement = (
        update(Product)
        .where(Product.id == product_id, Product.stock_quantity >= quantity)
        .values(stock_quantity=Product.stock_quantity - quantity)
        .returning(Product.id)
    )
    return session.scalar(statement) is not None
