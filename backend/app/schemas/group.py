import datetime as dt
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict, EmailStr


class GroupMemberBase(BaseModel):
    role: str = Field("member", pattern="^(admin|member)$", description="Role of the member in the group")


class GroupMemberAdd(BaseModel):
    email: EmailStr = Field(..., description="Email of the user to invite to the group")


class GroupMemberUpdate(BaseModel):
    role: str = Field(..., pattern="^(admin|member)$", description="New role for the member")


class GroupMemberResponse(GroupMemberBase):
    id: int
    user_id: int
    full_name: str
    email: str
    joined_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class GroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Name of the sharing group")
    icon: Optional[str] = Field("👥", max_length=50, description="Emoji or symbol icon for the group")
    description: Optional[str] = Field(None, max_length=500, description="Optional description of the group")


class GroupCreate(GroupBase):
    """Payload schema to create a new group."""
    pass


class GroupUpdate(BaseModel):
    """Payload schema to update group metadata."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    icon: Optional[str] = Field(None, max_length=50)
    description: Optional[str] = Field(None, max_length=500)
    is_archived: Optional[bool] = None


class GroupResponse(GroupBase):
    """Detailed response schema representing a group."""
    id: int
    is_archived: bool
    owner_id: Optional[int]
    created_at: dt.datetime
    updated_at: dt.datetime
    members: Optional[List[GroupMemberResponse]] = None

    model_config = ConfigDict(from_attributes=True)
