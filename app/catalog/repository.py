"""Catalog queries; transaction ownership stays with the caller."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.catalog.models import Product


def list_products(session: Session) -> list[Product]:
    statement = select(Product).order_by(Product.id)
    return list(session.scalars(statement))
