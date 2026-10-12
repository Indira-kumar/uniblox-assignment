"""Read a consistent report without changing state."""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.reporting import repository
from app.reporting.schemas import CouponCounts, ProductQuantity, ReportResponse


def get_report(session: Session) -> ReportResponse:
    with session.begin():
        # All aggregates must see one PostgreSQL snapshot, even during active checkouts.
        session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY"))
        order_count, gross, discounts, net = repository.order_totals(session)
        quantities = repository.purchased_quantities(session)
        generated, redeemed = repository.coupon_counts(session)

    return ReportResponse(
        total_orders=order_count,
        purchased_quantities=[
            ProductQuantity(product_id=product_id, purchased_quantity=quantity)
            for product_id, quantity in quantities
        ],
        gross_revenue_cents=gross,
        total_discounts_cents=discounts,
        net_revenue_cents=net,
        coupons=CouponCounts(
            generated=generated,
            available=generated - redeemed,
            redeemed=redeemed,
        ),
    )
