from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetUtilizationResponse
from app.schemas.common import MessageResponse
from app.services.budget_service import budget_service

router = APIRouter(prefix="/budgets", tags=["Budgets"])


@router.get(
    "",
    response_model=List[BudgetUtilizationResponse],
    status_code=status.HTTP_200_OK,
    summary="List budgets with real-time utilization",
    description="Returns all category budget allocations with live spent calculations, remaining balance, and status.",
)
def list_budgets(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    month: Optional[int] = Query(None, ge=1, le=12, description="Filter by month (1-12)"),
    year: Optional[int] = Query(None, ge=2000, le=2100, description="Filter by year"),
) -> List[BudgetUtilizationResponse]:
    return budget_service.list_budgets(db=db, user=current_user, month=month, year=year)


@router.post(
    "",
    response_model=BudgetUtilizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new monthly category budget",
    description="Sets a spending cap for a specific category in a given month and year.",
)
def create_budget(
    budget_in: BudgetCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BudgetUtilizationResponse:
    client_ip = request.client.host if request.client else None
    return budget_service.create_budget(
        db=db,
        budget_in=budget_in,
        user=current_user,
        ip_address=client_ip,
    )


@router.get(
    "/{budget_id}",
    response_model=BudgetUtilizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get budget details and utilization",
)
def get_budget(
    budget_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BudgetUtilizationResponse:
    return budget_service.get_budget(db=db, budget_id=budget_id, user=current_user)


@router.patch(
    "/{budget_id}",
    response_model=BudgetUtilizationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update budget limit amount",
)
def update_budget(
    budget_id: int,
    budget_in: BudgetUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> BudgetUtilizationResponse:
    client_ip = request.client.host if request.client else None
    return budget_service.update_budget(
        db=db,
        budget_id=budget_id,
        budget_in=budget_in,
        user=current_user,
        ip_address=client_ip,
    )


@router.delete(
    "/{budget_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a budget",
)
def delete_budget(
    budget_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    client_ip = request.client.host if request.client else None
    budget_service.delete_budget(
        db=db,
        budget_id=budget_id,
        user=current_user,
        ip_address=client_ip,
    )
    return MessageResponse(message="Budget successfully deleted.")
