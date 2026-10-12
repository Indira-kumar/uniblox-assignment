"""Cart behavior against PostgreSQL through the HTTP API."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.seed import seed_products
from app.db.session import get_engine, get_session_factory
from app.main import app


@pytest.fixture(autouse=True)
def seeded_catalog() -> Iterator[None]:
    with get_engine().begin() as connection:
        connection.execute(text("TRUNCATE TABLE carts, products RESTART IDENTITY CASCADE"))
    with get_session_factory().begin() as session:
        seed_products(session)
    yield


def test_cart_item_lifecycle_and_idempotent_set() -> None:
    with TestClient(app) as client:
        cart = client.post("/carts").json()
        assert cart["items"] == []
        assert cart["gross_cents"] == 0

        url = f"/carts/{cart['id']}/items/1"
        added = client.put(url, json={"quantity": 2}).json()
        assert added["version"] == 2
        assert added["gross_cents"] == 3198
        assert added["items"][0]["line_total_cents"] == 3198

        repeated = client.put(url, json={"quantity": 2}).json()
        assert repeated["version"] == 2
        assert repeated["quote_token"] == added["quote_token"]

        changed = client.put(url, json={"quantity": 3}).json()
        assert changed["version"] == 3
        assert changed["quote_token"] != added["quote_token"]

        assert client.delete(url).status_code == 204
        empty = client.get(f"/carts/{cart['id']}").json()
        assert empty["items"] == []
        assert empty["version"] == 4


def test_current_price_changes_quote_and_invalid_items_are_rejected() -> None:
    with TestClient(app) as client:
        cart_id = client.post("/carts").json()["id"]
        item_url = f"/carts/{cart_id}/items/1"
        assert client.put(item_url, json={"quantity": 1}).status_code == 200
        quote_before = client.get(f"/carts/{cart_id}").json()

        with get_session_factory().begin() as session:
            session.execute(text("UPDATE products SET price_cents = 1699 WHERE id = 1"))

        quote_after = client.get(f"/carts/{cart_id}").json()
        assert quote_after["gross_cents"] == 1699
        assert quote_after["quote_token"] != quote_before["quote_token"]
        assert quote_after["version"] == quote_before["version"]

        missing = client.put(f"/carts/{cart_id}/items/999", json={"quantity": 1})
        assert missing.status_code == 404
        assert missing.json()["code"] == "PRODUCT_NOT_FOUND"

        invalid = client.put(item_url, json={"quantity": 0})
        assert invalid.status_code == 422
        assert invalid.json()["code"] == "VALIDATION_ERROR"

        boolean_quantity = client.put(item_url, json={"quantity": True})
        assert boolean_quantity.status_code == 422
