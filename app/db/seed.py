"""Repeatable catalog seed for local evaluation."""

import os

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.catalog.models import Product
from app.db.session import get_session_factory
from app.rewards.models import RewardPolicy

SEED_PRODUCTS = (
    {"id": 1, "name": "Canvas Tote", "price_cents": 1599, "stock_quantity": 20},
    {"id": 2, "name": "Ceramic Mug", "price_cents": 1299, "stock_quantity": 12},
    {"id": 3, "name": "Notebook", "price_cents": 899, "stock_quantity": 30},
    {"id": 4, "name": "Desk Lamp", "price_cents": 3499, "stock_quantity": 6},
    {"id": 5, "name": "Limited Edition Print", "price_cents": 2499, "stock_quantity": 1},
)


def seed_products(session: Session) -> int:
    statement = (
        insert(Product).values(SEED_PRODUCTS).on_conflict_do_nothing(index_elements=[Product.id])
    )
    return len(session.scalars(statement.returning(Product.id)).all())


def seed_reward_policy(session: Session) -> bool:
    interval = int(os.getenv("REWARD_EVERY_N", "5"))
    percent = int(os.getenv("REWARD_DISCOUNT_PERCENT", "10"))
    if interval <= 0 or not 1 <= percent <= 100:
        raise ValueError("Reward settings must have n > 0 and 1 <= percent <= 100")
    statement = (
        insert(RewardPolicy)
        .values(id=1, orders_per_coupon=interval, discount_percent=percent)
        .on_conflict_do_nothing(index_elements=[RewardPolicy.id])
        .returning(RewardPolicy.id)
    )
    return session.scalar(statement) is not None


def main() -> None:
    with get_session_factory().begin() as session:
        inserted = seed_products(session)
        policy_inserted = seed_reward_policy(session)
    print(f"Seeded {inserted} products and reward policy inserted={policy_inserted}")


if __name__ == "__main__":
    main()
