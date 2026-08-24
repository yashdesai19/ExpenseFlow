from datetime import timedelta
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash, verify_password, create_access_token, DUMMY_PASSWORD_HASH
from app.models.user import User
from app.models.category import Category
from app.models.settings import UserSettings
from app.models.audit_log import AuditLog
from app.schemas.user import UserRegister, UserLogin, TokenResponse, UserResponse
from app.repositories.user_repo import user_repo


DEFAULT_CATEGORIES = [
    {"name": "Food & Dining", "color": "#EF4444", "icon": "🍽️"},
    {"name": "Transportation", "color": "#F59E0B", "icon": "🚗"},
    {"name": "Housing & Rent", "color": "#10B981", "icon": "🏠"},
    {"name": "Utilities & Bills", "color": "#3B82F6", "icon": "⚡"},
    {"name": "Entertainment", "color": "#8B5CF6", "icon": "🎬"},
    {"name": "Healthcare", "color": "#EC4899", "icon": "🩺"},
    {"name": "Shopping", "color": "#06B6D4", "icon": "🛍️"},
    {"name": "Income & Salary", "color": "#22C55E", "icon": "💰"},
]


class AuthService:
    """Service layer handling user authentication and onboarding lifecycle."""

    @staticmethod
    def register(db: Session, user_in: UserRegister, ip_address: Optional[str] = None) -> User:
        """
        Registers a new user, hashes password, seeds default categories and settings,
        and logs the audit event.
        """
        # 1. Check if email already exists
        existing_user = user_repo.get_by_email(db, email=user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists.",
            )

        # 2. Hash plaintext password
        hashed_password = get_password_hash(user_in.password)

        # 3. Create user record
        user = user_repo.create(
            db,
            email=user_in.email,
            hashed_password=hashed_password,
            full_name=user_in.full_name,
        )

        # 4. Seed user default categories
        for cat_data in DEFAULT_CATEGORIES:
            cat = Category(
                user_id=user.id,
                name=cat_data["name"],
                color=cat_data["color"],
                icon=cat_data["icon"],
                is_system=False,
            )
            db.add(cat)

        # 5. Create default user preferences
        user_settings = UserSettings(
            user_id=user.id,
            currency="USD",
            date_format="YYYY-MM-DD",
            theme="dark",
            email_notifications=True,
        )
        db.add(user_settings)

        # 6. Record Audit Log
        audit = AuditLog(
            user_id=user.id,
            action="USER_REGISTERED",
            resource_type="auth",
            resource_id=str(user.id),
            details={"email": user.email, "full_name": user.full_name},
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()
        db.refresh(user)

        return user

    @staticmethod
    def authenticate(
        db: Session,
        login_data: UserLogin,
        ip_address: Optional[str] = None,
    ) -> User:
        """
        Validates user credentials, verifies account status, and records audit trail.
        """
        user = user_repo.get_by_email(db, email=login_data.email)

        # Prevent timing attacks: always verify password even if user doesn't exist
        # (use a dummy hash comparison to equalize response times)
        if user is None:
            verify_password(login_data.password, DUMMY_PASSWORD_HASH)  # Dummy verify for timing safety
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated. Please contact support.",
            )

        # Record Login Audit Log
        audit = AuditLog(
            user_id=user.id,
            action="USER_LOGIN",
            resource_type="auth",
            resource_id=str(user.id),
            details={"email": user.email},
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()

        return user

    @staticmethod
    def create_token_payload(user: User) -> TokenResponse:
        """Generates JWT token and packages TokenResponse schema."""
        expires_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
        access_token = create_access_token(
            subject=user.id,
            expires_delta=timedelta(minutes=expires_minutes),
            extra_claims={"email": user.email, "is_superuser": user.is_superuser},
        )
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_minutes * 60,
            user=UserResponse.model_validate(user),
        )


auth_service = AuthService()
