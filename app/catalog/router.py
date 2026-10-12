"""Public product endpoints."""

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict

from app.api.dependencies import SessionDependency
from app.catalog import service

router = APIRouter(prefix="/products", tags=["products"])


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    price_cents: int
    stock_quantity: int


@router.get("", response_model=list[ProductResponse])
def get_products(session: SessionDependency) -> list[ProductResponse]:
    return [ProductResponse.model_validate(product) for product in service.list_products(session)]
