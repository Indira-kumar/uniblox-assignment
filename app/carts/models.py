"""Cart persistence models."""

from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Cart(Base):
    __tablename__ = "carts"
    __table_args__ = (
        CheckConstraint("status IN ('OPEN', 'CHECKED_OUT')", name="ck_carts_status"),
        CheckConstraint("version >= 1", name="ck_carts_version_positive"),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (CheckConstraint("quantity > 0", name="ck_cart_items_quantity_positive"),)

    cart_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("carts.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="RESTRICT"), primary_key=True
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
