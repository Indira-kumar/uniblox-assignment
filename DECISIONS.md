# Engineering decisions

Approximate active time: 2-3 hours across design, implementation, tests, and review.

## Decision: PostgreSQL and a modular monolith

- **Context:** Cart, stock, and coupon rules must hold across API workers.
- **Options considered:** SQLite, separate services, or one PostgreSQL-backed service.
- **Choice:** FastAPI with PostgreSQL, SQLAlchemy, and Alembic.
- **Why:** Row locks and database constraints are enough to coordinate workers (and postgreSQL is scalable)
- **Consequences:** Any future service split needs a clear split of responsibilities

## Decision: Fresh quotes and order snapshots
- **Context:** Product data can change between adding an item and checkout.
- **Options considered:** Freeze prices on add, silently use current prices, or require a current quote.
- **Choice:** A SHA-256 token covers cart version and current product IDs, names, quantities, and prices. Checkout validates it after locking products
- **Why:** The customer accepts the current amount, and later catalog edits cannot change the order record.
- **Consequences:** Even a name-only change invalidates a quote.

## Decision: Idempotency: One order per cart for retries

- **Context:** A client may retry after a timeout or send two checkouts at once.
- **Options considered:** A separate idempotency-key table, timing-based deduplication, or cart-scoped idempotency.
- **Choice:** Lock the cart, store a fingerprint of the quote and normalized coupon, and enforce unique `orders.cart_id`. The same request returns the order with `200`; a different one returns `409`.
- **Why:** A cart is already single-use, so its ID is the retry key.
- **Consequences:** Another purchase needs another cart. Real payment attempts would need explicit idempotency keys.

## Decision: Coupon generation and redemption
- **Context:** Concurrent admin requests must not create duplicate coupons. Concurrent checkouts must not redeem the same coupon twice.
- **Options considered:** A scheduler, in-memory counters, a `used` flag, or linking redemption to a committed order.
- **Choice:** Lock the reward policy and enforce a unique milestone during generation. At checkout, lock the coupon and link it to the order; `orders.coupon_id` is unique.
- **Why:** Locks and constraints protect both operations across workers. If checkout fails, the transaction rolls back and the coupon remains available.
- **Consequences:** Generation is explicit, produces one coupon per request.