# Checkout and Rewards Service

A Python API for the reliable checkout assignment. The design is a modular monolith backed by PostgreSQL. Work is being delivered [one module at a time](MODULES.md).

## High-level design

![Checkout service HLD](assets/checkout-service-hld.png)

## Current scope: modules 1–4

The runnable service exposes the seeded product catalog, carts, live-price quotes, atomic checkout, immutable orders, milestone coupons, and health endpoints. Reporting is the next module.

### Run locally with Docker Compose

Docker Compose is the only runtime prerequisite. It starts PostgreSQL, applies migrations, seeds five products, and runs the API with two worker processes:

```sh
docker compose up --build -d api
curl http://localhost:8000/products
```

Open [the generated API documentation](http://localhost:8000/docs) to inspect the endpoints. `GET /health/live` checks the process; `GET /health/ready` checks database connectivity. The seed is repeatable and does not reset inventory in an existing database.

### Run tests and code-quality checks

The test service uses its own `checkout_test` database in the same local PostgreSQL container. Its database is created when the Compose volume is first initialized.

```sh
docker compose --profile test run --build --rm tests
uv sync
uv run ruff check .
uv run ruff format --check .
```

The `uv.lock` file pins Python dependencies. To stop containers, run `docker compose down`. To **erase local database data** and recreate both databases from scratch, run `docker compose down -v`.

## Available API

| Endpoint | Response |
| --- | --- |
| `GET /products` | `200` with product IDs, names, prices in cents, and available inventory |
| `POST /carts` | `201` with an empty cart and quote token |
| `GET /carts/{id}` | `200` with current product prices, line totals, gross, and quote token |
| `PUT /carts/{id}/items/{product_id}` | `200` after setting an absolute positive quantity |
| `DELETE /carts/{id}/items/{product_id}` | `204` after removing an item |
| `POST /carts/{id}/checkout` | `201` with an order; identical retry returns `200` with the same order |
| `GET /orders/{id}` | `200` with immutable purchased lines and totals |
| `POST /admin/coupons/generate` | `201` with a coupon for the oldest eligible milestone; `409` when none is eligible |
| `GET /health/live` | `200` when the API process is running |
| `GET /health/ready` | `200` when PostgreSQL is reachable |

Product 5 has one unit of inventory for the later concurrency demonstration. Prices are integer cents; the intended currency is USD.

Cart items do not reserve inventory or freeze prices. A quote token changes when the cart or a product's displayed details change. Setting the same quantity twice leaves the cart version and quote token unchanged.

Checkout requires the cart's current `quote_token`, locks the cart and products in a stable order, and decrements stock in the same transaction as order creation. A stale quote or insufficient stock returns `409` without a partial order or inventory change.

Checkout accepts an optional `coupon_code`. A generated coupon can be redeemed once; discount is rounded to the nearest cent with half cents rounded up. A failed checkout leaves the coupon available. The seed creates reward settings of one 10% coupon per five placed orders by default. Set `REWARD_EVERY_N` and `REWARD_DISCOUNT_PERCENT` on the migration/seed service before initializing a fresh database to use other values. Existing settings are intentionally not overwritten by a later seed.
