from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="User's primary email address")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name of the user")


class UserRegister(UserBase):
    """Payload schema for user registration."""
    password: str = Field(
        ...,
        min_length=8,
        max_length=100,
        description="Password (minimum 8 characters)",
    )


class UserLogin(BaseModel):
    """Payload schema for JSON-based login."""
    email: EmailStr = Field(..., description="User email")
    password: str = Field(..., description="Plaintext password")


class UserResponse(UserBase):
    """
    Public response schema for User entity.
    Excludes sensitive fields like hashed_password.
    """
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Schema returned upon successful authentication."""
    access_token: str = Field(..., description="JWT Bearer access token")
    token_type: str = Field(default="bearer", description="Authentication scheme")
    expires_in: int = Field(..., description="Token validity duration in seconds")
    user: UserResponse = Field(..., description="Authenticated user profile")


class UserUpdate(BaseModel):
    """Payload schema for updating profile details."""
    full_name: Optional[str] = Field(None, min_length=2, max_length=100)
    password: Optional[str] = Field(None, min_length=8, max_length=100)
