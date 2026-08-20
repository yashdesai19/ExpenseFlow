from decimal import Decimal
from typing import List
from pydantic import BaseModel, Field
from app.schemas.expense import ExpenseResponse


class CategorySpendingStat(BaseModel):
    category_id: int
    category_name: str
    color: str
    icon: str
    total_amount: Decimal
    percentage_of_total: float = Field(..., description="Percentage of total monthly spend (0-100%)")


class AccountSpendingStat(BaseModel):
    account: str
    total_amount: Decimal
    transaction_count: int


class DailySpendingStat(BaseModel):
    date: str = Field(..., description="Date formatted as YYYY-MM-DD")
    amount: Decimal


class DashboardKPIs(BaseModel):
    total_spent_this_month: Decimal
    total_spent_last_month: Decimal
    month_over_month_change_pct: float = Field(
        ...,
        description="Percentage change compared to previous month (+/- %)",
    )
    total_budget_allocated: Decimal
    total_budget_spent: Decimal
    total_budget_remaining: Decimal
    budget_utilization_pct: float
    transaction_count: int


class DashboardSummaryResponse(BaseModel):
    """
    Consolidated payload powering the entire frontend dashboard with a single API call.
    """
    month: int
    year: int
    kpis: DashboardKPIs
    category_breakdown: List[CategorySpendingStat]
    account_breakdown: List[AccountSpendingStat]
    daily_trends: List[DailySpendingStat]
    recent_expenses: List[ExpenseResponse]
