import datetime as dt
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.report import SpendingReportResponse, MonthlyTrendsResponse
from app.services.report_service import report_service

router = APIRouter(prefix="/reports", tags=["Reports & Analytics"])


@router.get(
    "/spending",
    response_model=SpendingReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get detailed date-range spending report",
    description="Generates an in-depth financial summary, daily average, category and account breakdown, and period monthly trends.",
)
def get_spending_report(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    start_date: dt.date = Query(
        default_factory=lambda: dt.date.today().replace(day=1),
        description="Start date of report period (default: 1st day of current month)",
    ),
    end_date: dt.date = Query(
        default_factory=lambda: dt.date.today(),
        description="End date of report period (default: today)",
    ),
    category_id: Optional[int] = Query(None, description="Optional category filter"),
    account: Optional[str] = Query(None, description="Optional account filter"),
) -> SpendingReportResponse:
    return report_service.get_spending_report(
        db=db,
        user=current_user,
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        account=account,
    )


@router.get(
    "/monthly-trends",
    response_model=MonthlyTrendsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get multi-month spending trend series",
    description="Returns chronological monthly spending totals and transaction counts for chart visualization.",
)
def get_monthly_trends(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    months: int = Query(6, ge=1, le=36, description="Number of past months to include"),
) -> MonthlyTrendsResponse:
    return report_service.get_monthly_trends(
        db=db,
        user=current_user,
        months=months,
    )
