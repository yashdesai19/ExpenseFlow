from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.expense import Expense
    from app.models.budget import Budget
    from app.models.recurring import RecurringExpense


class Category(Base, TimestampMixin):
    """
    Category model for organizing expenses and budgets.
    Supports system-wide default categories (user_id=None) and user-custom categories.
    """
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="#3B82F6", nullable=False)  # Hex color code
    icon: Mapped[str] = mapped_column(String(50), default="tag", nullable=False)       # Icon name/class
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # --------------------------------------------------------------------------
    # Relationships
    # --------------------------------------------------------------------------
    user: Mapped[Optional["User"]] = relationship("User", back_populates="categories")
    expenses: Mapped[List["Expense"]] = relationship("Expense", back_populates="category")
    budgets: Mapped[List["Budget"]] = relationship("Budget", back_populates="category")
    recurring_expenses: Mapped[List["RecurringExpense"]] = relationship(
        "RecurringExpense", back_populates="category"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_user_category_name"),
    )
