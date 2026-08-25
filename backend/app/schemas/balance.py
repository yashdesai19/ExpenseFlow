from decimal import Decimal
from typing import List, Dict
from pydantic import BaseModel, Field


class MemberBalanceSummary(BaseModel):
    user_id: int
    full_name: str
    email: str
    total_paid: Decimal = Field(..., description="Total amount paid by this member (expenses + settlements payer)")
    total_owed: Decimal = Field(..., description="Total amount owed by this member (shares + settlements receiver)")
    net_balance: Decimal = Field(..., description="Net balance (total_paid - total_owed). Positive means they get back money.")


class SimplifiedDebt(BaseModel):
    from_user_id: int
    from_user_name: str
    to_user_id: int
    to_user_name: str
    amount: Decimal = Field(..., description="Simplified settlement amount")


class GroupBalanceResponse(BaseModel):
    group_id: int
    total_expenses: Decimal = Field(..., description="Total expenses in the group")
    balances: List[MemberBalanceSummary] = Field(..., description="Balance sheet per member")
    simplified_debts: List[SimplifiedDebt] = Field(..., description="Simplified settlement transactions")
