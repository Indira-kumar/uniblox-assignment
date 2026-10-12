"""Milestone and redemption races against PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.db.seed import seed_products, seed_reward_policy
from app.db.session import get_engine, get_session_factory
from app.main import app


@pytest.fixture(autouse=True)
def fresh_rewards() -> None:
    if make_url(str(get_engine().url)).database != "checkout_test":
        raise RuntimeError("Integration tests require the checkout_test database")
    with get_engine().begin() as connection:
        connection.execute(
            text("TRUNCATE products, carts, coupons, reward_policy RESTART IDENTITY CASCADE")
        )
    with get_session_factory().begin() as session:
        seed_products(session)
        seed_reward_policy(session)


def make_cart(client: TestClient, product_id: int = 3, quantity: int = 1) -> dict:
    cart_id = client.post("/carts").json()["id"]
    response = client.put(f"/carts/{cart_id}/items/{product_id}", json={"quantity": quantity})
    assert response.status_code == 200
    return response.json()


def place_order(client: TestClient, product_id: int = 3) -> dict:
    cart = make_cart(client, product_id)
    response = client.post(
        f"/carts/{cart['id']}/checkout", json={"quote_token": cart["quote_token"]}
    )
    assert response.status_code == 201
    return response.json()


def test_milestone_generation_is_unique_and_oldest_first() -> None:
    with TestClient(app) as client:
        assert client.post("/admin/coupons/generate").json()["code"] == "NO_ELIGIBLE_MILESTONE"
        for _ in range(4):
            place_order(client)
        assert client.post("/admin/coupons/generate").status_code == 409
        place_order(client)

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: client.post("/admin/coupons/generate"), range(2)))
        assert sorted(response.status_code for response in responses) == [201, 409]
        coupon = next(response.json() for response in responses if response.status_code == 201)
        assert coupon["milestone_number"] == 1
        assert coupon["discount_percent"] == 10

        for _ in range(5):
            place_order(client)
        second = client.post("/admin/coupons/generate")
        assert second.status_code == 201
        assert second.json()["milestone_number"] == 2
        assert client.post("/admin/coupons/generate").status_code == 409


def test_coupon_survives_failed_checkout_and_is_used_once() -> None:
    with TestClient(app) as client:
        for _ in range(5):
            place_order(client)
        coupon = client.post("/admin/coupons/generate").json()

        failed_cart = make_cart(client, product_id=5, quantity=2)
        failed = client.post(
            f"/carts/{failed_cart['id']}/checkout",
            json={"quote_token": failed_cart["quote_token"], "coupon_code": coupon["code"]},
        )
        assert failed.status_code == 409
        assert failed.json()["code"] == "INSUFFICIENT_STOCK"

        cart = make_cart(client, product_id=1)
        request = {"quote_token": cart["quote_token"], "coupon_code": coupon["code"].lower()}
        response = client.post(f"/carts/{cart['id']}/checkout", json=request)
        assert response.status_code == 201
        order = response.json()
        assert order["gross_cents"] == 1599
        assert order["discount_cents"] == 160
        assert order["net_cents"] == 1439
        assert order["coupon_code"] == coupon["code"]
        assert client.post(f"/carts/{cart['id']}/checkout", json=request).status_code == 200

        other = make_cart(client, product_id=1)
        redeemed = client.post(
            f"/carts/{other['id']}/checkout",
            json={"quote_token": other["quote_token"], "coupon_code": coupon["code"]},
        )
        assert redeemed.status_code == 409
        assert redeemed.json()["code"] == "COUPON_ALREADY_REDEEMED"
        with get_session_factory().begin() as session:
            assert (
                session.scalar(text("SELECT count(*) FROM orders WHERE coupon_id IS NOT NULL")) == 1
            )


def test_competing_coupon_redemptions_have_one_winner() -> None:
    with TestClient(app) as client:
        for _ in range(5):
            place_order(client)
        code = client.post("/admin/coupons/generate").json()["code"]
        carts = [make_cart(client, product_id=1) for _ in range(2)]

        def redeem(cart: dict) -> tuple[int, str | None]:
            response = client.post(
                f"/carts/{cart['id']}/checkout",
                json={"quote_token": cart["quote_token"], "coupon_code": code},
            )
            return response.status_code, response.json().get("code")

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(redeem, carts))
        assert sorted(status for status, _ in results) == [201, 409]
        assert [code for _, code in results if code] == ["COUPON_ALREADY_REDEEMED"]
        with get_session_factory().begin() as session:
            assert (
                session.scalar(text("SELECT count(*) FROM orders WHERE coupon_id IS NOT NULL")) == 1
            )
            assert session.scalar(text("SELECT stock_quantity FROM products WHERE id = 1")) == 19
