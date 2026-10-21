"""Exercise two API workers over HTTP and reconcile the resulting purchases."""

import json
import math
import os
import subprocess
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from threading import Barrier

import httpx2
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.db.seed import seed_products, seed_reward_policy
from app.db.session import get_engine, get_session_factory

BASE_URL = "http://127.0.0.1:8000"
PRODUCT_ID = 3
UNIT_PRICE_CENTS = 899


@dataclass
class WorkerResult:
    order_ids: list[str] = field(default_factory=list)
    checkout_ms: list[float] = field(default_factory=list)
    flow_ms: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    requests: int = 0


def load_settings() -> tuple[int, int]:
    orders = int(os.getenv("LOAD_ORDERS", "100"))
    clients = int(os.getenv("LOAD_CLIENTS", "8"))
    if not 1 <= orders <= 10_000 or not 1 <= clients <= min(orders, 128):
        raise ValueError("Use 1-10,000 orders and 1-min(orders, 128) clients")
    return orders, clients


def reset_load_data(orders: int) -> None:
    url = make_url(str(get_engine().url))
    if url.host != "db" or url.database != "checkout_load":
        raise RuntimeError("Load test can only reset the local Compose checkout_load database")
    with get_engine().begin() as connection:
        connection.execute(
            text("TRUNCATE products, carts, coupons, reward_policy RESTART IDENTITY CASCADE")
        )
    with get_session_factory().begin() as session:
        seed_products(session)
        seed_reward_policy(session)
        session.execute(
            text("UPDATE products SET stock_quantity = :stock WHERE id = :product_id"),
            {"stock": orders, "product_id": PRODUCT_ID},
        )


def wait_for_api(process: subprocess.Popen[str]) -> None:
    with httpx2.Client(base_url=BASE_URL, timeout=1.0) as client:
        for _ in range(100):
            if process.poll() is not None:
                raise RuntimeError("API workers exited during startup")
            try:
                if client.get("/health/ready").status_code == 200:
                    return
            except httpx2.HTTPError:
                pass
            time.sleep(0.1)
    raise TimeoutError("API workers did not become ready within 10 seconds")


def request_json(
    client: httpx2.Client, method: str, path: str, expected_status: int, body: dict | None = None
) -> tuple[dict, float]:
    started = time.perf_counter()
    response = client.request(method, path, json=body)
    elapsed_ms = (time.perf_counter() - started) * 1000
    if response.status_code != expected_status:
        raise RuntimeError(f"{method} {path}: HTTP {response.status_code}: {response.text[:200]}")
    return response.json(), elapsed_ms


def run_worker(flow_count: int, start_barrier: Barrier) -> WorkerResult:
    result = WorkerResult()
    with httpx2.Client(base_url=BASE_URL, timeout=15.0) as client:
        start_barrier.wait()
        for _ in range(flow_count):
            started = time.perf_counter()
            try:
                result.requests += 1
                cart, _ = request_json(client, "POST", "/carts", 201)
                result.requests += 1
                cart, _ = request_json(
                    client,
                    "PUT",
                    f"/carts/{cart['id']}/items/{PRODUCT_ID}",
                    200,
                    {"quantity": 1},
                )
                path = f"/carts/{cart['id']}/checkout"
                body = {"quote_token": cart["quote_token"]}
                result.requests += 1
                order, checkout_ms = request_json(client, "POST", path, 201, body)
                result.requests += 1
                retry, _ = request_json(client, "POST", path, 200, body)
                if retry["id"] != order["id"]:
                    raise RuntimeError("Checkout retry returned a different order")
                result.order_ids.append(order["id"])
                result.checkout_ms.append(checkout_ms)
                result.flow_ms.append((time.perf_counter() - started) * 1000)
            except Exception as error:
                result.errors.append(str(error))
    return result


def percentile(values: list[float], percent: int) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return round(ordered[math.ceil(percent * len(ordered) / 100) - 1], 2)


def latency_summary(values: list[float]) -> dict[str, float | None]:
    return {f"p{percent}": percentile(values, percent) for percent in (50, 95, 99)}


def run_load(orders: int, clients: int) -> dict:
    barrier = Barrier(clients)
    per_client = [orders // clients + (index < orders % clients) for index in range(clients)]
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=clients) as executor:
        results = list(executor.map(lambda count: run_worker(count, barrier), per_client))
    elapsed = time.perf_counter() - started

    order_ids = [order_id for result in results for order_id in result.order_ids]
    checkout_ms = [duration for result in results for duration in result.checkout_ms]
    flow_ms = [duration for result in results for duration in result.flow_ms]
    errors = [error for result in results for error in result.errors]
    request_count = sum(result.requests for result in results)

    with httpx2.Client(base_url=BASE_URL, timeout=15.0) as client:
        report, _ = request_json(client, "GET", "/admin/report", 200)
    with get_session_factory().begin() as session:
        remaining_stock = session.scalar(
            text("SELECT stock_quantity FROM products WHERE id = :product_id"),
            {"product_id": PRODUCT_ID},
        )

    passed = (
        not errors
        and len(order_ids) == orders
        and len(set(order_ids)) == orders
        and report["total_orders"] == orders
        and report["purchased_quantities"]
        == [{"product_id": PRODUCT_ID, "purchased_quantity": orders}]
        and report["gross_revenue_cents"] == orders * UNIT_PRICE_CENTS
        and report["total_discounts_cents"] == 0
        and report["net_revenue_cents"] == orders * UNIT_PRICE_CENTS
        and report["coupons"] == {"generated": 0, "available": 0, "redeemed": 0}
        and remaining_stock == 0
    )
    return {
        "passed": passed,
        "target_orders": orders,
        "concurrent_clients": clients,
        "completed_flows": len(order_ids),
        "unexpected_error_count": len(errors),
        "sample_errors": errors[:5],
        "elapsed_seconds": round(elapsed, 2),
        "http_requests": request_count + 1,
        "http_requests_per_second": round((request_count + 1) / elapsed, 2),
        "orders_per_second": round(len(order_ids) / elapsed, 2),
        "checkout_latency_ms": latency_summary(checkout_ms),
        "full_flow_latency_ms": latency_summary(flow_ms),
        "remaining_stock": remaining_stock,
        "report": report,
    }


def main() -> None:
    orders, clients = load_settings()
    reset_load_data(orders)
    with tempfile.TemporaryFile(mode="w+t") as server_log:
        server = subprocess.Popen(
            ["uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000", "--workers", "2"],
            stdout=server_log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            wait_for_api(server)
            summary = run_load(orders, clients)
            print(json.dumps(summary, indent=2), flush=True)
            if not summary["passed"]:
                raise SystemExit(1)
        except Exception:
            server_log.seek(0)
            print(server_log.read()[-4000:], flush=True)
            raise
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()


if __name__ == "__main__":
    main()
