import calendar
import datetime as dt
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, extract, desc, asc

from app.models.expense import Expense
from app.models.category import Category


class ReportRepository:
    """Analytical repository powering deep financial reports and trend analytics."""

    @staticmethod
    def get_spending_summary(
        db: Session,
        user_id: int,
        start_date: dt.date,
        end_date: dt.date,
        category_id: Optional[int] = None,
        account: Optional[str] = None,
    ) -> Tuple[Decimal, int]:
        filters = [
            Expense.user_id == user_id,
            Expense.date >= start_date,
            Expense.date <= end_date,
        ]
        if category_id is not None:
            filters.append(Expense.category_id == category_id)
        if account is not None:
            filters.append(Expense.account.ilike(f"%{account.strip()}%"))

        stmt = select(
            func.coalesce(func.sum(Expense.amount), Decimal("0.00")),
            func.count(Expense.id),
        ).where(*filters)

        result = db.execute(stmt).first()
        if result:
            return result[0], result[1]
        return Decimal("0.00"), 0

    @staticmethod
    def get_category_report(
        db: Session,
        user_id: int,
        start_date: dt.date,
        end_date: dt.date,
        account: Optional[str] = None,
    ) -> List[Tuple[int, str, str, str, Decimal, int]]:
        """Returns [(category_id, name, color, icon, total_amount, transaction_count), ...]"""
        filters = [
            Expense.user_id == user_id,
            Expense.date >= start_date,
            Expense.date <= end_date,
        ]
        if account is not None:
            filters.append(Expense.account.ilike(f"%{account.strip()}%"))

        stmt = (
            select(
                Category.id,
                Category.name,
                Category.color,
                Category.icon,
                func.coalesce(func.sum(Expense.amount), Decimal("0.00")).label("total_amount"),
                func.count(Expense.id).label("tx_count"),
            )
            .join(Expense, Expense.category_id == Category.id)
            .where(*filters)
            .group_by(Category.id, Category.name, Category.color, Category.icon)
            .order_by(desc("total_amount"))
        )
        return list(db.execute(stmt).all())  # type: ignore

    @staticmethod
    def get_account_report(
        db: Session,
        user_id: int,
        start_date: dt.date,
        end_date: dt.date,
        category_id: Optional[int] = None,
    ) -> List[Tuple[str, Decimal, int]]:
        """Returns [(account_name, total_amount, transaction_count), ...]"""
        filters = [
            Expense.user_id == user_id,
            Expense.date >= start_date,
            Expense.date <= end_date,
        ]
        if category_id is not None:
            filters.append(Expense.category_id == category_id)

        stmt = (
            select(
                Expense.account,
                func.coalesce(func.sum(Expense.amount), Decimal("0.00")).label("total_amount"),
                func.count(Expense.id).label("tx_count"),
            )
            .where(*filters)
            .group_by(Expense.account)
            .order_by(desc("total_amount"))
        )
        return list(db.execute(stmt).all())  # type: ignore

    @staticmethod
    def get_monthly_breakdown_in_range(
        db: Session,
        user_id: int,
        start_date: dt.date,
        end_date: dt.date,
    ) -> List[Tuple[int, int, Decimal, int]]:
        """Returns [(year, month, total_amount, transaction_count), ...]"""
        year_col = extract("year", Expense.date).label("exp_year")
        month_col = extract("month", Expense.date).label("exp_month")

        stmt = (
            select(
                year_col,
                month_col,
                func.coalesce(func.sum(Expense.amount), Decimal("0.00")).label("total_amount"),
                func.count(Expense.id).label("tx_count"),
            )
            .where(
                Expense.user_id == user_id,
                Expense.date >= start_date,
                Expense.date <= end_date,
            )
            .group_by(year_col, month_col)
            .order_by(asc(year_col), asc(month_col))
        )
        return [(int(r[0]), int(r[1]), r[2], r[3]) for r in db.execute(stmt).all()]

    @staticmethod
    def get_monthly_trends_history(
        db: Session,
        user_id: int,
        months_count: int = 6,
    ) -> List[Tuple[int, int, Decimal, int]]:
        """Calculates spending totals for the past N calendar months."""
        now = dt.date.today()
        # Compute start date N-1 months ago on the 1st of that month
        # Generate list of (year, month) tuples
        periods = []
        cur_year, cur_month = now.year, now.month
        for _ in range(months_count):
            periods.append((cur_year, cur_month))
            cur_month -= 1
            if cur_month == 0:
                cur_month = 12
                cur_year -= 1

        periods.reverse()  # Chronological order
        start_year, start_month = periods[0]
        start_date = dt.date(start_year, start_month, 1)

        year_col = extract("year", Expense.date).label("exp_year")
        month_col = extract("month", Expense.date).label("exp_month")

        stmt = (
            select(
                year_col,
                month_col,
                func.coalesce(func.sum(Expense.amount), Decimal("0.00")).label("total_amount"),
                func.count(Expense.id).label("tx_count"),
            )
            .where(
                Expense.user_id == user_id,
                Expense.date >= start_date,
            )
            .group_by(year_col, month_col)
        )
        results_map = {(int(r[0]), int(r[1])): (r[2], r[3]) for r in db.execute(stmt).all()}

        # Fill in zero-spend months to guarantee continuous trend series
        output = []
        for yr, mo in periods:
            amt, count = results_map.get((yr, mo), (Decimal("0.00"), 0))
            output.append((yr, mo, amt, count))

        return output


report_repo = ReportRepository()
