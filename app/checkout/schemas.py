"""Checkout request model."""

from pydantic import BaseModel, Field, field_validator


class CheckoutRequest(BaseModel):
    quote_token: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
    coupon_code: str | None = Field(default=None, min_length=1, max_length=32)

    @field_validator("coupon_code")
    @classmethod
    def normalize_coupon_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        code = value.strip().upper()
        if not code:
            raise ValueError("coupon_code cannot be blank")
        return code
