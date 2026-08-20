from typing import Annotated
from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.user import (
    UserRegister,
    UserLogin,
    UserResponse,
    TokenResponse,
)
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["Authentication & Security"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Creates a new user account, initializes default categories and settings, and records audit trail.",
)
def register(
    user_in: UserRegister,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    """Register new user endpoint."""
    client_ip = request.client.host if request.client else None
    user = auth_service.register(db=db, user_in=user_in, ip_address=client_ip)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Login (JSON)",
    description="Authenticates user credentials and returns a signed JWT access token.",
)
def login(
    login_data: UserLogin,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """JSON login endpoint for frontend web clients."""
    client_ip = request.client.host if request.client else None
    user = auth_service.authenticate(db=db, login_data=login_data, ip_address=client_ip)
    return auth_service.create_token_payload(user)


@router.post(
    "/token",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="OAuth2 Password Flow Token",
    description="Form-encoded authentication endpoint compatible with Swagger UI interactive documentation.",
)
def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    request: Request,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """OAuth2 standard form-data login endpoint."""
    client_ip = request.client.host if request.client else None
    login_data = UserLogin(email=form_data.username, password=form_data.password)
    user = auth_service.authenticate(db=db, login_data=login_data, ip_address=client_ip)
    return auth_service.create_token_payload(user)


@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile",
    description="Returns the profile information of the currently authenticated user extracted from the JWT token.",
)
def get_current_user_profile(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> UserResponse:
    """Protected endpoint to retrieve current user."""
    return UserResponse.model_validate(current_user)
