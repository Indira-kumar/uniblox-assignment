"""Public cart endpoints."""

from uuid import UUID

from fastapi import APIRouter, Response, status

from app.api.dependencies import SessionDependency
from app.carts import service
from app.carts.schemas import CartResponse, SetItemRequest

router = APIRouter(prefix="/carts", tags=["carts"])


@router.post("", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
def create_cart(session: SessionDependency) -> CartResponse:
    return service.create_cart(session)


@router.get("/{cart_id}", response_model=CartResponse)
def get_cart(cart_id: UUID, session: SessionDependency) -> CartResponse:
    return service.get_cart(session, cart_id)


@router.put("/{cart_id}/items/{product_id}", response_model=CartResponse)
def set_item(
    cart_id: UUID, product_id: int, body: SetItemRequest, session: SessionDependency
) -> CartResponse:
    return service.set_item(session, cart_id, product_id, body.quantity)


@router.delete("/{cart_id}/items/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_item(cart_id: UUID, product_id: int, session: SessionDependency) -> Response:
    service.remove_item(session, cart_id, product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
