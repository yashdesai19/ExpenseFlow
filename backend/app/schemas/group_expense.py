import datetime as dt
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator
from app.schemas.category import CategoryResponse


class GroupExpensePaymentCreate(BaseModel):
    user_id: int = Field(..., description="ID of the user who paid")
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="Amount paid by the user")


class GroupExpenseParticipantCreate(BaseModel):
    user_id: int = Field(..., description="ID of the user who participated")
    share_value: Decimal = Field(..., ge=0, max_digits=12, decimal_places=2, description="Target split ratio/value for this user")


class GroupExpensePaymentResponse(BaseModel):
    user_id: int
    full_name: str
    email: str
    amount: Decimal

    model_config = ConfigDict(from_attributes=True)


class GroupExpenseParticipantResponse(BaseModel):
    user_id: int
    full_name: str
    email: str
    share_value: Decimal
    calculated_amount: Decimal

    model_config = ConfigDict(from_attributes=True)


class GroupExpenseCreate(BaseModel):
    category_id: int = Field(..., description="Category ID for the expense")
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="Total amount of the group expense")
    description: str = Field(..., min_length=1, max_length=255, description="Short summary of the expense")
    date: dt.date = Field(..., description="Transaction date (YYYY-MM-DD)")
    notes: Optional[str] = Field(None, max_length=2000, description="Optional notes")
    split_method: str = Field("equal", pattern="^(equal|exact|percentage|shares)$", description="Algorithm to split the expense")
    payments: List[GroupExpensePaymentCreate] = Field(..., min_length=1, description="List of payments specifying who paid how much")
    participants: List[GroupExpenseParticipantCreate] = Field(..., min_length=1, description="List of participants specifying who owes what")

    @model_validator(mode="after")
    def validate_payments_and_splits(self):
        # 1. Verify sum of payments equals total amount
        total_paid = sum(p.amount for p in self.payments)
        if abs(total_paid - self.amount) > Decimal("0.01"):
            raise ValueError(f"Sum of payments ({total_paid}) must equal the total expense amount ({self.amount}).")

        # 2. Split-method specific validations
        if self.split_method == "exact":
            total_split = sum(p.share_value for p in self.participants)
            if abs(total_split - self.amount) > Decimal("0.01"):
                raise ValueError(f"For exact splits, the sum of shares ({total_split}) must equal the total expense amount ({self.amount}).")
        
        elif self.split_method == "percentage":
            total_pct = sum(p.share_value for p in self.participants)
            if abs(total_pct - Decimal("100.00")) > Decimal("0.01"):
                raise ValueError(f"For percentage splits, the sum of percentages ({total_pct}%) must equal exactly 100%.")

        elif self.split_method == "shares":
            total_shares = sum(p.share_value for p in self.participants)
            if total_shares <= 0:
                raise ValueError("For shares splits, the sum of shares must be greater than 0.")

        return self


class GroupExpenseResponse(BaseModel):
    id: int
    group_id: int
    created_by_id: Optional[int]
    category_id: int
    amount: Decimal
    description: str
    date: dt.date
    notes: Optional[str]
    split_method: str
    created_at: dt.datetime
    updated_at: dt.datetime
    category: Optional[CategoryResponse] = None
    payments: List[GroupExpensePaymentResponse]
    participants: List[GroupExpenseParticipantResponse]

    model_config = ConfigDict(from_attributes=True)
