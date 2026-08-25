from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from app.models.group import Group, GroupMember
from app.models.user import User


class GroupRepository:
    """Data Access Layer for Group and GroupMember entities."""

    @staticmethod
    def get_by_id(db: Session, group_id: int) -> Optional[Group]:
        """Fetch group by primary key ID, eagerly loading members."""
        stmt = (
            select(Group)
            .options(joinedload(Group.members).joinedload(GroupMember.user))
            .where(Group.id == group_id)
        )
        return db.scalars(stmt).first()

    @staticmethod
    def list_for_user(db: Session, user_id: int) -> List[Group]:
        """List all groups where the user is a member."""
        stmt = (
            select(Group)
            .join(GroupMember)
            .where(GroupMember.user_id == user_id, Group.is_archived == False)
            .order_by(Group.updated_at.desc())
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def create(
        db: Session,
        name: str,
        icon: Optional[str] = "👥",
        description: Optional[str] = None,
        owner_id: Optional[int] = None,
    ) -> Group:
        """Create a new group, persisting it to database."""
        group = Group(
            name=name.strip(),
            icon=icon.strip() if icon else "👥",
            description=description.strip() if description else None,
            owner_id=owner_id,
            is_archived=False,
        )
        db.add(group)
        db.commit()
        db.refresh(group)
        return group

    @staticmethod
    def update(
        db: Session,
        group: Group,
        name: Optional[str] = None,
        icon: Optional[str] = None,
        description: Optional[str] = None,
        is_archived: Optional[bool] = None,
    ) -> Group:
        """Update group fields and commit."""
        if name is not None:
            group.name = name.strip()
        if icon is not None:
            group.icon = icon.strip()
        if description is not None:
            group.description = description.strip() if description else None
        if is_archived is not None:
            group.is_archived = is_archived

        db.commit()
        db.refresh(group)
        return group

    @staticmethod
    def delete(db: Session, group: Group) -> None:
        """Delete group."""
        db.delete(group)
        db.commit()

    @staticmethod
    def get_member(db: Session, group_id: int, user_id: int) -> Optional[GroupMember]:
        """Retrieve group membership record for user."""
        stmt = select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        return db.scalars(stmt).first()

    @staticmethod
    def add_member(db: Session, group_id: int, user_id: int, role: str = "member") -> GroupMember:
        """Create a new member association in the group."""
        member = GroupMember(
            group_id=group_id,
            user_id=user_id,
            role=role,
        )
        db.add(member)
        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def remove_member(db: Session, member: GroupMember) -> None:
        """Remove user from group."""
        db.delete(member)
        db.commit()

    @staticmethod
    def update_member_role(db: Session, member: GroupMember, role: str) -> GroupMember:
        """Update member's role (admin/member)."""
        member.role = role
        db.commit()
        db.refresh(member)
        return member

    @staticmethod
    def is_member(db: Session, group_id: int, user_id: int) -> bool:
        """Check if user is a member of the group."""
        stmt = select(GroupMember.id).where(GroupMember.group_id == group_id, GroupMember.user_id == user_id)
        return db.scalar(stmt) is not None


group_repo = GroupRepository()
