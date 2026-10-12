"""Immutable purchase records."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("gross_cents >= 0", name="ck_orders_gross_nonnegative"),
        CheckConstraint("discount_cents >= 0", name="ck_orders_discount_nonnegative"),
        CheckConstraint("net_cents >= 0", name="ck_orders_net_nonnegative"),
        CheckConstraint(
            "gross_cents = discount_cents + net_cents", name="ck_orders_total_reconciles"
        ),
    )

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)
    cart_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("carts.id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    coupon_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("coupons.id", ondelete="RESTRICT"),
        unique=True,
        nullable=True,
    )
    gross_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    discount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    net_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OrderLine(Base):
    __tablename__ = "order_lines"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_order_lines_quantity_positive"),
        CheckConstraint("unit_price_cents >= 0", name="ck_order_lines_price_nonnegative"),
        CheckConstraint("line_total_cents >= 0", name="ck_order_lines_total_nonnegative"),
        CheckConstraint(
            "line_total_cents = quantity * unit_price_cents", name="ck_order_lines_total_reconciles"
        ),
    )

    order_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), primary_key=True
    )
    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_name: Mapped[str] = mapped_column(String(120), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    line_total_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
