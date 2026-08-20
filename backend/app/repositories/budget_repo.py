from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, extract

from app.models.budget import Budget
from app.models.expense import Expense


class BudgetRepository:
    """Data Access Layer for Budget management and spending tracking."""

    @staticmethod
    def get_by_id_and_user(db: Session, budget_id: int, user_id: int) -> Optional[Budget]:
        stmt = (
            select(Budget)
            .options(joinedload(Budget.category))
            .where(Budget.id == budget_id, Budget.user_id == user_id)
        )
        return db.scalars(stmt).first()

    @staticmethod
    def get_by_category_and_period(
        db: Session,
        user_id: int,
        category_id: int,
        month: int,
        year: int,
    ) -> Optional[Budget]:
        stmt = select(Budget).where(
            Budget.user_id == user_id,
            Budget.category_id == category_id,
            Budget.month == month,
            Budget.year == year,
        )
        return db.scalars(stmt).first()

    @staticmethod
    def list_for_user_and_period(
        db: Session,
        user_id: int,
        month: Optional[int] = None,
        year: Optional[int] = None,
    ) -> List[Budget]:
        stmt = (
            select(Budget)
            .options(joinedload(Budget.category))
            .where(Budget.user_id == user_id)
        )
        if month is not None:
            stmt = stmt.where(Budget.month == month)
        if year is not None:
            stmt = stmt.where(Budget.year == year)

        stmt = stmt.order_by(Budget.year.desc(), Budget.month.desc(), Budget.id.asc())
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_category_spent_for_month(
        db: Session,
        user_id: int,
        category_id: int,
        month: int,
        year: int,
    ) -> Decimal:
        """
        Calculates the exact total spent in a specific category for a given month and year
        using database-level SQL aggregation.
        """
        stmt = select(
            func.coalesce(func.sum(Expense.amount), Decimal("0.00"))
        ).where(
            Expense.user_id == user_id,
            Expense.category_id == category_id,
            extract("month", Expense.date) == month,
            extract("year", Expense.date) == year,
        )
        return db.scalar(stmt) or Decimal("0.00")

    @staticmethod
    def create(
        db: Session,
        user_id: int,
        category_id: int,
        amount: Decimal,
        month: int,
        year: int,
    ) -> Budget:
        budget = Budget(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
            month=month,
            year=year,
        )
        db.add(budget)
        db.commit()
        db.refresh(budget)
        return budget

    @staticmethod
    def update(db: Session, budget: Budget, amount: Decimal) -> Budget:
        budget.amount = amount
        db.commit()
        db.refresh(budget)
        return budget

    @staticmethod
    def delete(db: Session, budget: Budget) -> None:
        db.delete(budget)
        db.commit()


budget_repo = BudgetRepository()
