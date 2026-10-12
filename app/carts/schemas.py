"""Cart HTTP models."""

from uuid import UUID

from pydantic import BaseModel, Field


class SetItemRequest(BaseModel):
    quantity: int = Field(gt=0, le=1_000_000, strict=True)


class CartItemResponse(BaseModel):
    product_id: int
    name: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int
    available_stock: int


class CartResponse(BaseModel):
    id: UUID
    status: str
    version: int
    items: list[CartItemResponse]
    gross_cents: int
    quote_token: str
