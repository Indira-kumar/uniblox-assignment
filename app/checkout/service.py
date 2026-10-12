"""Atomically turn one cart into one order."""

import hashlib
import json
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.carts import repository as cart_repository
from app.catalog import repository as catalog_repository
from app.core.errors import DomainError
from app.core.pricing import MAX_MONEY_CENTS, line_total_cents, make_quote_token
from app.orders import repository as order_repository
from app.orders.models import Order, OrderLine
from app.rewards import repository as reward_repository


@dataclass(frozen=True)
class CheckoutResult:
    order_id: UUID
    created: bool


@dataclass(frozen=True)
class PurchaseLine:
    product_id: int
    product_name: str
    quantity: int
    unit_price_cents: int
    available_stock: int

    @property
    def total_cents(self) -> int:
        return line_total_cents(self.quantity, self.unit_price_cents)


def request_fingerprint(quote_token: str, coupon_code: str | None = None) -> str:
    payload = {"quote_token": quote_token, "coupon_code": coupon_code}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def checkout(
    session: Session, cart_id: UUID, quote_token: str, coupon_code: str | None = None
) -> CheckoutResult:
    fingerprint = request_fingerprint(quote_token, coupon_code)
    with session.begin():
        cart = cart_repository.get_cart(session, cart_id, for_update=True)
        if cart is None:
            raise DomainError("CART_NOT_FOUND", "Cart does not exist", 404)

        existing_order = order_repository.get_by_cart(session, cart_id)
        if existing_order is not None:
            if existing_order.request_fingerprint != fingerprint:
                raise DomainError(
                    "CART_ALREADY_CHECKED_OUT", "Cart was checked out with a different request", 409
                )
            return CheckoutResult(order_id=existing_order.id, created=False)

        if cart.status != "OPEN":
            raise DomainError("CART_ALREADY_CHECKED_OUT", "Cart is already checked out", 409)

        cart_items = cart_repository.list_items(session, cart_id)
        if not cart_items:
            raise DomainError("CART_EMPTY", "Cart has no items", 409)

        lines: list[PurchaseLine] = []
        for cart_item in cart_items:
            product = catalog_repository.get_product(session, cart_item.product_id, for_update=True)
            if product is None:
                raise DomainError(
                    "PRODUCT_NOT_FOUND",
                    "A cart product no longer exists",
                    409,
                    {"product_id": cart_item.product_id},
                )
            lines.append(
                PurchaseLine(
                    product_id=product.id,
                    product_name=product.name,
                    quantity=cart_item.quantity,
                    unit_price_cents=product.price_cents,
                    available_stock=product.stock_quantity,
                )
            )

        actual_quote = make_quote_token(
            cart.version,
            [
                (line.product_id, line.product_name, line.quantity, line.unit_price_cents)
                for line in lines
            ],
        )
        if actual_quote != quote_token:
            raise DomainError(
                "STALE_QUOTE", "Cart or product prices changed; refresh the cart", 409
            )

        for line in lines:
            if line.quantity > line.available_stock:
                raise DomainError(
                    "INSUFFICIENT_STOCK",
                    "Requested quantity exceeds available inventory",
                    409,
                    {
                        "product_id": line.product_id,
                        "requested": line.quantity,
                        "available": line.available_stock,
                    },
                )

        gross_cents = sum(line.total_cents for line in lines)
        if gross_cents > MAX_MONEY_CENTS:
            raise DomainError("CART_TOTAL_TOO_LARGE", "Cart total exceeds the supported range", 422)

        coupon_id = None
        discount_cents = 0
        if coupon_code is not None:
            coupon = reward_repository.get_coupon_by_code(session, coupon_code, for_update=True)
            if coupon is None:
                raise DomainError("COUPON_NOT_FOUND", "Coupon does not exist", 404)
            if reward_repository.is_redeemed(session, coupon.id):
                raise DomainError(
                    "COUPON_ALREADY_REDEEMED", "Coupon has already been redeemed", 409
                )
            coupon_id = coupon.id
            discount_cents = (gross_cents * coupon.discount_percent + 50) // 100

        for line in lines:
            if not catalog_repository.decrement_stock(session, line.product_id, line.quantity):
                raise DomainError(
                    "INSUFFICIENT_STOCK",
                    "Requested quantity exceeds available inventory",
                    409,
                    {"product_id": line.product_id},
                )

        order = Order(
            cart_id=cart_id,
            coupon_id=coupon_id,
            gross_cents=gross_cents,
            discount_cents=discount_cents,
            net_cents=gross_cents - discount_cents,
            request_fingerprint=fingerprint,
        )
        session.add(order)
        session.flush()
        session.add_all(
            OrderLine(
                order_id=order.id,
                product_id=line.product_id,
                product_name=line.product_name,
                quantity=line.quantity,
                unit_price_cents=line.unit_price_cents,
                line_total_cents=line.total_cents,
            )
            for line in lines
        )
        cart.status = "CHECKED_OUT"
        order_id = order.id

    return CheckoutResult(order_id=order_id, created=True)
