import datetime as dt
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.schemas.category import CategoryResponse


class BudgetBase(BaseModel):
    category_id: int = Field(..., description="ID of category to allocate budget for")
    amount: Decimal = Field(
        ...,
        gt=0,
        max_digits=12,
        decimal_places=2,
        description="Budget ceiling amount for the period",
    )
    month: int = Field(
        default_factory=lambda: dt.datetime.now().month,
        ge=1,
        le=12,
        description="Month (1-12)",
    )
    year: int = Field(
        default_factory=lambda: dt.datetime.now().year,
        ge=2000,
        le=2100,
        description="Four-digit year (e.g. 2026)",
    )


class BudgetCreate(BudgetBase):
    """Payload schema for creating a new monthly budget."""
    pass


class BudgetUpdate(BaseModel):
    """Payload schema for updating budget amount."""
    amount: Optional[Decimal] = Field(None, gt=0, max_digits=12, decimal_places=2)


class BudgetResponse(BudgetBase):
    """Basic representation of a Budget entity."""
    id: int
    user_id: int
    created_at: dt.datetime
    category: Optional[CategoryResponse] = None

    model_config = ConfigDict(from_attributes=True)


class BudgetUtilizationResponse(BudgetResponse):
    """
    Enhanced budget representation with real-time calculations
    derived from actual historical and current expense records.
    """
    spent_amount: Decimal = Field(..., description="Total actual spending in this category for the month")
    remaining_amount: Decimal = Field(..., description="Unused budget balance (can be negative if over budget)")
    percentage_used: float = Field(..., description="Utilization percentage (e.g. 75.5%)")
    status: str = Field(..., description="Budget status: 'UNDER_BUDGET', 'WARNING_80_PERCENT', or 'EXCEEDED'")
