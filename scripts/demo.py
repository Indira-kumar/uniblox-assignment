"""Repeatable HTTP scenario walkthrough on a dedicated local database."""

import json
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.db.seed import seed_products, seed_reward_policy
from app.db.session import get_engine, get_session_factory
from app.main import app


def reset_demo_data() -> None:
    if make_url(str(get_engine().url)).database != "checkout_demo":
        raise RuntimeError("Demo can only reset checkout_demo")
    with get_engine().begin() as connection:
        connection.execute(
            text("TRUNCATE products, carts, coupons, reward_policy RESTART IDENTITY CASCADE")
        )
    with get_session_factory().begin() as session:
        seed_products(session)
        seed_reward_policy(session)


def make_cart(client: TestClient, product_id: int, quantity: int = 1) -> dict:
    cart = client.post("/carts").json()
    response = client.put(f"/carts/{cart['id']}/items/{product_id}", json={"quantity": quantity})
    assert response.status_code == 200, response.text
    return response.json()


def submit(client: TestClient, cart: dict, coupon_code: str | None = None) -> tuple[int, dict]:
    response = client.post(
        f"/carts/{cart['id']}/checkout",
        json={"quote_token": cart["quote_token"], "coupon_code": coupon_code},
    )
    return response.status_code, response.json()


def main() -> None:
    reset_demo_data()
    with TestClient(app) as client:
        first_five = [submit(client, make_cart(client, 3)) for _ in range(5)]
        assert all(status == 201 for status, _ in first_five)
        coupon_response = client.post("/admin/coupons/generate")
        assert coupon_response.status_code == 201, coupon_response.text
        coupon = coupon_response.json()
        assert client.post("/admin/coupons/generate").status_code == 409

        last_unit_carts = [make_cart(client, 5) for _ in range(2)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            stock_race = list(pool.map(lambda cart: submit(client, cart), last_unit_carts))
        assert sorted(status for status, _ in stock_race) == [201, 409]

        stale_cart = make_cart(client, 2)
        with get_session_factory().begin() as session:
            session.execute(text("UPDATE products SET price_cents = 1399 WHERE id = 2"))
        stale_status, stale_body = submit(client, stale_cart)
        assert (stale_status, stale_body["code"]) == (409, "STALE_QUOTE")

        failed_cart = make_cart(client, 5, quantity=2)
        failed_status, failed_body = submit(client, failed_cart, coupon["code"])
        assert (failed_status, failed_body["code"]) == (409, "INSUFFICIENT_STOCK")

        coupon_carts = [make_cart(client, 1) for _ in range(2)]
        with ThreadPoolExecutor(max_workers=2) as pool:
            coupon_race = list(
                pool.map(lambda cart: submit(client, cart, coupon["code"]), coupon_carts)
            )
        assert sorted(status for status, _ in coupon_race) == [201, 409]
        winner_index = next(i for i, result in enumerate(coupon_race) if result[0] == 201)
        winner = coupon_race[winner_index][1]
        retry_status, retry_order = submit(client, coupon_carts[winner_index], coupon["code"])
        assert retry_status == 200 and retry_order["id"] == winner["id"]

        report_response = client.get("/admin/report")
        assert report_response.status_code == 200
        report = report_response.json()
        assert report["total_orders"] == 7
        assert report["coupons"] == {"generated": 1, "available": 0, "redeemed": 1}
        assert report["gross_revenue_cents"] == (
            report["total_discounts_cents"] + report["net_revenue_cents"]
        )

    print(
        json.dumps(
            {
                "first_five_orders": len(first_five),
                "generated_coupon": coupon,
                "last_unit_race": [status for status, _ in stock_race],
                "stale_quote": stale_body["code"],
                "failed_checkout": failed_body["code"],
                "coupon_race": [status for status, _ in coupon_race],
                "idempotent_retry_status": retry_status,
                "report": report,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
