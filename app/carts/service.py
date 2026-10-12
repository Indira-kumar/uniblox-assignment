"""Cart operations and live-price quotes."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.carts import repository
from app.carts.models import Cart, CartItem
from app.carts.schemas import CartItemResponse, CartResponse
from app.catalog.models import Product
from app.core.errors import DomainError
from app.core.pricing import line_total_cents, make_quote_token


def create_cart(session: Session) -> CartResponse:
    with session.begin():
        cart = Cart()
        session.add(cart)
        session.flush()
        cart_id = cart.id
    return get_cart(session, cart_id)


def get_cart(session: Session, cart_id: UUID) -> CartResponse:
    rows = repository.list_cart_rows(session, cart_id)
    if not rows:
        raise DomainError("CART_NOT_FOUND", "Cart does not exist", 404)

    cart = rows[0][0]
    items: list[CartItemResponse] = []
    quote_lines: list[tuple[int, str, int, int]] = []
    for _, cart_item, product in rows:
        if cart_item is None:
            continue
        if product is None:
            raise RuntimeError("Cart item references a missing product")
        items.append(_item_response(cart_item, product))
        quote_lines.append((product.id, product.name, cart_item.quantity, product.price_cents))

    return CartResponse(
        id=cart.id,
        status=cart.status,
        version=cart.version,
        items=items,
        gross_cents=sum(item.line_total_cents for item in items),
        quote_token=make_quote_token(cart.version, quote_lines),
    )


def set_item(session: Session, cart_id: UUID, product_id: int, quantity: int) -> CartResponse:
    with session.begin():
        cart = _open_cart_for_update(session, cart_id)
        product = session.get(Product, product_id)
        if product is None:
            raise DomainError("PRODUCT_NOT_FOUND", "Product does not exist", 404)
        item = repository.get_item(session, cart_id, product_id)
        if item is None:
            session.add(CartItem(cart_id=cart_id, product_id=product_id, quantity=quantity))
            cart.version += 1
        elif item.quantity != quantity:
            item.quantity = quantity
            cart.version += 1
    return get_cart(session, cart_id)


def remove_item(session: Session, cart_id: UUID, product_id: int) -> None:
    with session.begin():
        cart = _open_cart_for_update(session, cart_id)
        item = repository.get_item(session, cart_id, product_id)
        if item is None:
            raise DomainError("CART_ITEM_NOT_FOUND", "Cart item does not exist", 404)
        session.delete(item)
        cart.version += 1


def _open_cart_for_update(session: Session, cart_id: UUID) -> Cart:
    cart = repository.get_cart(session, cart_id, for_update=True)
    if cart is None:
        raise DomainError("CART_NOT_FOUND", "Cart does not exist", 404)
    if cart.status != "OPEN":
        raise DomainError("CART_ALREADY_CHECKED_OUT", "Cart is already checked out", 409)
    return cart


def _item_response(item: CartItem, product: Product) -> CartItemResponse:
    return CartItemResponse(
        product_id=product.id,
        name=product.name,
        quantity=item.quantity,
        unit_price_cents=product.price_cents,
        line_total_cents=line_total_cents(item.quantity, product.price_cents),
        available_stock=product.stock_quantity,
    )
