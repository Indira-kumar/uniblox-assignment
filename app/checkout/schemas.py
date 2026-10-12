"""Checkout request model."""

from pydantic import BaseModel, Field


class CheckoutRequest(BaseModel):
    quote_token: str = Field(min_length=64, max_length=64, pattern=r"^[0-9a-f]{64}$")
