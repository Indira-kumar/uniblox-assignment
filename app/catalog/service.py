"""Catalog use cases."""

from sqlalchemy.orm import Session

from app.catalog import repository
from app.catalog.models import Product


def list_products(session: Session) -> list[Product]:
    return repository.list_products(session)
