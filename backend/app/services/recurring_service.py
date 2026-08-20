import calendar
import datetime as dt
from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.recurring import RecurringExpense
from app.models.expense import Expense
from app.models.audit_log import AuditLog
from app.schemas.recurring import (
    RecurringExpenseCreate,
    RecurringExpenseUpdate,
    ProcessRecurringResponse,
)
from app.repositories.recurring_repo import recurring_repo
from app.repositories.category_repo import category_repo


def calculate_next_date(current_date: dt.date, frequency: str) -> dt.date:
    """
    Safely calculates the next occurrence date handling variable month lengths
    (e.g., Jan 31 -> Feb 28, Leap Years) and frequencies.
    """
    if frequency == "DAILY":
        return current_date + dt.timedelta(days=1)
    elif frequency == "WEEKLY":
        return current_date + dt.timedelta(weeks=1)
    elif frequency == "MONTHLY":
        year = current_date.year + (current_date.month // 12)
        month = (current_date.month % 12) + 1
        max_days = calendar.monthrange(year, month)[1]
        day = min(current_date.day, max_days)
        return dt.date(year, month, day)
    elif frequency == "YEARLY":
        year = current_date.year + 1
        max_days = calendar.monthrange(year, current_date.month)[1]
        day = min(current_date.day, max_days)
        return dt.date(year, current_date.month, day)
    return current_date + dt.timedelta(days=30)


class RecurringService:
    """Service layer managing recurring expense schedules and automated expense generation."""

    @staticmethod
    def create_recurring(
        db: Session,
        recurring_in: RecurringExpenseCreate,
        user: User,
        ip_address: Optional[str] = None,
    ) -> RecurringExpense:
        # Validate category
        category = category_repo.get_for_user(db, category_id=recurring_in.category_id, user_id=user.id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with ID {recurring_in.category_id} not found.",
            )

        next_due = recurring_in.next_due_date or recurring_in.start_date

        recurring = recurring_repo.create(
            db=db,
            user_id=user.id,
            category_id=recurring_in.category_id,
            amount=recurring_in.amount,
            description=recurring_in.description,
            account=recurring_in.account,
            frequency=recurring_in.frequency,
            start_date=recurring_in.start_date,
            next_due_date=next_due,
            end_date=recurring_in.end_date,
        )

        audit = AuditLog(
            user_id=user.id,
            action="RECURRING_EXPENSE_CREATED",
            resource_type="recurring_expense",
            resource_id=str(recurring.id),
            details={
                "description": recurring.description,
                "amount": str(recurring.amount),
                "frequency": recurring.frequency,
                "next_due_date": str(recurring.next_due_date),
            },
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()

        return recurring_repo.get_by_id_and_user(db, recurring_id=recurring.id, user_id=user.id)  # type: ignore

    @staticmethod
    def list_recurring(
        db: Session,
        user: User,
        is_active: Optional[bool] = None,
    ) -> List[RecurringExpense]:
        return recurring_repo.list_for_user(db, user_id=user.id, is_active=is_active)

    @staticmethod
    def get_recurring(db: Session, recurring_id: int, user: User) -> RecurringExpense:
        recurring = recurring_repo.get_by_id_and_user(db, recurring_id=recurring_id, user_id=user.id)
        if not recurring:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Recurring schedule with ID {recurring_id} not found.",
            )
        return recurring

    @staticmethod
    def update_recurring(
        db: Session,
        recurring_id: int,
        recurring_in: RecurringExpenseUpdate,
        user: User,
        ip_address: Optional[str] = None,
    ) -> RecurringExpense:
        recurring = RecurringService.get_recurring(db, recurring_id=recurring_id, user=user)

        if recurring_in.category_id is not None and recurring_in.category_id != recurring.category_id:
            cat = category_repo.get_for_user(db, category_id=recurring_in.category_id, user_id=user.id)
            if not cat:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Category with ID {recurring_in.category_id} not found.",
                )

        updated = recurring_repo.update(
            db=db,
            recurring=recurring,
            amount=recurring_in.amount,
            description=recurring_in.description,
            category_id=recurring_in.category_id,
            account=recurring_in.account,
            frequency=recurring_in.frequency,
            end_date=recurring_in.end_date,
            next_due_date=recurring_in.next_due_date,
            is_active=recurring_in.is_active,
        )

        audit = AuditLog(
            user_id=user.id,
            action="RECURRING_EXPENSE_UPDATED",
            resource_type="recurring_expense",
            resource_id=str(updated.id),
            details={"description": updated.description, "amount": str(updated.amount)},
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()

        return recurring_repo.get_by_id_and_user(db, recurring_id=updated.id, user_id=user.id)  # type: ignore

    @staticmethod
    def delete_recurring(
        db: Session,
        recurring_id: int,
        user: User,
        ip_address: Optional[str] = None,
    ) -> None:
        recurring = RecurringService.get_recurring(db, recurring_id=recurring_id, user=user)

        audit = AuditLog(
            user_id=user.id,
            action="RECURRING_EXPENSE_DELETED",
            resource_type="recurring_expense",
            resource_id=str(recurring.id),
            details={"description": recurring.description},
            ip_address=ip_address,
        )
        db.add(audit)
        recurring_repo.delete(db, recurring=recurring)

    @staticmethod
    def process_due_expenses(
        db: Session,
        as_of_date: Optional[dt.date] = None,
        user_id: Optional[int] = None,
    ) -> ProcessRecurringResponse:
        """
        Scans all active schedules whose next_due_date <= as_of_date,
        generates official Expense entries, advances their next due date,
        and marks completed schedules as inactive.
        """
        check_date = as_of_date or dt.date.today()
        due_schedules = recurring_repo.get_due_schedules(db, as_of_date=check_date, user_id=user_id)

        generated_ids: List[int] = []

        for sched in due_schedules:
            # 1. Create the materialized expense record
            expense = Expense(
                user_id=sched.user_id,
                category_id=sched.category_id,
                recurring_expense_id=sched.id,
                amount=sched.amount,
                description=f"{sched.description} (Recurring: {sched.frequency})",
                account=sched.account,
                date=sched.next_due_date,
                notes=f"Automatically generated from recurring schedule #{sched.id}",
            )
            db.add(expense)
            db.flush()  # Generates expense.id
            generated_ids.append(expense.id)

            # 2. Advance next due date
            next_date = calculate_next_date(sched.next_due_date, sched.frequency)
            sched.next_due_date = next_date

            # 3. Check if schedule has passed end date
            if sched.end_date and sched.next_due_date > sched.end_date:
                sched.is_active = False

            # 4. Record Audit Log
            audit = AuditLog(
                user_id=sched.user_id,
                action="RECURRING_EXPENSE_PROCESSED",
                resource_type="expense",
                resource_id=str(expense.id),
                details={
                    "recurring_schedule_id": sched.id,
                    "generated_expense_id": expense.id,
                    "amount": str(sched.amount),
                    "advanced_next_due_date": str(sched.next_due_date),
                },
                ip_address=None,
            )
            db.add(audit)

        db.commit()

        return ProcessRecurringResponse(
            processed_schedules=len(due_schedules),
            generated_expenses_count=len(generated_ids),
            generated_expense_ids=generated_ids,
            message=(
                f"Successfully processed {len(due_schedules)} recurring schedule(s) "
                f"and generated {len(generated_ids)} expense transaction(s)."
            ),
        )


recurring_service = RecurringService()
