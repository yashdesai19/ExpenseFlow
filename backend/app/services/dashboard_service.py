import datetime as dt
from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.expense import ExpenseResponse
from app.schemas.dashboard import (
    DashboardSummaryResponse,
    DashboardKPIs,
    CategorySpendingStat,
    AccountSpendingStat,
    DailySpendingStat,
)
from app.repositories.dashboard_repo import dashboard_repo


class DashboardService:
    """Service layer aggregating high-level financial analytics and trends for the dashboard."""

    @staticmethod
    def get_summary(
        db: Session,
        user: User,
        month: Optional[int] = None,
        year: Optional[int] = None,
    ) -> DashboardSummaryResponse:
        today = dt.date.today()
        target_month = month if month is not None else today.month
        target_year = year if year is not None else today.year

        # 1. Calculate Previous Month & Year for Comparison
        if target_month == 1:
            prev_month = 12
            prev_year = target_year - 1
        else:
            prev_month = target_month - 1
            prev_year = target_year

        # 2. Fetch Aggregated Metrics from Database
        this_month_spent, tx_count = dashboard_repo.get_monthly_total(
            db, user_id=user.id, month=target_month, year=target_year
        )
        last_month_spent, _ = dashboard_repo.get_monthly_total(
            db, user_id=user.id, month=prev_month, year=prev_year
        )

        # 3. Compute Month-over-Month Percentage Change
        if last_month_spent > Decimal("0.00"):
            change_pct = float((this_month_spent - last_month_spent) / last_month_spent * 100)
        else:
            change_pct = 100.0 if this_month_spent > Decimal("0.00") else 0.0

        # 4. Fetch Total Budget Allocation
        total_budget = dashboard_repo.get_budget_totals(
            db, user_id=user.id, month=target_month, year=target_year
        )
        budget_remaining = total_budget - this_month_spent
        budget_pct = (
            float(this_month_spent / total_budget * 100) if total_budget > Decimal("0.00") else 0.0
        )

        # 5. Category Breakdown with Share Percentages
        category_rows = dashboard_repo.get_category_breakdown(
            db, user_id=user.id, month=target_month, year=target_year
        )
        categories_stat = []
        for cat_id, cat_name, cat_color, cat_icon, total_amt in category_rows:
            cat_pct = (
                float(total_amt / this_month_spent * 100) if this_month_spent > Decimal("0.00") else 0.0
            )
            categories_stat.append(
                CategorySpendingStat(
                    category_id=cat_id,
                    category_name=cat_name,
                    color=cat_color,
                    icon=cat_icon,
                    total_amount=total_amt,
                    percentage_of_total=round(cat_pct, 2),
                )
            )

        # 6. Account Breakdown
        account_rows = dashboard_repo.get_account_breakdown(
            db, user_id=user.id, month=target_month, year=target_year
        )
        accounts_stat = [
            AccountSpendingStat(account=acc, total_amount=tot, transaction_count=cnt)
            for acc, tot, cnt in account_rows
        ]

        # 7. Daily Spending Trends
        daily_rows = dashboard_repo.get_daily_trends(
            db, user_id=user.id, month=target_month, year=target_year
        )
        daily_stat = [DailySpendingStat(date=d, amount=amt) for d, amt in daily_rows]

        # 8. Top 5 Recent Expenses
        recent_expenses = dashboard_repo.get_recent_expenses(db, user_id=user.id, limit=5)

        kpis = DashboardKPIs(
            total_spent_this_month=this_month_spent,
            total_spent_last_month=last_month_spent,
            month_over_month_change_pct=round(change_pct, 2),
            total_budget_allocated=total_budget,
            total_budget_spent=this_month_spent,
            total_budget_remaining=budget_remaining,
            budget_utilization_pct=round(budget_pct, 2),
            transaction_count=tx_count,
        )

        return DashboardSummaryResponse(
            month=target_month,
            year=target_year,
            kpis=kpis,
            category_breakdown=categories_stat,
            account_breakdown=accounts_stat,
            daily_trends=daily_stat,
            recent_expenses=[ExpenseResponse.model_validate(e) for e in recent_expenses],
        )


dashboard_service = DashboardService()
