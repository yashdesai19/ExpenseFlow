from datetime import date
from decimal import Decimal
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Numeric, Date, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.category import Category
    from app.models.expense import Expense


class RecurringExpense(Base, TimestampMixin):
    """
    Template schedule for automatically or semi-automatically recurring expenses
    (e.g., Monthly Rent, Spotify Subscription, Annual Insurance).
    """
    __tablename__ = "recurring_expenses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    account: Mapped[str] = mapped_column(String(100), nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)  # DAILY, WEEKLY, MONTHLY, YEARLY
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    next_due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # --------------------------------------------------------------------------
    # Relationships
    # --------------------------------------------------------------------------
    user: Mapped["User"] = relationship("User", back_populates="recurring_expenses")
    category: Mapped["Category"] = relationship("Category", back_populates="recurring_expenses")
    generated_expenses: Mapped[List["Expense"]] = relationship(
        "Expense", back_populates="recurring_expense"
    )
