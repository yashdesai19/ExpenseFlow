from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, func, or_, desc, asc

from app.models.expense import Expense


class ExpenseRepository:
    """Data Access Layer for Expense entities with optimized query execution."""

    @staticmethod
    def get_by_id_and_user(db: Session, expense_id: int, user_id: int) -> Optional[Expense]:
        """
        Fetch a single expense by ID, guaranteeing ownership by user_id
        and eagerly loading the related Category.
        """
        stmt = (
            select(Expense)
            .options(joinedload(Expense.category))
            .where(Expense.id == expense_id, Expense.user_id == user_id)
        )
        return db.scalars(stmt).first()

    @staticmethod
    def list_paginated(
        db: Session,
        user_id: int,
        page: int = 1,
        limit: int = 20,
        category_id: Optional[int] = None,
        account: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        min_amount: Optional[Decimal] = None,
        max_amount: Optional[Decimal] = None,
        search: Optional[str] = None,
        sort_by: str = "date",
        order: str = "desc",
    ) -> Tuple[List[Expense], int, Decimal]:
        """
        Retrieves paginated expenses with dynamic filters, search, and aggregates.
        Returns: (items, total_count, total_amount_sum)
        """
        # Base query filtered strictly by user_id
        base_filters = [Expense.user_id == user_id]

        if category_id is not None:
            base_filters.append(Expense.category_id == category_id)
        if account is not None:
            base_filters.append(Expense.account.ilike(f"%{account.strip()}%"))
        if start_date is not None:
            base_filters.append(Expense.date >= start_date)
        if end_date is not None:
            base_filters.append(Expense.date <= end_date)
        if min_amount is not None:
            base_filters.append(Expense.amount >= min_amount)
        if max_amount is not None:
            base_filters.append(Expense.amount <= max_amount)
        if search:
            search_pattern = f"%{search.strip()}%"
            base_filters.append(
                or_(
                    Expense.description.ilike(search_pattern),
                    Expense.notes.ilike(search_pattern),
                )
            )

        # 1. Calculate Total Count and Total Sum in single/fast SQL aggregation
        count_stmt = select(func.count(Expense.id)).where(*base_filters)
        total_count = db.scalar(count_stmt) or 0

        sum_stmt = select(func.coalesce(func.sum(Expense.amount), Decimal("0.00"))).where(*base_filters)
        total_sum = db.scalar(sum_stmt) or Decimal("0.00")

        # 2. Configure Dynamic Sorting
        sort_column = getattr(Expense, sort_by, Expense.date)
        sort_clause = desc(sort_column) if order.lower() == "desc" else asc(sort_column)

        # 3. Retrieve Paginated Results with joinedload
        offset = (page - 1) * limit
        query_stmt = (
            select(Expense)
            .options(joinedload(Expense.category))
            .where(*base_filters)
            .order_by(sort_clause, desc(Expense.id))
            .offset(offset)
            .limit(limit)
        )
        items = list(db.scalars(query_stmt).all())

        return items, total_count, total_sum

    @staticmethod
    def create(
        db: Session,
        user_id: int,
        category_id: int,
        amount: Decimal,
        description: str,
        account: str,
        date: date,
        notes: Optional[str] = None,
        recurring_expense_id: Optional[int] = None,
    ) -> Expense:
        """Persist a new expense record to the database."""
        expense = Expense(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
            description=description.strip(),
            account=account.strip(),
            date=date,
            notes=notes.strip() if notes else None,
            recurring_expense_id=recurring_expense_id,
        )
        db.add(expense)
        db.commit()
        db.refresh(expense)
        return expense

    @staticmethod
    def update(
        db: Session,
        expense: Expense,
        amount: Optional[Decimal] = None,
        description: Optional[str] = None,
        category_id: Optional[int] = None,
        account: Optional[str] = None,
        date: Optional[date] = None,
        notes: Optional[str] = None,
    ) -> Expense:
        """Apply partial updates to an existing expense."""
        if amount is not None:
            expense.amount = amount
        if description is not None:
            expense.description = description.strip()
        if category_id is not None:
            expense.category_id = category_id
        if account is not None:
            expense.account = account.strip()
        if date is not None:
            expense.date = date
        if notes is not None:
            expense.notes = notes.strip() if notes else None

        db.commit()
        db.refresh(expense)
        return expense

    @staticmethod
    def delete(db: Session, expense: Expense) -> None:
        """Delete an expense record."""
        db.delete(expense)
        db.commit()


expense_repo = ExpenseRepository()
