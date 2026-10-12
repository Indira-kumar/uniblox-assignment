"""Generate exactly one coupon for the oldest eligible milestone."""

import secrets

from sqlalchemy.orm import Session

from app.core.errors import DomainError
from app.rewards import repository
from app.rewards.models import Coupon
from app.rewards.schemas import CouponResponse


def generate_coupon(session: Session) -> CouponResponse:
    with session.begin():
        policy = repository.get_policy(session, for_update=True)
        if policy is None:
            raise RuntimeError("Reward policy has not been seeded")

        milestone_number = repository.next_milestone_number(session)
        if milestone_number * policy.orders_per_coupon > repository.placed_order_count(session):
            raise DomainError(
                "NO_ELIGIBLE_MILESTONE", "No unrewarded order milestone is eligible", 409
            )

        coupon = Coupon(
            code=secrets.token_hex(12).upper(),
            milestone_number=milestone_number,
            discount_percent=policy.discount_percent,
        )
        session.add(coupon)
        session.flush()
        response = CouponResponse(
            id=coupon.id,
            code=coupon.code,
            milestone_number=coupon.milestone_number,
            discount_percent=coupon.discount_percent,
            created_at=coupon.created_at,
        )
    return response
