from typing import Annotated
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.settings import UserSettingsUpdate, UserSettingsResponse
from app.services.settings_service import settings_service

router = APIRouter(prefix="/settings", tags=["User Preferences & Settings"])


@router.get(
    "",
    response_model=UserSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get user preferences and settings",
    description="Retrieves active currency, theme mode, date format, and notification preferences for the user.",
)
def get_user_settings(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserSettingsResponse:
    settings_obj = settings_service.get_settings(db=db, user=current_user)
    return UserSettingsResponse.model_validate(settings_obj)


@router.patch(
    "",
    response_model=UserSettingsResponse,
    status_code=status.HTTP_200_OK,
    summary="Update user preferences",
    description="Updates user currency, date display formatting, theme, or notification preferences.",
)
def update_user_settings(
    settings_in: UserSettingsUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> UserSettingsResponse:
    client_ip = request.client.host if request.client else None
    updated = settings_service.update_settings(
        db=db,
        user=current_user,
        settings_in=settings_in,
        ip_address=client_ip,
    )
    return UserSettingsResponse.model_validate(updated)
