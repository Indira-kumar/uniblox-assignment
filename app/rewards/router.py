"""Administrative coupon generation."""

from fastapi import APIRouter, status

from app.api.dependencies import SessionDependency
from app.rewards import service
from app.rewards.schemas import CouponResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post(
    "/coupons/generate", response_model=CouponResponse, status_code=status.HTTP_201_CREATED
)
def generate_coupon(session: SessionDependency) -> CouponResponse:
    return service.generate_coupon(session)
