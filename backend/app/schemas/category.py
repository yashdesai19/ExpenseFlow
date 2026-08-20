from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100, description="Display name of the category")
    color: str = Field(
        default="#3B82F6",
        pattern=r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$",
        description="Hexadecimal color code (e.g. #EF4444)",
    )
    icon: str = Field(
        default="tag",
        min_length=1,
        max_length=50,
        description="Icon identifier or class name (e.g. utensils, car, home)",
    )


class CategoryCreate(CategoryBase):
    """Payload schema for creating a new custom category."""
    pass


class CategoryUpdate(BaseModel):
    """Payload schema for updating a category."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    color: Optional[str] = Field(None, pattern=r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")
    icon: Optional[str] = Field(None, min_length=1, max_length=50)


class CategoryResponse(CategoryBase):
    """Public representation of a Category entity."""
    id: int
    user_id: Optional[int]
    is_system: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
