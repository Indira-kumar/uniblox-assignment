# HTTP API

Base URL: `http://localhost:8000`. IDs in paths are UUIDs except product IDs, which are integers. Prices and totals are integer USD cents. The administrative routes are under `/admin`; authentication is intentionally outside this assignment's scope.

## Endpoints

| Method and path | Request | Success response | Important errors |
| --- | --- | --- | --- |
| `GET /products` | None | `200`: array of `{id, name, price_cents, stock_quantity}` | Database unavailable |
| `POST /carts` | No body | `201`: cart object | Database unavailable |
| `GET /carts/{cart_id}` | None | `200`: cart object with current prices and quote | `404 CART_NOT_FOUND` |
| `PUT /carts/{cart_id}/items/{product_id}` | `{"quantity": 2}`; absolute integer quantity 1–1,000,000 | `200`: updated cart object | `404 CART_NOT_FOUND` or `PRODUCT_NOT_FOUND`; `409 CART_ALREADY_CHECKED_OUT`; `422 VALIDATION_ERROR` |
| `DELETE /carts/{cart_id}/items/{product_id}` | None | `204`: empty body | `404 CART_NOT_FOUND` or `CART_ITEM_NOT_FOUND`; `409 CART_ALREADY_CHECKED_OUT` |
| `POST /carts/{cart_id}/checkout` | `{"quote_token": "<64 lowercase hex characters>", "coupon_code": "<optional code>"}` | `201`: order object; exact retry returns `200` and the same order | `404 CART_NOT_FOUND` or `COUPON_NOT_FOUND`; `409 CART_EMPTY`, `STALE_QUOTE`, `INSUFFICIENT_STOCK`, `COUPON_ALREADY_REDEEMED`, or `CART_ALREADY_CHECKED_OUT`; `422 VALIDATION_ERROR` or `CART_TOTAL_TOO_LARGE` |
| `GET /orders/{order_id}` | None | `200`: immutable order object | `404 ORDER_NOT_FOUND` |
| `POST /admin/coupons/generate` | No body | `201`: coupon object | `409 NO_ELIGIBLE_MILESTONE` |
| `GET /admin/report` | None | `200`: report object | Database unavailable |
| `GET /health/live` | None | `200`: `{"status":"ok"}` | None |
| `GET /health/ready` | None | `200`: `{"status":"ok"}` | Database unavailable |

### Cart object

```json
{
  "id": "<uuid>",
  "status": "OPEN",
  "version": 2,
  "items": [
    {"product_id": 1, "name": "Canvas Tote", "quantity": 2, "unit_price_cents": 1599, "line_total_cents": 3198, "available_stock": 20}
  ],
  "gross_cents": 3198,
  "quote_token": "<64 lowercase hex characters>"
}
```

`status` becomes `CHECKED_OUT` after purchase. Cart totals and `available_stock` reflect current product data. Changing the cart or a product's name or price changes the quote token. Stock changes do not change it; stock is checked at checkout. Repeating a `PUT` with the same quantity leaves the version unchanged.

### Order object

```json
{
  "id": "<uuid>",
  "cart_id": "<uuid>",
  "coupon_code": null,
  "lines": [
    {"product_id": 1, "product_name": "Canvas Tote", "quantity": 2, "unit_price_cents": 1599, "line_total_cents": 3198}
  ],
  "gross_cents": 3198,
  "discount_cents": 0,
  "net_cents": 3198,
  "created_at": "<ISO-8601 timestamp>"
}
```

If a coupon is used, `coupon_code` contains its normalized uppercase code. `gross_cents = discount_cents + net_cents`. Order lines are snapshots and do not change when catalog prices change.

### Coupon object

```json
{
  "id": "<uuid>",
  "code": "<uppercase code>",
  "milestone_number": 1,
  "discount_percent": 10,
  "created_at": "<ISO-8601 timestamp>"
}
```

The first coupon becomes eligible after order `n`, the second after order `2n`, and so on. One `POST` generates at most one coupon. Codes can be applied to any later checkout; there is no expiry or customer binding. Codes are case insensitive at checkout.

### Report object

```json
{
  "total_orders": 6,
  "purchased_quantities": [
    {"product_id": 1, "purchased_quantity": 1},
    {"product_id": 3, "purchased_quantity": 5}
  ],
  "gross_revenue_cents": 6094,
  "total_discounts_cents": 160,
  "net_revenue_cents": 5934,
  "coupons": {"generated": 1, "available": 0, "redeemed": 1}
}
```

Only products with successful purchases appear in `purchased_quantities`. The report is a consistent snapshot; a concurrent checkout appears either wholly or not at all. `generated = available + redeemed`.

## Error body

Expected domain and request validation errors use this shape:

```json
{"code": "INSUFFICIENT_STOCK", "message": "Requested quantity exceeds available inventory", "details": {"product_id": 5, "requested": 2, "available": 1}}
```

`details` may be empty. Invalid UUIDs, quantities, and malformed bodies produce `422 VALIDATION_ERROR`. Infrastructure failures can return a framework `500` response.

## Example checkout

After starting the API, create a cart, add a product, and copy the returned `id` and `quote_token` into the next requests:

```sh
curl -X POST http://localhost:8000/carts
curl -X PUT http://localhost:8000/carts/<cart-id>/items/1 \
  -H 'Content-Type: application/json' -d '{"quantity":2}'
curl -X POST http://localhost:8000/carts/<cart-id>/checkout \
  -H 'Content-Type: application/json' -d '{"quote_token":"<quote-token>"}'
curl http://localhost:8000/admin/report
```

Repeat the checkout `POST` with the same body to see the same order and a `200` status. For a fully automated race and rewards walkthrough, use the Compose demo command in the README.
