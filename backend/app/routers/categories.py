from typing import Annotated, List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryUpdate, CategoryResponse
from app.schemas.common import MessageResponse
from app.services.category_service import category_service

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get(
    "",
    response_model=List[CategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List all categories",
    description="Returns all categories available to the authenticated user (custom + system defaults).",
)
def list_categories(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> List[CategoryResponse]:
    categories = category_service.list_categories(db=db, user=current_user)
    return [CategoryResponse.model_validate(c) for c in categories]


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom category",
    description="Adds a new custom spending category for the current user.",
)
def create_category(
    category_in: CategoryCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CategoryResponse:
    client_ip = request.client.host if request.client else None
    category = category_service.create_category(
        db=db,
        category_in=category_in,
        user=current_user,
        ip_address=client_ip,
    )
    return CategoryResponse.model_validate(category)


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get category by ID",
)
def get_category(
    category_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CategoryResponse:
    category = category_service.get_category(db=db, category_id=category_id, user=current_user)
    return CategoryResponse.model_validate(category)


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update custom category",
)
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> CategoryResponse:
    client_ip = request.client.host if request.client else None
    category = category_service.update_category(
        db=db,
        category_id=category_id,
        category_in=category_in,
        user=current_user,
        ip_address=client_ip,
    )
    return CategoryResponse.model_validate(category)


@router.delete(
    "/{category_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete custom category",
)
def delete_category(
    category_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    client_ip = request.client.host if request.client else None
    category_service.delete_category(
        db=db,
        category_id=category_id,
        user=current_user,
        ip_address=client_ip,
    )
    return MessageResponse(message="Category successfully deleted.")
