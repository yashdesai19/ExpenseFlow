import calendar
import datetime as dt
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.report import (
    SpendingReportResponse,
    MonthlyTrendsResponse,
    CategoryReportItem,
    AccountReportItem,
    MonthlyTrendItem,
)
from app.repositories.report_repo import report_repo


class ReportService:
    """Service layer synthesizing multi-dimensional financial reports."""

    @staticmethod
    def get_spending_report(
        db: Session,
        user: User,
        start_date: dt.date,
        end_date: dt.date,
        category_id: Optional[int] = None,
        account: Optional[str] = None,
    ) -> SpendingReportResponse:
        # 1. Total and Count
        total_spent, tx_count = report_repo.get_spending_summary(
            db, user_id=user.id, start_date=start_date, end_date=end_date,
            category_id=category_id, account=account,
        )

        # 2. Daily Average
        days_in_period = max(1, (end_date - start_date).days + 1)
        daily_average = total_spent / Decimal(str(days_in_period))

        # 3. Category Breakdown
        cat_rows = report_repo.get_category_report(
            db, user_id=user.id, start_date=start_date, end_date=end_date, account=account
        )
        cat_items = []
        for cat_id, cat_name, cat_color, cat_icon, amt, count in cat_rows:
            pct = float(amt / total_spent * 100) if total_spent > Decimal("0.00") else 0.0
            cat_items.append(
                CategoryReportItem(
                    category_id=cat_id,
                    category_name=cat_name,
                    color=cat_color,
                    icon=cat_icon,
                    total_amount=amt,
                    percentage=round(pct, 2),
                    transaction_count=count,
                )
            )

        # 4. Account Breakdown
        acc_rows = report_repo.get_account_report(
            db, user_id=user.id, start_date=start_date, end_date=end_date, category_id=category_id
        )
        acc_items = []
        for acc_name, amt, count in acc_rows:
            pct = float(amt / total_spent * 100) if total_spent > Decimal("0.00") else 0.0
            acc_items.append(
                AccountReportItem(
                    account=acc_name,
                    total_amount=amt,
                    percentage=round(pct, 2),
                    transaction_count=count,
                )
            )

        # 5. Monthly Breakdown in Period
        mo_rows = report_repo.get_monthly_breakdown_in_range(
            db, user_id=user.id, start_date=start_date, end_date=end_date
        )
        monthly_items = [
            MonthlyTrendItem(
                year=yr,
                month=mo,
                month_name=calendar.month_name[mo],
                total_amount=amt,
                transaction_count=cnt,
            )
            for yr, mo, amt, cnt in mo_rows
        ]

        return SpendingReportResponse(
            start_date=start_date,
            end_date=end_date,
            total_spent=total_spent,
            transaction_count=tx_count,
            daily_average=round(daily_average, 2),
            category_breakdown=cat_items,
            account_breakdown=acc_items,
            monthly_trends=monthly_items,
        )

    @staticmethod
    def get_monthly_trends(
        db: Session,
        user: User,
        months: int = 6,
    ) -> MonthlyTrendsResponse:
        months_clamped = min(max(1, months), 36)
        raw_trends = report_repo.get_monthly_trends_history(
            db, user_id=user.id, months_count=months_clamped
        )
        items = [
            MonthlyTrendItem(
                year=yr,
                month=mo,
                month_name=calendar.month_name[mo],
                total_amount=amt,
                transaction_count=cnt,
            )
            for yr, mo, amt, cnt in raw_trends
        ]
        return MonthlyTrendsResponse(months_requested=months_clamped, items=items)


report_service = ReportService()
