# Implementation modules

The service is a modular monolith. Each module lands with its focused tests before work starts on the next one.

| Order | Module | Scope | Completion check |
| --- | --- | --- | --- |
| 1 | Foundation and catalog | uv project, Docker Compose, migrations, seeded products, product API, lint and format commands | Compose starts; products are returned from PostgreSQL; seed is repeatable |
| 2 | Carts and quotes | Create/read carts, set/remove items, live prices, quote token | Invalid items are rejected; mutations and price changes invalidate quotes |
| 3 | Checkout and orders | Transactional stock decrement, immutable order snapshot, one order per cart, retry behavior | Repeated and competing checkouts preserve inventory and order invariants |
| 4 | Rewards | Milestone generation and single-use coupon checkout | Competing generation/redemption cannot duplicate or lose coupons |
| 5 | Reporting | Read-only reconciliation across orders, lines, and coupons | Totals agree with stored records and repeated reads do not mutate state |
| 6 | Demonstration and handoff | HTTP scenario runner, complete API examples, `DECISIONS.md`, final review | One command demonstrates retries, races, failures, and reporting |

Database transactions belong to application services. Repositories only query or mutate through the session supplied by a service and never commit independently.
