from decimal import Decimal
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.budget import Budget
from app.models.audit_log import AuditLog
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetUtilizationResponse
from app.repositories.budget_repo import budget_repo
from app.repositories.category_repo import category_repo


class BudgetService:
    """Service layer managing budget allocations and dynamic utilization metrics."""

    @staticmethod
    def _compute_utilization(db: Session, budget: Budget) -> BudgetUtilizationResponse:
        spent = budget_repo.get_category_spent_for_month(
            db=db,
            user_id=budget.user_id,
            category_id=budget.category_id,
            month=budget.month,
            year=budget.year,
        )
        remaining = budget.amount - spent
        pct = (float(spent) / float(budget.amount) * 100.0) if budget.amount > 0 else 0.0

        if remaining < 0:
            status_label = "EXCEEDED"
        elif pct >= 80.0:
            status_label = "WARNING_80_PERCENT"
        else:
            status_label = "UNDER_BUDGET"

        return BudgetUtilizationResponse(
            id=budget.id,
            user_id=budget.user_id,
            category_id=budget.category_id,
            amount=budget.amount,
            month=budget.month,
            year=budget.year,
            created_at=budget.created_at,
            updated_at=budget.updated_at,
            category=budget.category,  # type: ignore
            spent_amount=spent,
            remaining_amount=remaining,
            percentage_used=round(pct, 2),
            status=status_label,
        )

    @staticmethod
    def create_budget(
        db: Session,
        budget_in: BudgetCreate,
        user: User,
        ip_address: Optional[str] = None,
    ) -> BudgetUtilizationResponse:
        # 1. Verify category exists for this user
        category = category_repo.get_for_user(db, category_id=budget_in.category_id, user_id=user.id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with ID {budget_in.category_id} not found.",
            )

        # 2. Check duplicate budget for same category and month/year
        existing = budget_repo.get_by_category_and_period(
            db=db,
            user_id=user.id,
            category_id=budget_in.category_id,
            month=budget_in.month,
            year=budget_in.year,
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"A budget for '{category.name}' already exists for "
                    f"{budget_in.month}/{budget_in.year}. Please update the existing budget instead."
                ),
            )

        budget = budget_repo.create(
            db=db,
            user_id=user.id,
            category_id=budget_in.category_id,
            amount=budget_in.amount,
            month=budget_in.month,
            year=budget_in.year,
        )

        audit = AuditLog(
            user_id=user.id,
            action="BUDGET_CREATED",
            resource_type="budget",
            resource_id=str(budget.id),
            details={
                "amount": str(budget.amount),
                "category": category.name,
                "period": f"{budget.month}/{budget.year}",
            },
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()

        # Re-fetch with joined category
        fresh_budget = budget_repo.get_by_id_and_user(db, budget_id=budget.id, user_id=user.id)
        return BudgetService._compute_utilization(db, fresh_budget)  # type: ignore

    @staticmethod
    def list_budgets(
        db: Session,
        user: User,
        month: Optional[int] = None,
        year: Optional[int] = None,
    ) -> List[BudgetUtilizationResponse]:
        budgets = budget_repo.list_for_user_and_period(
            db=db,
            user_id=user.id,
            month=month,
            year=year,
        )
        return [BudgetService._compute_utilization(db, b) for b in budgets]

    @staticmethod
    def get_budget(db: Session, budget_id: int, user: User) -> BudgetUtilizationResponse:
        budget = budget_repo.get_by_id_and_user(db, budget_id=budget_id, user_id=user.id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Budget with ID {budget_id} not found.",
            )
        return BudgetService._compute_utilization(db, budget)

    @staticmethod
    def update_budget(
        db: Session,
        budget_id: int,
        budget_in: BudgetUpdate,
        user: User,
        ip_address: Optional[str] = None,
    ) -> BudgetUtilizationResponse:
        budget = budget_repo.get_by_id_and_user(db, budget_id=budget_id, user_id=user.id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Budget with ID {budget_id} not found.",
            )

        if budget_in.amount is not None:
            budget = budget_repo.update(db, budget=budget, amount=budget_in.amount)

        audit = AuditLog(
            user_id=user.id,
            action="BUDGET_UPDATED",
            resource_type="budget",
            resource_id=str(budget.id),
            details={"amount": str(budget.amount)},
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()

        return BudgetService._compute_utilization(db, budget)

    @staticmethod
    def delete_budget(
        db: Session,
        budget_id: int,
        user: User,
        ip_address: Optional[str] = None,
    ) -> None:
        budget = budget_repo.get_by_id_and_user(db, budget_id=budget_id, user_id=user.id)
        if not budget:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Budget with ID {budget_id} not found.",
            )

        audit = AuditLog(
            user_id=user.id,
            action="BUDGET_DELETED",
            resource_type="budget",
            resource_id=str(budget.id),
            details={"amount": str(budget.amount)},
            ip_address=ip_address,
        )
        db.add(audit)
        budget_repo.delete(db, budget=budget)


budget_service = BudgetService()
