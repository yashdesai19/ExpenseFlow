import datetime as dt
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.category import CategoryResponse


class ExpenseBase(BaseModel):
    amount: Decimal = Field(
        ...,
        gt=0,
        max_digits=12,
        decimal_places=2,
        description="Positive monetary transaction value",
    )
    description: str = Field(..., min_length=1, max_length=500, description="Short summary of the expense")
    category_id: int = Field(..., description="ID of the associated Category")
    account: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Payment account/method (e.g. Credit Card, Checking, Cash)",
    )
    date: dt.date = Field(..., description="Transaction date (YYYY-MM-DD)")
    notes: Optional[str] = Field(None, max_length=2000, description="Optional extra details or memo")


class ExpenseCreate(ExpenseBase):
    """Payload schema for logging a new expense."""
    recurring_expense_id: Optional[int] = None


class ExpenseUpdate(BaseModel):
    """Payload schema for partially updating an expense."""
    amount: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=2)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    category_id: Optional[int] = None
    account: Optional[str] = Field(None, min_length=1, max_length=100)
    date: Optional[dt.date] = None
    notes: Optional[str] = Field(None, max_length=2000)


class ExpenseResponse(ExpenseBase):
    """Full detail of an Expense entity returned to client."""
    id: int
    user_id: int
    recurring_expense_id: Optional[int]
    created_at: dt.datetime
    updated_at: dt.datetime
    category: Optional[CategoryResponse] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedExpenseResponse(BaseModel):
    """Standardized paginated list response schema."""
    items: List[ExpenseResponse]
    total: int = Field(..., description="Total matching items across all pages")
    page: int = Field(..., description="Current page number (1-indexed)")
    limit: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Calculated total number of pages")
    total_amount: Decimal = Field(..., description="Aggregated sum of all filtered expenses")
