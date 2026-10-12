"""Cart checkout endpoint."""

from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import SessionDependency
from app.checkout import service
from app.checkout.schemas import CheckoutRequest
from app.orders import service as order_service
from app.orders.schemas import OrderResponse

router = APIRouter(tags=["checkout"])


@router.post(
    "/carts/{cart_id}/checkout",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
def checkout(
    cart_id: UUID, body: CheckoutRequest, response: Response, session: SessionDependency
) -> OrderResponse:
    result = service.checkout(session, cart_id, body.quote_token, body.coupon_code)
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return order_service.get_order(session, result.order_id)
