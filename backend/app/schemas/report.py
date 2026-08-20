import datetime as dt
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field


class CategoryReportItem(BaseModel):
    category_id: int
    category_name: str
    color: str
    icon: str
    total_amount: Decimal
    percentage: float
    transaction_count: int


class AccountReportItem(BaseModel):
    account: str
    total_amount: Decimal
    percentage: float
    transaction_count: int


class MonthlyTrendItem(BaseModel):
    year: int
    month: int
    month_name: str
    total_amount: Decimal
    transaction_count: int


class SpendingReportResponse(BaseModel):
    """Structured financial report payload across a customized date range."""
    start_date: dt.date
    end_date: dt.date
    total_spent: Decimal
    transaction_count: int
    daily_average: Decimal
    category_breakdown: List[CategoryReportItem]
    account_breakdown: List[AccountReportItem]
    monthly_trends: List[MonthlyTrendItem]


class MonthlyTrendsResponse(BaseModel):
    """Historical multi-month spending trend series."""
    months_requested: int
    items: List[MonthlyTrendItem]
