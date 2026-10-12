"""Report response contract."""

from pydantic import BaseModel


class ProductQuantity(BaseModel):
    product_id: int
    purchased_quantity: int


class CouponCounts(BaseModel):
    generated: int
    available: int
    redeemed: int


class ReportResponse(BaseModel):
    total_orders: int
    purchased_quantities: list[ProductQuantity]
    gross_revenue_cents: int
    total_discounts_cents: int
    net_revenue_cents: int
    coupons: CouponCounts
