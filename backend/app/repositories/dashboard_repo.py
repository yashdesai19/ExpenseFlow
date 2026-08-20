from decimal import Decimal
from typing import List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, extract, desc

from app.models.expense import Expense
from app.models.category import Category
from app.models.budget import Budget


class DashboardRepository:
    """High-performance analytical repository using SQL GROUP BY aggregations."""

    @staticmethod
    def get_monthly_total(db: Session, user_id: int, month: int, year: int) -> Tuple[Decimal, int]:
        """Returns (total_amount_sum, transaction_count) for a specific month/year."""
        stmt = select(
            func.coalesce(func.sum(Expense.amount), Decimal("0.00")),
            func.count(Expense.id),
        ).where(
            Expense.user_id == user_id,
            extract("month", Expense.date) == month,
            extract("year", Expense.date) == year,
        )
        result = db.execute(stmt).first()
        if result:
            return result[0], result[1]
        return Decimal("0.00"), 0

    @staticmethod
    def get_category_breakdown(
        db: Session,
        user_id: int,
        month: int,
        year: int,
    ) -> List[Tuple[int, str, str, str, Decimal]]:
        """
        Executes a high-speed SQL GROUP BY join:
        Returns: [(category_id, name, color, icon, total_amount), ...]
        """
        stmt = (
            select(
                Category.id,
                Category.name,
                Category.color,
                Category.icon,
                func.coalesce(func.sum(Expense.amount), Decimal("0.00")).label("total_amount"),
            )
            .join(Expense, Expense.category_id == Category.id)
            .where(
                Expense.user_id == user_id,
                extract("month", Expense.date) == month,
                extract("year", Expense.date) == year,
            )
            .group_by(Category.id, Category.name, Category.color, Category.icon)
            .order_by(desc("total_amount"))
        )
        return list(db.execute(stmt).all())  # type: ignore

    @staticmethod
    def get_account_breakdown(
        db: Session,
        user_id: int,
        month: int,
        year: int,
    ) -> List[Tuple[str, Decimal, int]]:
        """
        Executes GROUP BY account:
        Returns: [(account_name, total_amount, transaction_count), ...]
        """
        stmt = (
            select(
                Expense.account,
                func.coalesce(func.sum(Expense.amount), Decimal("0.00")).label("total_amount"),
                func.count(Expense.id).label("tx_count"),
            )
            .where(
                Expense.user_id == user_id,
                extract("month", Expense.date) == month,
                extract("year", Expense.date) == year,
            )
            .group_by(Expense.account)
            .order_by(desc("total_amount"))
        )
        return list(db.execute(stmt).all())  # type: ignore

    @staticmethod
    def get_daily_trends(
        db: Session,
        user_id: int,
        month: int,
        year: int,
    ) -> List[Tuple[str, Decimal]]:
        """
        Calculates daily spending trend for charts:
        Returns: [(date_string, total_amount), ...]
        """
        stmt = (
            select(
                Expense.date,
                func.coalesce(func.sum(Expense.amount), Decimal("0.00")).label("total_amount"),
            )
            .where(
                Expense.user_id == user_id,
                extract("month", Expense.date) == month,
                extract("year", Expense.date) == year,
            )
            .group_by(Expense.date)
            .order_by(Expense.date.asc())
        )
        results = db.execute(stmt).all()
        return [(str(row[0]), row[1]) for row in results]

    @staticmethod
    def get_budget_totals(db: Session, user_id: int, month: int, year: int) -> Decimal:
        """Returns total budget allocated for that month/year."""
        stmt = select(
            func.coalesce(func.sum(Budget.amount), Decimal("0.00"))
        ).where(
            Budget.user_id == user_id,
            Budget.month == month,
            Budget.year == year,
        )
        return db.scalar(stmt) or Decimal("0.00")

    @staticmethod
    def get_recent_expenses(db: Session, user_id: int, limit: int = 5) -> List[Expense]:
        """Retrieves top N latest expenses with category details."""
        stmt = (
            select(Expense)
            .options(joinedload(Expense.category))
            .where(Expense.user_id == user_id)
            .order_by(desc(Expense.date), desc(Expense.id))
            .limit(limit)
        )
        return list(db.scalars(stmt).all())


dashboard_repo = DashboardRepository()
