from typing import Optional
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.settings import UserSettings
from app.models.audit_log import AuditLog
from app.schemas.settings import UserSettingsUpdate
from app.repositories.settings_repo import settings_repo


class SettingsService:
    """Service layer managing user preferences and UI configurations."""

    @staticmethod
    def get_settings(db: Session, user: User) -> UserSettings:
        settings_obj = settings_repo.get_by_user_id(db, user_id=user.id)
        if not settings_obj:
            settings_obj = settings_repo.create_default(db, user_id=user.id)
        return settings_obj

    @staticmethod
    def update_settings(
        db: Session,
        user: User,
        settings_in: UserSettingsUpdate,
        ip_address: Optional[str] = None,
    ) -> UserSettings:
        settings_obj = SettingsService.get_settings(db, user=user)

        updated = settings_repo.update(
            db=db,
            settings=settings_obj,
            currency=settings_in.currency,
            date_format=settings_in.date_format,
            theme=settings_in.theme,
            email_notifications=settings_in.email_notifications,
        )

        audit = AuditLog(
            user_id=user.id,
            action="SETTINGS_UPDATED",
            resource_type="settings",
            resource_id=str(updated.id),
            details={
                "currency": updated.currency,
                "theme": updated.theme,
                "date_format": updated.date_format,
            },
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()

        return updated


settings_service = SettingsService()
