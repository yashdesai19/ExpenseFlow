from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse
from app.services.dashboard_service import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard & Analytics"])


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get complete dashboard financial summary",
    description=(
        "Retrieves a unified financial analytics payload containing KPIs, month-over-month comparisons, "
        "budget utilization, category spending distribution, payment account distribution, "
        "daily spending trend series, and recent transactions."
    ),
)
def get_dashboard_summary(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    month: Optional[int] = Query(None, ge=1, le=12, description="Target month (defaults to current month)"),
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Target year (defaults to current year)"),
) -> DashboardSummaryResponse:
    return dashboard_service.get_summary(
        db=db,
        user=current_user,
        month=month,
        year=year,
    )
