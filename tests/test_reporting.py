"""Report reconciliation and snapshot consistency."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.db.seed import seed_products, seed_reward_policy
from app.db.session import get_engine, get_session_factory
from app.main import app
from app.reporting import repository as report_repository


@pytest.fixture(autouse=True)
def fresh_report_data() -> None:
    if make_url(str(get_engine().url)).database != "checkout_test":
        raise RuntimeError("Integration tests require the checkout_test database")
    with get_engine().begin() as connection:
        connection.execute(
            text("TRUNCATE products, carts, coupons, reward_policy RESTART IDENTITY CASCADE")
        )
    with get_session_factory().begin() as session:
        seed_products(session)
        seed_reward_policy(session)


def make_cart(client: TestClient, product_id: int = 3) -> dict:
    cart_id = client.post("/carts").json()["id"]
    return client.put(f"/carts/{cart_id}/items/{product_id}", json={"quantity": 1}).json()


def buy(client: TestClient, product_id: int = 3, coupon_code: str | None = None) -> dict:
    cart = make_cart(client, product_id)
    response = client.post(
        f"/carts/{cart['id']}/checkout",
        json={"quote_token": cart["quote_token"], "coupon_code": coupon_code},
    )
    assert response.status_code == 201
    return response.json()


def test_report_reconciles_and_repeated_reads_do_not_mutate() -> None:
    with TestClient(app) as client:
        for _ in range(5):
            buy(client)
        coupon = client.post("/admin/coupons/generate").json()
        buy(client, product_id=1, coupon_code=coupon["code"])

        first = client.get("/admin/report")
        second = client.get("/admin/report")
        assert first.status_code == 200
        assert second.json() == first.json()
        report = first.json()
        assert report == {
            "total_orders": 6,
            "purchased_quantities": [
                {"product_id": 1, "purchased_quantity": 1},
                {"product_id": 3, "purchased_quantity": 5},
            ],
            "gross_revenue_cents": 6094,
            "total_discounts_cents": 160,
            "net_revenue_cents": 5934,
            "coupons": {"generated": 1, "available": 0, "redeemed": 1},
        }
        assert report["gross_revenue_cents"] == (
            report["total_discounts_cents"] + report["net_revenue_cents"]
        )


def test_report_queries_share_snapshot_during_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    with TestClient(app) as reporting_client, TestClient(app) as buying_client:
        cart = make_cart(buying_client)
        original = report_repository.purchased_quantities

        def commit_order_between_queries(session: Session) -> list[tuple[int, int]]:
            response = buying_client.post(
                f"/carts/{cart['id']}/checkout", json={"quote_token": cart["quote_token"]}
            )
            assert response.status_code == 201
            return original(session)

        monkeypatch.setattr(report_repository, "purchased_quantities", commit_order_between_queries)
        report = reporting_client.get("/admin/report")
        assert report.status_code == 200
        assert report.json()["total_orders"] == 0
        assert report.json()["purchased_quantities"] == []
        monkeypatch.setattr(report_repository, "purchased_quantities", original)
        next_report = reporting_client.get("/admin/report").json()
        assert next_report["total_orders"] == 1
        assert next_report["purchased_quantities"] == [{"product_id": 3, "purchased_quantity": 1}]
