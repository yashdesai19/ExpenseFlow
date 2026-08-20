from decimal import Decimal
from typing import TYPE_CHECKING
from sqlalchemy import Numeric, Integer, ForeignKey, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.category import Category


class Budget(Base, TimestampMixin):
    """
    Monthly category budget target set by a user.
    """
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 to 12
    year: Mapped[int] = mapped_column(Integer, nullable=False)   # e.g., 2026

    # --------------------------------------------------------------------------
    # Relationships
    # --------------------------------------------------------------------------
    user: Mapped["User"] = relationship("User", back_populates="budgets")
    category: Mapped["Category"] = relationship("Category", back_populates="budgets")

    __table_args__ = (
        UniqueConstraint("user_id", "category_id", "month", "year", name="uq_user_category_month_year_budget"),
        Index("ix_budgets_user_period", "user_id", "year", "month"),
    )
