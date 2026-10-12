"""Catalog persistence model."""

from sqlalchemy import BigInteger, CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price_cents >= 0", name="ck_products_price_nonnegative"),
        CheckConstraint("stock_quantity >= 0", name="ck_products_stock_nonnegative"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    price_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    stock_quantity: Mapped[int] = mapped_column(Integer, nullable=False)
