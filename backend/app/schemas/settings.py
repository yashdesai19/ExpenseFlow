import datetime as dt
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class UserSettingsBase(BaseModel):
    currency: str = Field(
        default="USD",
        min_length=1,
        max_length=10,
        description="ISO 4217 Currency Code (e.g. USD, EUR, INR, GBP)",
    )
    date_format: str = Field(
        default="YYYY-MM-DD",
        pattern="^(YYYY-MM-DD|DD/MM/YYYY|MM/DD/YYYY)$",
        description="Display date formatting preference",
    )
    theme: str = Field(
        default="dark",
        pattern="^(dark|light|system)$",
        description="UI appearance theme mode",
    )
    email_notifications: bool = Field(
        default=True,
        description="Enable/disable email summaries and alerts",
    )


class UserSettingsUpdate(BaseModel):
    """Payload schema for partially updating preferences."""
    currency: Optional[str] = Field(None, min_length=1, max_length=10)
    date_format: Optional[str] = Field(None, pattern="^(YYYY-MM-DD|DD/MM/YYYY|MM/DD/YYYY)$")
    theme: Optional[str] = Field(None, pattern="^(dark|light|system)$")
    email_notifications: Optional[bool] = None


class UserSettingsResponse(UserSettingsBase):
    """Public representation of user preferences."""
    id: int
    user_id: int
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)
