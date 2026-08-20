from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.settings import UserSettings


class SettingsRepository:
    """Data Access Layer for User Settings and preferences."""

    @staticmethod
    def get_by_user_id(db: Session, user_id: int) -> Optional[UserSettings]:
        stmt = select(UserSettings).where(UserSettings.user_id == user_id)
        return db.scalars(stmt).first()

    @staticmethod
    def create_default(db: Session, user_id: int) -> UserSettings:
        settings = UserSettings(
            user_id=user_id,
            currency="USD",
            date_format="YYYY-MM-DD",
            theme="dark",
            email_notifications=True,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
        return settings

    @staticmethod
    def update(
        db: Session,
        settings: UserSettings,
        currency: Optional[str] = None,
        date_format: Optional[str] = None,
        theme: Optional[str] = None,
        email_notifications: Optional[bool] = None,
    ) -> UserSettings:
        if currency is not None:
            settings.currency = currency.strip().upper()
        if date_format is not None:
            settings.date_format = date_format
        if theme is not None:
            settings.theme = theme
        if email_notifications is not None:
            settings.email_notifications = email_notifications

        db.commit()
        db.refresh(settings)
        return settings


settings_repo = SettingsRepository()
