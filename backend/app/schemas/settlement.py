import datetime as dt
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class GroupSettlementCreate(BaseModel):
    payer_id: int = Field(..., description="ID of the user who paid/settled")
    receiver_id: int = Field(..., description="ID of the user who received the payment")
    amount: Decimal = Field(..., gt=0, max_digits=12, decimal_places=2, description="Settlement payment amount")
    date: dt.date = Field(..., description="Payment date (YYYY-MM-DD)")
    notes: Optional[str] = Field(None, max_length=500, description="Optional description/notes for the settlement")


class GroupSettlementResponse(BaseModel):
    id: int
    group_id: int
    payer_id: int
    receiver_id: int
    amount: Decimal
    date: dt.date
    notes: Optional[str]
    created_by_id: Optional[int]
    created_at: dt.datetime
    updated_at: dt.datetime
    payer_name: str
    payer_email: str
    receiver_name: str
    receiver_email: str

    model_config = ConfigDict(from_attributes=True)
