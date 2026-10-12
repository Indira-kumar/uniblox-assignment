"""Administrative report endpoint."""

from fastapi import APIRouter

from app.api.dependencies import SessionDependency
from app.reporting import service
from app.reporting.schemas import ReportResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/report", response_model=ReportResponse)
def get_report(session: SessionDependency) -> ReportResponse:
    return service.get_report(session)
