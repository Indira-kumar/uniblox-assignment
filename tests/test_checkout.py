"""Checkout invariants exercised through the API and real PostgreSQL transactions."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.db.seed import seed_products
from app.db.session import get_engine, get_session_factory
from app.main import app


@pytest.fixture(autouse=True)
def fresh_catalog() -> None:
    if make_url(str(get_engine().url)).database != "checkout_test":
        raise RuntimeError("Integration tests require the checkout_test database")
    with get_engine().begin() as connection:
        connection.execute(text("TRUNCATE TABLE products, carts RESTART IDENTITY CASCADE"))
    with get_session_factory().begin() as session:
        seed_products(session)


def cart_with_item(client: TestClient, product_id: int = 1, quantity: int = 1) -> dict:
    cart = client.post("/carts").json()
    response = client.put(f"/carts/{cart['id']}/items/{product_id}", json={"quantity": quantity})
    assert response.status_code == 200
    return response.json()


def test_checkout_snapshots_prices_and_replays_identical_request() -> None:
    with TestClient(app) as client:
        cart = cart_with_item(client, quantity=2)
        request = {"quote_token": cart["quote_token"]}
        first = client.post(f"/carts/{cart['id']}/checkout", json=request)
        assert first.status_code == 201
        order = first.json()
        assert order["gross_cents"] == 3198
        assert order["discount_cents"] == 0
        assert order["lines"][0]["unit_price_cents"] == 1599

        replay = client.post(f"/carts/{cart['id']}/checkout", json=request)
        assert replay.status_code == 200
        assert replay.json() == order
        assert client.get(f"/orders/{order['id']}").json() == order
        assert client.put(f"/carts/{cart['id']}/items/1", json={"quantity": 3}).status_code == 409

        with get_session_factory().begin() as session:
            session.execute(text("UPDATE products SET price_cents = 1699 WHERE id = 1"))
            stock = session.scalar(text("SELECT stock_quantity FROM products WHERE id = 1"))
        assert stock == 18
        assert client.get(f"/orders/{order['id']}").json() == order


def test_stale_quote_and_insufficient_stock_leave_no_order_or_stock_change() -> None:
    with TestClient(app) as client:
        cart = cart_with_item(client)
        with get_session_factory().begin() as session:
            session.execute(text("UPDATE products SET price_cents = 1699 WHERE id = 1"))
        stale = client.post(
            f"/carts/{cart['id']}/checkout", json={"quote_token": cart["quote_token"]}
        )
        assert stale.status_code == 409
        assert stale.json()["code"] == "STALE_QUOTE"

        refreshed = client.get(f"/carts/{cart['id']}").json()
        with get_session_factory().begin() as session:
            session.execute(text("UPDATE products SET stock_quantity = 0 WHERE id = 1"))
        short = client.post(
            f"/carts/{cart['id']}/checkout", json={"quote_token": refreshed["quote_token"]}
        )
        assert short.status_code == 409
        assert short.json()["code"] == "INSUFFICIENT_STOCK"
        with get_session_factory().begin() as session:
            assert session.scalar(text("SELECT count(*) FROM orders")) == 0
            assert session.scalar(text("SELECT stock_quantity FROM products WHERE id = 1")) == 0


def test_competing_carts_cannot_buy_the_same_last_unit() -> None:
    with TestClient(app) as client:
        carts = [cart_with_item(client, product_id=5) for _ in range(2)]

        def submit(cart: dict) -> tuple[int, str | None]:
            response = client.post(
                f"/carts/{cart['id']}/checkout", json={"quote_token": cart["quote_token"]}
            )
            return response.status_code, response.json().get("code")

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, carts))

        assert sorted(status for status, _ in results) == [201, 409]
        assert [code for _, code in results if code] == ["INSUFFICIENT_STOCK"]
        with get_session_factory().begin() as session:
            assert session.scalar(text("SELECT count(*) FROM orders")) == 1
            assert session.scalar(text("SELECT stock_quantity FROM products WHERE id = 5")) == 0


def test_competing_retries_create_only_one_order() -> None:
    with TestClient(app) as client:
        cart = cart_with_item(client)

        def submit(_unused: int) -> tuple[int, str]:
            response = client.post(
                f"/carts/{cart['id']}/checkout", json={"quote_token": cart["quote_token"]}
            )
            return response.status_code, response.json()["id"]

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, range(2)))
        assert sorted(status for status, _ in results) == [200, 201]
        assert results[0][1] == results[1][1]
        with get_session_factory().begin() as session:
            assert session.scalar(text("SELECT count(*) FROM orders")) == 1
            assert session.scalar(text("SELECT stock_quantity FROM products WHERE id = 1")) == 19
