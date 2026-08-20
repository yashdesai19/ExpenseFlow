from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, func
from app.models.category import Category
from app.models.expense import Expense
from app.models.budget import Budget


class CategoryRepository:
    """Data Access Layer for Category entities."""

    @staticmethod
    def get_by_id(db: Session, category_id: int) -> Optional[Category]:
        stmt = select(Category).where(Category.id == category_id)
        return db.scalars(stmt).first()

    @staticmethod
    def get_for_user(db: Session, category_id: int, user_id: int) -> Optional[Category]:
        """Fetch a category if it belongs to the user or is a system-wide default."""
        stmt = select(Category).where(
            Category.id == category_id,
            or_(Category.user_id == user_id, Category.is_system.is_(True)),
        )
        return db.scalars(stmt).first()

    @staticmethod
    def list_for_user(db: Session, user_id: int) -> List[Category]:
        """List all available categories for a user (custom + system defaults)."""
        stmt = select(Category).where(
            or_(Category.user_id == user_id, Category.is_system.is_(True))
        ).order_by(Category.name.asc())
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_by_name(db: Session, user_id: int, name: str) -> Optional[Category]:
        """Check if user already has a category with this name."""
        stmt = select(Category).where(
            Category.user_id == user_id,
            func.lower(Category.name) == name.lower().strip(),
        )
        return db.scalars(stmt).first()

    @staticmethod
    def create(
        db: Session,
        name: str,
        color: str,
        icon: str,
        user_id: Optional[int] = None,
        is_system: bool = False,
    ) -> Category:
        category = Category(
            name=name.strip(),
            color=color.strip(),
            icon=icon.strip(),
            user_id=user_id,
            is_system=is_system,
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        return category

    @staticmethod
    def update(
        db: Session,
        category: Category,
        name: Optional[str] = None,
        color: Optional[str] = None,
        icon: Optional[str] = None,
    ) -> Category:
        if name is not None:
            category.name = name.strip()
        if color is not None:
            category.color = color.strip()
        if icon is not None:
            category.icon = icon.strip()
        db.commit()
        db.refresh(category)
        return category

    @staticmethod
    def delete(db: Session, category: Category) -> None:
        db.delete(category)
        db.commit()

    @staticmethod
    def is_in_use(db: Session, category_id: int) -> bool:
        """Checks if any expenses or budgets reference this category."""
        has_expenses = db.scalar(
            select(func.count(Expense.id)).where(Expense.category_id == category_id)
        ) or 0
        has_budgets = db.scalar(
            select(func.count(Budget.id)).where(Budget.category_id == category_id)
        ) or 0
        return (has_expenses + has_budgets) > 0


category_repo = CategoryRepository()
