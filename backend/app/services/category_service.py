from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.category import Category
from app.models.audit_log import AuditLog
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.repositories.category_repo import category_repo


class CategoryService:
    """Business logic for Category operations."""

    @staticmethod
    def list_categories(db: Session, user: User) -> List[Category]:
        return category_repo.list_for_user(db, user_id=user.id)

    @staticmethod
    def get_category(db: Session, category_id: int, user: User) -> Category:
        category = category_repo.get_for_user(db, category_id=category_id, user_id=user.id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found.",
            )
        return category

    @staticmethod
    def create_category(
        db: Session,
        category_in: CategoryCreate,
        user: User,
        ip_address: Optional[str] = None,
    ) -> Category:
        # Check duplicate name for this user
        existing = category_repo.get_by_name(db, user_id=user.id, name=category_in.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You already have a category named '{category_in.name}'.",
            )

        category = category_repo.create(
            db,
            user_id=user.id,
            name=category_in.name,
            color=category_in.color,
            icon=category_in.icon,
            is_system=False,
        )

        audit = AuditLog(
            user_id=user.id,
            action="CATEGORY_CREATED",
            resource_type="category",
            resource_id=str(category.id),
            details={"name": category.name, "color": category.color},
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()

        return category

    @staticmethod
    def update_category(
        db: Session,
        category_id: int,
        category_in: CategoryUpdate,
        user: User,
        ip_address: Optional[str] = None,
    ) -> Category:
        category = CategoryService.get_category(db, category_id=category_id, user=user)

        if category.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System default categories cannot be modified.",
            )

        if category_in.name is not None and category_in.name.lower().strip() != category.name.lower():
            existing = category_repo.get_by_name(db, user_id=user.id, name=category_in.name)
            if existing and existing.id != category.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"You already have a category named '{category_in.name}'.",
                )

        updated_cat = category_repo.update(
            db,
            category=category,
            name=category_in.name,
            color=category_in.color,
            icon=category_in.icon,
        )

        audit = AuditLog(
            user_id=user.id,
            action="CATEGORY_UPDATED",
            resource_type="category",
            resource_id=str(category.id),
            details={"name": updated_cat.name},
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()

        return updated_cat

    @staticmethod
    def delete_category(
        db: Session,
        category_id: int,
        user: User,
        ip_address: Optional[str] = None,
    ) -> None:
        category = CategoryService.get_category(db, category_id=category_id, user=user)

        if category.is_system:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="System default categories cannot be deleted.",
            )

        # Block deletion if the category is still referenced by expenses or budgets
        if category_repo.is_in_use(db, category_id=category.id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a category that is associated with existing expenses or budgets.",
            )

        audit = AuditLog(
            user_id=user.id,
            action="CATEGORY_DELETED",
            resource_type="category",
            resource_id=str(category.id),
            details={"name": category.name},
            ip_address=ip_address,
        )
        db.add(audit)
        category_repo.delete(db, category=category)


category_service = CategoryService()
