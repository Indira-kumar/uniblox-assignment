"""Order HTTP response models."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OrderLineResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int


class OrderResponse(BaseModel):
    id: UUID
    cart_id: UUID
    coupon_code: str | None
    lines: list[OrderLineResponse]
    gross_cents: int
    discount_cents: int
    net_cents: int
    created_at: datetime
