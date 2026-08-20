from datetime import date
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Text, Numeric, Date, Integer, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.category import Category
    from app.models.recurring import RecurringExpense


class Expense(Base, TimestampMixin):
    """
    Core Expense entity tracking monetary outflows per user.
    """
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    recurring_expense_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("recurring_expenses.id", ondelete="SET NULL"), nullable=True, index=True
    )

    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    account: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Credit Card", "Cash", "Checking"
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # --------------------------------------------------------------------------
    # Relationships
    # --------------------------------------------------------------------------
    user: Mapped["User"] = relationship("User", back_populates="expenses")
    category: Mapped["Category"] = relationship("Category", back_populates="expenses")
    recurring_expense: Mapped[Optional["RecurringExpense"]] = relationship(
        "RecurringExpense", back_populates="generated_expenses"
    )

    __table_args__ = (
        Index("ix_expenses_user_date", "user_id", "date"),
        Index("ix_expenses_user_category", "user_id", "category_id"),
        Index("ix_expenses_user_account", "user_id", "account"),
    )
