import datetime as dt
from decimal import Decimal
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, and_

from app.models.recurring import RecurringExpense


class RecurringRepository:
    """Data Access Layer for Recurring Expense schedules."""

    @staticmethod
    def get_by_id_and_user(db: Session, recurring_id: int, user_id: int) -> Optional[RecurringExpense]:
        stmt = (
            select(RecurringExpense)
            .options(joinedload(RecurringExpense.category))
            .where(RecurringExpense.id == recurring_id, RecurringExpense.user_id == user_id)
        )
        return db.scalars(stmt).first()

    @staticmethod
    def list_for_user(
        db: Session,
        user_id: int,
        is_active: Optional[bool] = None,
    ) -> List[RecurringExpense]:
        stmt = (
            select(RecurringExpense)
            .options(joinedload(RecurringExpense.category))
            .where(RecurringExpense.user_id == user_id)
        )
        if is_active is not None:
            stmt = stmt.where(RecurringExpense.is_active == is_active)

        stmt = stmt.order_by(RecurringExpense.next_due_date.asc(), RecurringExpense.id.asc())
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_due_schedules(
        db: Session,
        as_of_date: dt.date,
        user_id: Optional[int] = None,
    ) -> List[RecurringExpense]:
        """Fetch all active schedules where next_due_date <= as_of_date."""
        filters = [
            RecurringExpense.is_active.is_(True),
            RecurringExpense.next_due_date <= as_of_date,
        ]
        if user_id is not None:
            filters.append(RecurringExpense.user_id == user_id)

        stmt = (
            select(RecurringExpense)
            .options(joinedload(RecurringExpense.category))
            .where(and_(*filters))
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def create(
        db: Session,
        user_id: int,
        category_id: int,
        amount: Decimal,
        description: str,
        account: str,
        frequency: str,
        start_date: dt.date,
        next_due_date: dt.date,
        end_date: Optional[dt.date] = None,
    ) -> RecurringExpense:
        recurring = RecurringExpense(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
            description=description.strip(),
            account=account.strip(),
            frequency=frequency,
            start_date=start_date,
            next_due_date=next_due_date,
            end_date=end_date,
            is_active=True,
        )
        db.add(recurring)
        db.commit()
        db.refresh(recurring)
        return recurring

    @staticmethod
    def update(
        db: Session,
        recurring: RecurringExpense,
        amount: Optional[Decimal] = None,
        description: Optional[str] = None,
        category_id: Optional[int] = None,
        account: Optional[str] = None,
        frequency: Optional[str] = None,
        end_date: Optional[dt.date] = None,
        next_due_date: Optional[dt.date] = None,
        is_active: Optional[bool] = None,
    ) -> RecurringExpense:
        if amount is not None:
            recurring.amount = amount
        if description is not None:
            recurring.description = description.strip()
        if category_id is not None:
            recurring.category_id = category_id
        if account is not None:
            recurring.account = account.strip()
        if frequency is not None:
            recurring.frequency = frequency
        if end_date is not None:
            recurring.end_date = end_date
        if next_due_date is not None:
            recurring.next_due_date = next_due_date
        if is_active is not None:
            recurring.is_active = is_active

        db.commit()
        db.refresh(recurring)
        return recurring

    @staticmethod
    def delete(db: Session, recurring: RecurringExpense) -> None:
        db.delete(recurring)
        db.commit()


recurring_repo = RecurringRepository()
