"""Public order reads."""

from uuid import UUID

from fastapi import APIRouter

from app.api.dependencies import SessionDependency
from app.orders import service
from app.orders.schemas import OrderResponse

router = APIRouter(prefix="/orders", tags=["orders"])


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(order_id: UUID, session: SessionDependency) -> OrderResponse:
    return service.get_order(session, order_id)
