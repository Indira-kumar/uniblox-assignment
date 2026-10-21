# Checkout and Rewards Service

A Python 3.12, FastAPI, and PostgreSQL service for atomic checkout, milestone coupons, and reconciled reporting. The code is a [modular monolith](MODULES.md) with separate routes, services, repositories, models, and migrations.

![Checkout service HLD](assets/checkout-service-hld.png)

## Run the API

Docker Compose is the only runtime prerequisite. It starts PostgreSQL, applies migrations, seeds five products and the reward policy, and runs two API workers.

```sh
docker compose up --build -d api
curl http://localhost:8000/products
```

The interactive OpenAPI UI is at [localhost:8000/docs](http://localhost:8000/docs). `GET /health/live` checks the API process; `GET /health/ready` checks database connectivity. [API.md](API.md) lists every endpoint, body, response, status, and important error.

The default policy issues one 10% coupon after each fifth successfully placed order. To choose another policy for a **new** database, set `REWARD_EVERY_N` and `REWARD_DISCOUNT_PERCENT` before the first `docker compose up`. Seeding is repeatable and does not overwrite an existing policy or inventory. Product 5 begins with only one unit.

## Show the scenarios

The demo uses its own `checkout_demo` database and resets only that database each time. It runs through five orders, milestone generation, a last-unit race, stale pricing, a failed checkout, competing coupon redemption, an idempotent retry, and the final report.

```sh
docker compose --profile demo run --build --rm demo
```

## Test and inspect

The integration tests use a separate `checkout_test` database and real PostgreSQL transactions.

```sh
docker compose --profile test run --build --rm tests
uv sync
uv run ruff check .
uv run ruff format --check .
uv lock --check
```

`uv.lock` pins the dependencies. `docker compose down` stops the services. `docker compose down -v` **deletes all local Compose database data**, including the API, test, demo, and load databases.

## Put load on the API

The load command uses a dedicated `checkout_load` database. Each run resets that database, starts **two real API worker processes**, and sends HTTP requests through concurrent clients. Each client creates a cart, adds one product, checks out, and retries checkout. The script checks the final order count, revenue, purchased quantity, unique order IDs, and remaining inventory before reporting success.

```sh
docker compose --profile load run --build --rm load
LOAD_ORDERS=500 LOAD_CLIENTS=32 docker compose --profile load run --build --rm load
```

The defaults are 100 orders and 8 concurrent clients. The output includes requests per second, orders per second, and p50/p95/p99 checkout and full-flow latency. `"passed": true` means both the load run and final reconciliation succeeded; the command exits nonzero on failure. Increase concurrency gradually and compare latency, error count, and throughput. In another terminal, `docker stats` shows CPU and memory use. This runs the API, load generator, and PostgreSQL on one machine, so the numbers describe this local setup rather than production capacity. The regular `checkout` database is not reset.

## Behavior at a glance

- Cart prices are live; adding an item does not reserve stock. Checkout accepts the current cart `quote_token` and rejects a stale one with `409 STALE_QUOTE`.
- Checkout locks the cart and products, updates stock, and inserts the order in one transaction. A failed checkout leaves stock and coupons unchanged. An identical retry returns the original order with `200`.
- Orders retain product names, quantities, unit prices, gross, discount, and net. All money is integer USD cents. Percent discounts round half up to the nearest cent.
- Coupon generation creates one coupon for the oldest eligible milestone per request. Each coupon can be linked to at most one order.
- The report reads orders, lines, and coupons from one read-only PostgreSQL snapshot.

The major choices, limits, and scale path are explained in [DECISIONS.md](DECISIONS.md).
