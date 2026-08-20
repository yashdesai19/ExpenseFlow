from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.user import User


class UserRepository:
    """Data Access Layer for User entity."""

    @staticmethod
    def get_by_id(db: Session, user_id: int) -> Optional[User]:
        """Fetch user by primary key ID."""
        stmt = select(User).where(User.id == user_id)
        return db.scalars(stmt).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Fetch user by email (case-insensitive search)."""
        stmt = select(User).where(User.email == email.lower().strip())
        return db.scalars(stmt).first()

    @staticmethod
    def create(
        db: Session,
        email: str,
        hashed_password: str,
        full_name: str,
        is_superuser: bool = False,
    ) -> User:
        """Persist a new user entity to the database."""
        db_user = User(
            email=email.lower().strip(),
            hashed_password=hashed_password,
            full_name=full_name.strip(),
            is_active=True,
            is_superuser=is_superuser,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user

    @staticmethod
    def update(
        db: Session,
        user: User,
        full_name: Optional[str] = None,
        hashed_password: Optional[str] = None,
    ) -> User:
        """Update existing user fields and commit."""
        if full_name is not None:
            user.full_name = full_name.strip()
        if hashed_password is not None:
            user.hashed_password = hashed_password
        db.commit()
        db.refresh(user)
        return user


user_repo = UserRepository()
