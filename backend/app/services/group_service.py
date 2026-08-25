from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.group import Group, GroupMember
from app.models.audit_log import AuditLog
from app.schemas.group import GroupCreate, GroupUpdate, GroupResponse, GroupMemberResponse
from app.repositories.group_repo import group_repo
from app.repositories.user_repo import user_repo


class GroupService:
    """Service layer handling business logic and authorization for Group operations."""

    @staticmethod
    def create_group(db: Session, group_in: GroupCreate, user: User, ip_address: Optional[str] = None) -> Group:
        # 1. Create Group
        group = group_repo.create(
            db=db,
            name=group_in.name,
            icon=group_in.icon,
            description=group_in.description,
            owner_id=user.id,
        )

        # 2. Add owner as admin member
        group_repo.add_member(db, group_id=group.id, user_id=user.id, role="admin")

        # 3. Log Audit
        audit = AuditLog(
            user_id=user.id,
            action="GROUP_CREATED",
            resource_type="group",
            resource_id=str(group.id),
            details={"name": group.name, "owner_id": user.id},
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()

        # Re-fetch group with relations
        return group_repo.get_by_id(db, group_id=group.id)

    @staticmethod
    def get_group(db: Session, group_id: int, user: User) -> Group:
        # Verify group exists
        group = group_repo.get_by_id(db, group_id=group_id)
        if not group:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Group with ID {group_id} not found.",
            )

        # Verify user membership
        if not group_repo.is_member(db, group_id=group_id, user_id=user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this group.",
            )

        return group
        
    @staticmethod
    def list_groups(db: Session, user: User) -> List[Group]:
        return group_repo.list_for_user(db, user_id=user.id)

    @staticmethod
    def update_group(
        db: Session, group_id: int, group_in: GroupUpdate, user: User, ip_address: Optional[str] = None
    ) -> Group:
        # Check permissions: must be member and admin/owner
        group = GroupService.get_group(db, group_id=group_id, user=user)
        membership = group_repo.get_member(db, group_id=group_id, user_id=user.id)
        
        if not membership or (membership.role != "admin" and group.owner_id != user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group admins or owners can update group details.",
            )

        updated_group = group_repo.update(
            db=db,
            group=group,
            name=group_in.name,
            icon=group_in.icon,
            description=group_in.description,
            is_archived=group_in.is_archived,
        )

        # Log Audit
        audit = AuditLog(
            user_id=user.id,
            action="GROUP_UPDATED",
            resource_type="group",
            resource_id=str(updated_group.id),
            details={"name": updated_group.name, "is_archived": updated_group.is_archived},
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()

        return updated_group

    @staticmethod
    def delete_group(db: Session, group_id: int, user: User, ip_address: Optional[str] = None) -> None:
        group = GroupService.get_group(db, group_id=group_id, user=user)
        
        if group.owner_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the group owner can delete the group.",
            )

        # Verify that group has no expenses or settlements
        # (This is a simplified check. When the balance engine is implemented, we can verify that all balances are zero.)
        if len(group.expenses) > 0 or len(group.settlements) > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a group with active expenses or settlements. Please archive it instead.",
            )

        audit = AuditLog(
            user_id=user.id,
            action="GROUP_DELETED",
            resource_type="group",
            resource_id=str(group.id),
            details={"name": group.name},
            ip_address=ip_address,
        )
        db.add(audit)
        
        group_repo.delete(db, group=group)

    @staticmethod
    def add_member(
        db: Session, group_id: int, email: str, user: User, ip_address: Optional[str] = None
    ) -> GroupMember:
        group = GroupService.get_group(db, group_id=group_id, user=user)
        membership = group_repo.get_member(db, group_id=group_id, user_id=user.id)
        
        if not membership or (membership.role != "admin" and group.owner_id != user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only group admins or owners can add new members.",
            )

        # Check if user to add exists
        target_user = user_repo.get_by_email(db, email=email)
        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with email '{email}' is not registered on ExpenseFlow.",
            )

        # Check if already a member
        existing_member = group_repo.get_member(db, group_id=group_id, user_id=target_user.id)
        if existing_member:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User '{target_user.full_name}' is already a member of this group.",
            )

        # Add member
        new_member = group_repo.add_member(db, group_id=group_id, user_id=target_user.id, role="member")

        # Log Audit
        audit = AuditLog(
            user_id=user.id,
            action="GROUP_MEMBER_ADDED",
            resource_type="group",
            resource_id=str(group_id),
            details={"added_user_id": target_user.id, "email": email},
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()

        return new_member

    @staticmethod
    def remove_member(
        db: Session, group_id: int, target_user_id: int, user: User, ip_address: Optional[str] = None
    ) -> None:
        group = GroupService.get_group(db, group_id=group_id, user=user)
        requesting_member = group_repo.get_member(db, group_id=group_id, user_id=user.id)
        target_member = group_repo.get_member(db, group_id=group_id, user_id=target_user_id)

        if not target_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="The specified user is not a member of this group.",
            )

        # Self-leaving is allowed, or admin/owner removing someone
        is_self_leaving = (target_user_id == user.id)
        is_admin_removing = requesting_member and (requesting_member.role == "admin" or group.owner_id == user.id)

        if not is_self_leaving and not is_admin_removing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to remove this member.",
            )

        if group.owner_id == target_user_id and is_self_leaving:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The group owner cannot leave the group. Transfer ownership or delete/archive the group first.",
            )

        # Verify member has no outstanding balances
        from app.services.balance_service import balance_service
        balances = balance_service.get_group_balances(db=db, group_id=group_id, user=user)
        member_balance = next((b for b in balances.balances if b.user_id == target_user_id), None)
        if member_balance and abs(member_balance.net_balance) > 0.005:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Member '{target_member.user.full_name}' has an outstanding balance of {member_balance.net_balance}. They must settle up before leaving.",
            )

        # Remove member
        group_repo.remove_member(db, member=target_member)

        # Log Audit
        audit = AuditLog(
            user_id=user.id,
            action="GROUP_MEMBER_REMOVED",
            resource_type="group",
            resource_id=str(group_id),
            details={"removed_user_id": target_user_id},
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()


group_service = GroupService()
