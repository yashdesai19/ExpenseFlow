from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.models.user import User
from app.models.group import Group, GroupMember, GroupSettlement
from app.models.audit_log import AuditLog
from app.schemas.settlement import GroupSettlementCreate
from app.repositories.group_repo import group_repo


class SettlementService:
    """Service layer handling peer-to-peer debt settlements within groups."""

    @staticmethod
    def create_settlement(
        db: Session, group_id: int, settlement_in: GroupSettlementCreate, user: User, ip_address: Optional[str] = None
    ) -> GroupSettlement:
        # 1. Verify group membership for requester
        group = group_repo.get_by_id(db, group_id=group_id)
        if not group:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found.")

        if not group_repo.is_member(db, group_id=group_id, user_id=user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this group.")

        # 2. Verify payer and receiver are members of the group
        member_ids = {m.user_id for m in group.members}
        if settlement_in.payer_id not in member_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Payer is not a member of this group.")
        if settlement_in.receiver_id not in member_ids:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Receiver is not a member of this group.")

        # 3. Create GroupSettlement
        settlement = GroupSettlement(
            group_id=group_id,
            payer_id=settlement_in.payer_id,
            receiver_id=settlement_in.receiver_id,
            amount=settlement_in.amount,
            date=settlement_in.date,
            notes=settlement_in.notes.strip() if settlement_in.notes else None,
            created_by_id=user.id,
        )
        db.add(settlement)

        # 4. Log Audit
        audit = AuditLog(
            user_id=user.id,
            action="GROUP_SETTLEMENT_CREATED",
            resource_type="group_settlement",
            resource_id=str(settlement.id),
            details={
                "group_id": group_id,
                "payer_id": settlement_in.payer_id,
                "receiver_id": settlement_in.receiver_id,
                "amount": str(settlement.amount),
            },
            ip_address=ip_address,
        )
        db.add(audit)

        db.commit()

        # Re-fetch with relationships loaded
        return (
            db.query(GroupSettlement)
            .options(
                joinedload(GroupSettlement.payer),
                joinedload(GroupSettlement.receiver),
            )
            .filter(GroupSettlement.id == settlement.id)
            .first()
        )

    @staticmethod
    def list_settlements(db: Session, group_id: int, user: User) -> List[GroupSettlement]:
        # Check membership
        if not group_repo.is_member(db, group_id=group_id, user_id=user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this group.")

        return (
            db.query(GroupSettlement)
            .options(
                joinedload(GroupSettlement.payer),
                joinedload(GroupSettlement.receiver),
            )
            .filter(GroupSettlement.group_id == group_id)
            .order_by(desc(GroupSettlement.date), desc(GroupSettlement.id))
            .all()
        )

    @staticmethod
    def delete_settlement(
        db: Session, group_id: int, settlement_id: int, user: User, ip_address: Optional[str] = None
    ) -> None:
        # Check membership
        if not group_repo.is_member(db, group_id=group_id, user_id=user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a member of this group.")

        settlement = (
            db.query(GroupSettlement)
            .filter(GroupSettlement.id == settlement_id, GroupSettlement.group_id == group_id)
            .first()
        )
        if not settlement:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Settlement not found.")

        # Restrict delete to owner/admin or the settlement creator/payer
        group = group_repo.get_by_id(db, group_id=group_id)
        membership = group_repo.get_member(db, group_id=group_id, user_id=user.id)
        
        is_creator = (settlement.created_by_id == user.id)
        is_payer = (settlement.payer_id == user.id)
        is_admin = membership and (membership.role == "admin" or group.owner_id == user.id)

        if not is_creator and not is_payer and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the settlement creator, payer, or group admins can delete this settlement.",
            )

        audit = AuditLog(
            user_id=user.id,
            action="GROUP_SETTLEMENT_DELETED",
            resource_type="group_settlement",
            resource_id=str(settlement.id),
            details={
                "group_id": group_id,
                "payer_id": settlement.payer_id,
                "receiver_id": settlement.receiver_id,
                "amount": str(settlement.amount),
            },
            ip_address=ip_address,
        )
        db.add(audit)
        db.delete(settlement)
        db.commit()


settlement_service = SettlementService()
