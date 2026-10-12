"""Repeatable catalog seed for local evaluation."""

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.catalog.models import Product
from app.db.session import get_session_factory

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


def main() -> None:
    with get_session_factory().begin() as session:
        inserted = seed_products(session)
    print(f"Seeded {inserted} products")


if __name__ == "__main__":
    main()
