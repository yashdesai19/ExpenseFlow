from decimal import Decimal
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select, desc

from app.models.user import User
from app.models.group import Group, GroupMember, GroupExpense, GroupExpensePayment, GroupExpenseParticipant
from app.models.audit_log import AuditLog
from app.models.category import Category
from app.schemas.group_expense import GroupExpenseCreate, GroupExpenseParticipantCreate
from app.repositories.group_repo import group_repo
from app.repositories.category_repo import category_repo


class GroupExpenseService:
    """Service layer handling group expense logging and split engine logic."""

    @staticmethod
    def calculate_splits(amount: Decimal, split_method: str, participants: List[GroupExpenseParticipantCreate]) -> List[Decimal]:
        n = len(participants)
        if n == 0:
            return []

        if split_method == "equal":
            share = (amount / Decimal(n)).quantize(Decimal("0.01"))
            calculated_amounts = [share] * n
            diff = amount - sum(calculated_amounts)
            if diff != 0:
                calculated_amounts[0] += diff

        elif split_method == "exact":
            calculated_amounts = [p.share_value for p in participants]
            diff = amount - sum(calculated_amounts)
            if abs(diff) > 0 and abs(diff) <= Decimal("0.05"):
                calculated_amounts[0] += diff

        elif split_method == "percentage":
            calculated_amounts = [
                (amount * p.share_value / Decimal("100.00")).quantize(Decimal("0.01"))
                for p in participants
            ]
            diff = amount - sum(calculated_amounts)
            if diff != 0:
                calculated_amounts[0] += diff

        elif split_method == "shares":
            total_shares = sum(p.share_value for p in participants)
            calculated_amounts = [
                (amount * p.share_value / total_shares).quantize(Decimal("0.01"))
                for p in participants
            ]
            diff = amount - sum(calculated_amounts)
            if diff != 0:
                calculated_amounts[0] += diff
        else:
            raise ValueError(f"Unknown split method: {split_method}")

        return calculated_amounts

    @staticmethod
    def create_group_expense(
        db: Session, group_id: int, expense_in: GroupExpenseCreate, user: User, ip_address: Optional[str] = None
    ) -> GroupExpense:
        # 1. Verify group membership for the creator
        group = group_repo.get_by_id(db, group_id=group_id)
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")

        if not group_repo.is_member(db, group_id=group_id, user_id=user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this group.")

        # 2. Verify Category exists
        category = db.scalar(select(Category).where(Category.id == expense_in.category_id))
        if not category:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Category ID.")

        # 3. Verify all payers and participants are group members
        member_ids = {m.user_id for m in group.members}
        for payment in expense_in.payments:
            if payment.user_id not in member_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User ID {payment.user_id} in payments is not a member of this group.",
                )

        for participant in expense_in.participants:
            if participant.user_id not in member_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User ID {participant.user_id} in participants is not a member of this group.",
                )

        # 4. Calculate Split Amounts
        calculated_shares = GroupExpenseService.calculate_splits(
            amount=expense_in.amount,
            split_method=expense_in.split_method,
            participants=expense_in.participants,
        )

        # 5. Create GroupExpense
        db_expense = GroupExpense(
            group_id=group_id,
            created_by_id=user.id,
            category_id=expense_in.category_id,
            amount=expense_in.amount,
            description=expense_in.description.strip(),
            date=expense_in.date,
            notes=expense_in.notes.strip() if expense_in.notes else None,
            split_method=expense_in.split_method,
        )
        db.add(db_expense)
        db.flush()  # Populates db_expense.id

        # 6. Add Payments
        for payment in expense_in.payments:
            db_payment = GroupExpensePayment(
                group_expense_id=db_expense.id,
                user_id=payment.user_id,
                amount=payment.amount,
            )
            db.add(db_payment)

        # 7. Add Participants
        for idx, participant in enumerate(expense_in.participants):
            db_participant = GroupExpenseParticipant(
                group_expense_id=db_expense.id,
                user_id=participant.user_id,
                share_value=participant.share_value,
                calculated_amount=calculated_shares[idx],
            )
            db.add(db_participant)

        # 8. Log Audit
        audit = AuditLog(
            user_id=user.id,
            action="GROUP_EXPENSE_CREATED",
            resource_type="group_expense",
            resource_id=str(db_expense.id),
            details={
                "group_id": group_id,
                "amount": str(db_expense.amount),
                "description": db_expense.description,
            },
            ip_address=ip_address,
        )
        db.add(audit)

        db.commit()

        # Re-fetch with relationships loaded
        return (
            db.query(GroupExpense)
            .options(
                joinedload(GroupExpense.category),
                joinedload(GroupExpense.payments).joinedload(GroupExpensePayment.user),
                joinedload(GroupExpense.participants).joinedload(GroupExpenseParticipant.user),
            )
            .filter(GroupExpense.id == db_expense.id)
            .first()
        )

    @staticmethod
    def get_group_expense(db: Session, group_id: int, expense_id: int, user: User) -> GroupExpense:
        # Check membership
        if not group_repo.is_member(db, group_id=group_id, user_id=user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this group.")

        expense = (
            db.query(GroupExpense)
            .options(
                joinedload(GroupExpense.category),
                joinedload(GroupExpense.payments).joinedload(GroupExpensePayment.user),
                joinedload(GroupExpense.participants).joinedload(GroupExpenseParticipant.user),
            )
            .filter(GroupExpense.id == expense_id, GroupExpense.group_id == group_id)
            .first()
        )
        if not expense:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group expense not found.")
        return expense

    @staticmethod
    def list_group_expenses(
        db: Session, group_id: int, user: User, page: int = 1, limit: int = 20
    ) -> Tuple[List[GroupExpense], int]:
        # Check membership
        if not group_repo.is_member(db, group_id=group_id, user_id=user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this group.")

        page = max(1, page)
        limit = min(max(1, limit), 100)
        offset = (page - 1) * limit

        base_query = db.query(GroupExpense).filter(GroupExpense.group_id == group_id)
        total_count = base_query.count()

        items = (
            base_query.options(
                joinedload(GroupExpense.category),
                joinedload(GroupExpense.payments).joinedload(GroupExpensePayment.user),
                joinedload(GroupExpense.participants).joinedload(GroupExpenseParticipant.user),
            )
            .order_by(desc(GroupExpense.date), desc(GroupExpense.id))
            .offset(offset)
            .limit(limit)
            .all()
        )

        return list(items), total_count

    @staticmethod
    def delete_group_expense(
        db: Session, group_id: int, expense_id: int, user: User, ip_address: Optional[str] = None
    ) -> None:
        expense = GroupExpenseService.get_group_expense(db, group_id=group_id, expense_id=expense_id, user=user)

        # Restrict delete to owner/admin or the expense creator
        group = group_repo.get_by_id(db, group_id=group_id)
        membership = group_repo.get_member(db, group_id=group_id, user_id=user.id)
        
        is_creator = (expense.created_by_id == user.id)
        is_admin = membership and (membership.role == "admin" or group.owner_id == user.id)

        if not is_creator and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the expense creator or group admins can delete this expense.",
            )

        audit = AuditLog(
            user_id=user.id,
            action="GROUP_EXPENSE_DELETED",
            resource_type="group_expense",
            resource_id=str(expense.id),
            details={
                "group_id": group_id,
                "amount": str(expense.amount),
                "description": expense.description,
            },
            ip_address=ip_address,
        )
        db.add(audit)
        db.delete(expense)
        db.commit()

    @staticmethod
    def update_group_expense(
        db: Session, group_id: int, expense_id: int, expense_in: GroupExpenseCreate, user: User, ip_address: Optional[str] = None
    ) -> GroupExpense:
        # Check membership
        if not group_repo.is_member(db, group_id=group_id, user_id=user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this group.")

        # Get the existing expense
        expense = GroupExpenseService.get_group_expense(db, group_id=group_id, expense_id=expense_id, user=user)

        # Check if expense can be updated - only creator or admin/owner can update
        membership = group_repo.get_member(db, group_id=group_id, user_id=user.id)
        is_creator = (expense.created_by_id == user.id)
        is_admin = membership and (membership.role == "admin" or expense.group.owner_id == user.id)

        if not is_creator and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the expense creator or group admins can update this expense.",
            )

        # Verify Category exists
        category = db.scalar(select(Category).where(Category.id == expense_in.category_id))
        if not category:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid Category ID.")

        # Verify all payers and participants are group members
        member_ids = {m.user_id for m in expense.group.members}
        for payment in expense_in.payments:
            if payment.user_id not in member_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User ID {payment.user_id} in payments is not a member of this group.",
                )

        for participant in expense_in.participants:
            if participant.user_id not in member_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"User ID {participant.user_id} in participants is not a member of this group.",
                )

        # Calculate Split Amounts
        calculated_shares = GroupExpenseService.calculate_splits(
            amount=expense_in.amount,
            split_method=expense_in.split_method,
            participants=expense_in.participants,
        )

        # Update expense fields
        expense.category_id = expense_in.category_id
        expense.amount = expense_in.amount
        expense.description = expense_in.description.strip()
        expense.date = expense_in.date
        expense.notes = expense_in.notes.strip() if expense_in.notes else None
        expense.split_method = expense_in.split_method

        # Remove old payments and participants
        db.query(GroupExpensePayment).filter(GroupExpensePayment.group_expense_id == expense.id).delete()
        db.query(GroupExpenseParticipant).filter(GroupExpenseParticipant.group_expense_id == expense.id).delete()

        # Add new Payments
        for payment in expense_in.payments:
            db_payment = GroupExpensePayment(
                group_expense_id=expense.id,
                user_id=payment.user_id,
                amount=payment.amount,
            )
            db.add(db_payment)

        # Add new Participants
        for idx, participant in enumerate(expense_in.participants):
            db_participant = GroupExpenseParticipant(
                group_expense_id=expense.id,
                user_id=participant.user_id,
                share_value=participant.share_value,
                calculated_amount=calculated_shares[idx],
            )
            db.add(db_participant)

        # Log Audit
        audit = AuditLog(
            user_id=user.id,
            action="GROUP_EXPENSE_UPDATED",
            resource_type="group_expense",
            resource_id=str(expense.id),
            details={
                "group_id": group_id,
                "amount": str(expense.amount),
                "description": expense.description,
            },
            ip_address=ip_address,
        )
        db.add(audit)

        db.commit()

        # Re-fetch with relationships loaded
        return (
            db.query(GroupExpense)
            .options(
                joinedload(GroupExpense.category),
                joinedload(GroupExpense.payments).joinedload(GroupExpensePayment.user),
                joinedload(GroupExpense.participants).joinedload(GroupExpenseParticipant.user),
            )
            .filter(GroupExpense.id == expense.id)
            .first()
        )


group_expense_service = GroupExpenseService()
