import math
from datetime import date
from decimal import Decimal
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.expense import Expense
from app.models.audit_log import AuditLog
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    PaginatedExpenseResponse,
)
from app.repositories.expense_repo import expense_repo
from app.repositories.category_repo import category_repo


class ExpenseService:
    """Service layer handling business logic and validation for Expense operations."""

    @staticmethod
    def create_expense(
        db: Session,
        expense_in: ExpenseCreate,
        user: User,
        ip_address: Optional[str] = None,
    ) -> Expense:
        # 1. Validate that Category exists and is available to this user
        category = category_repo.get_for_user(db, category_id=expense_in.category_id, user_id=user.id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with ID {expense_in.category_id} does not exist.",
            )

        # 2. Persist Expense record with enforced user_id
        expense = expense_repo.create(
            db=db,
            user_id=user.id,
            category_id=expense_in.category_id,
            amount=expense_in.amount,
            description=expense_in.description,
            account=expense_in.account,
            date=expense_in.date,
            notes=expense_in.notes,
            recurring_expense_id=expense_in.recurring_expense_id,
        )

        # 3. Create Audit Trail
        audit = AuditLog(
            user_id=user.id,
            action="EXPENSE_CREATED",
            resource_type="expense",
            resource_id=str(expense.id),
            details={
                "amount": str(expense.amount),
                "description": expense.description,
                "category": category.name,
                "account": expense.account,
                "date": expense.date.isoformat(),
            },
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()

        # Re-fetch with joined relationships for response serialization
        return expense_repo.get_by_id_and_user(db, expense_id=expense.id, user_id=user.id)  # type: ignore

    @staticmethod
    def get_expense(db: Session, expense_id: int, user: User) -> Expense:
        """Fetch a single expense guaranteeing ownership."""
        expense = expense_repo.get_by_id_and_user(db, expense_id=expense_id, user_id=user.id)
        if not expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Expense with ID {expense_id} not found.",
            )
        return expense

    @staticmethod
    def list_expenses(
        db: Session,
        user: User,
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
    ) -> PaginatedExpenseResponse:
        # Enforce page and limit safety boundaries
        page = max(1, page)
        limit = min(max(1, limit), 100)

        items, total_count, total_amount = expense_repo.list_paginated(
            db=db,
            user_id=user.id,
            page=page,
            limit=limit,
            category_id=category_id,
            account=account,
            start_date=start_date,
            end_date=end_date,
            min_amount=min_amount,
            max_amount=max_amount,
            search=search,
            sort_by=sort_by,
            order=order,
        )

        total_pages = math.ceil(total_count / limit) if total_count > 0 else 1

        return PaginatedExpenseResponse(
            items=[ExpenseResponse.model_validate(item) for item in items],
            total=total_count,
            page=page,
            limit=limit,
            total_pages=total_pages,
            total_amount=total_amount,
        )

    @staticmethod
    def update_expense(
        db: Session,
        expense_id: int,
        expense_in: ExpenseUpdate,
        user: User,
        ip_address: Optional[str] = None,
    ) -> Expense:
        expense = ExpenseService.get_expense(db, expense_id=expense_id, user=user)

        # If category is being updated, verify it exists and belongs to user
        if expense_in.category_id is not None and expense_in.category_id != expense.category_id:
            category = category_repo.get_for_user(db, category_id=expense_in.category_id, user_id=user.id)
            if not category:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Category with ID {expense_in.category_id} does not exist.",
                )

        updated_expense = expense_repo.update(
            db=db,
            expense=expense,
            amount=expense_in.amount,
            description=expense_in.description,
            category_id=expense_in.category_id,
            account=expense_in.account,
            date=expense_in.date,
            notes=expense_in.notes,
        )

        audit = AuditLog(
            user_id=user.id,
            action="EXPENSE_UPDATED",
            resource_type="expense",
            resource_id=str(updated_expense.id),
            details={
                "amount": str(updated_expense.amount),
                "description": updated_expense.description,
                "account": updated_expense.account,
                "category_id": updated_expense.category_id,
            },
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()

        return expense_repo.get_by_id_and_user(db, expense_id=updated_expense.id, user_id=user.id)  # type: ignore

    @staticmethod
    def delete_expense(
        db: Session,
        expense_id: int,
        user: User,
        ip_address: Optional[str] = None,
    ) -> None:
        expense = ExpenseService.get_expense(db, expense_id=expense_id, user=user)

        audit = AuditLog(
            user_id=user.id,
            action="EXPENSE_DELETED",
            resource_type="expense",
            resource_id=str(expense.id),
            details={"description": expense.description, "amount": str(expense.amount)},
            ip_address=ip_address,
        )
        db.add(audit)
        expense_repo.delete(db, expense=expense)


expense_service = ExpenseService()
