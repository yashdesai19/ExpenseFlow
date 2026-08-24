import datetime as dt
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.category import CategoryResponse


class RecurringExpenseBase(BaseModel):
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="Recurring expense amount")
    description: str = Field(..., min_length=1, max_length=500, description="Subscription or recurring charge description")
    category_id: int = Field(..., description="Target category ID")
    account: str = Field(..., min_length=1, max_length=100, description="Payment method / account")
    frequency: str = Field(
        ...,
        pattern="^(DAILY|WEEKLY|MONTHLY|YEARLY)$",
        description="Recurrence interval: 'DAILY', 'WEEKLY', 'MONTHLY', or 'YEARLY'",
    )
    start_date: dt.date = Field(..., description="Start date of the schedule")
    end_date: Optional[dt.date] = Field(None, description="Optional cancellation or termination date")


class RecurringExpenseCreate(RecurringExpenseBase):
    """Payload schema for creating a new recurring schedule."""
    next_due_date: Optional[dt.date] = Field(
        None,
        description="Optional custom first due date (defaults to start_date if omitted)",
    )


class RecurringExpenseUpdate(BaseModel):
    """Payload schema for updating a recurring rule."""
    amount: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=2)
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    category_id: Optional[int] = None
    account: Optional[str] = Field(None, min_length=1, max_length=100)
    frequency: Optional[str] = Field(None, pattern="^(DAILY|WEEKLY|MONTHLY|YEARLY)$")
    end_date: Optional[dt.date] = None
    next_due_date: Optional[dt.date] = None
    is_active: Optional[bool] = None


class RecurringExpenseResponse(RecurringExpenseBase):
    """Public representation of a Recurring Expense schedule."""
    id: int
    user_id: int
    next_due_date: dt.date
    is_active: bool
    created_at: dt.datetime
    updated_at: dt.datetime | None = None
    category: Optional[CategoryResponse] = None

    model_config = ConfigDict(from_attributes=True)


class ProcessRecurringResponse(BaseModel):
    """Result of automated batch or manual recurring expense generation."""
    processed_schedules: int = Field(..., description="Number of active recurring rules inspected")
    generated_expenses_count: int = Field(..., description="Number of new expense records created")
    generated_expense_ids: List[int] = Field(..., description="List of generated expense primary keys")
    message: str
