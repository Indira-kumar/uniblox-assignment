"""Catalog smoke test against a real PostgreSQL database."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError

from app.catalog.models import Product
from app.db.seed import seed_products
from app.db.session import get_engine, get_session_factory
from app.main import app


@pytest.fixture(autouse=True)
def empty_test_catalog() -> Iterator[None]:
    database_name = make_url(str(get_engine().url)).database
    if database_name != "checkout_test":
        raise RuntimeError("Catalog integration tests require the checkout_test database")

    with get_engine().begin() as connection:
        connection.execute(text("TRUNCATE TABLE products RESTART IDENTITY CASCADE"))
    yield


def test_seed_is_repeatable_and_products_are_exposed() -> None:
    with get_session_factory().begin() as session:
        assert seed_products(session) == 5

    with get_session_factory().begin() as session:
        assert seed_products(session) == 0

    with TestClient(app) as client:
        response = client.get("/products")

    assert response.status_code == 200
    products = response.json()
    assert len(products) == 5
    assert [product["id"] for product in products] == [1, 2, 3, 4, 5]
    assert products[-1]["stock_quantity"] == 1
    assert all(product["price_cents"] >= 0 for product in products)


def test_database_rejects_negative_stock() -> None:
    with pytest.raises(IntegrityError), get_session_factory().begin() as session:
        session.add(Product(id=99, name="Invalid", price_cents=100, stock_quantity=-1))
        session.flush()
