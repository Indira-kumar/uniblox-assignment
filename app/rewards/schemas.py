"""Coupon API response."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class CouponResponse(BaseModel):
    id: UUID
    code: str
    milestone_number: int
    discount_percent: int
    created_at: datetime
