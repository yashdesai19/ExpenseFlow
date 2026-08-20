import datetime as dt
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.recurring import (
    RecurringExpenseCreate,
    RecurringExpenseUpdate,
    RecurringExpenseResponse,
    ProcessRecurringResponse,
)
from app.schemas.common import MessageResponse
from app.services.recurring_service import recurring_service

router = APIRouter(prefix="/recurring", tags=["Recurring Expenses & Subscriptions"])


@router.get(
    "",
    response_model=List[RecurringExpenseResponse],
    status_code=status.HTTP_200_OK,
    summary="List recurring expense schedules",
    description="Returns all active or inactive recurring rules configured by the user.",
)
def list_recurring_expenses(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
) -> List[RecurringExpenseResponse]:
    schedules = recurring_service.list_recurring(db=db, user=current_user, is_active=is_active)
    return [RecurringExpenseResponse.model_validate(s) for s in schedules]


@router.post(
    "",
    response_model=RecurringExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new recurring schedule",
    description="Configures a new recurring expense rule (e.g. Monthly Rent, Spotify, Insurance).",
)
def create_recurring_expense(
    recurring_in: RecurringExpenseCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RecurringExpenseResponse:
    client_ip = request.client.host if request.client else None
    schedule = recurring_service.create_recurring(
        db=db,
        recurring_in=recurring_in,
        user=current_user,
        ip_address=client_ip,
    )
    return RecurringExpenseResponse.model_validate(schedule)


@router.get(
    "/{recurring_id}",
    response_model=RecurringExpenseResponse,
    status_code=status.HTTP_200_OK,
    summary="Get recurring schedule details",
)
def get_recurring_expense(
    recurring_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RecurringExpenseResponse:
    schedule = recurring_service.get_recurring(db=db, recurring_id=recurring_id, user=current_user)
    return RecurringExpenseResponse.model_validate(schedule)


@router.patch(
    "/{recurring_id}",
    response_model=RecurringExpenseResponse,
    status_code=status.HTTP_200_OK,
    summary="Update recurring schedule",
)
def update_recurring_expense(
    recurring_id: int,
    recurring_in: RecurringExpenseUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> RecurringExpenseResponse:
    client_ip = request.client.host if request.client else None
    schedule = recurring_service.update_recurring(
        db=db,
        recurring_id=recurring_id,
        recurring_in=recurring_in,
        user=current_user,
        ip_address=client_ip,
    )
    return RecurringExpenseResponse.model_validate(schedule)


@router.delete(
    "/{recurring_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete recurring schedule",
)
def delete_recurring_expense(
    recurring_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    client_ip = request.client.host if request.client else None
    recurring_service.delete_recurring(
        db=db,
        recurring_id=recurring_id,
        user=current_user,
        ip_address=client_ip,
    )
    return MessageResponse(message="Recurring expense schedule successfully deleted.")


@router.post(
    "/process",
    response_model=ProcessRecurringResponse,
    status_code=status.HTTP_200_OK,
    summary="Process pending recurring expenses",
    description="Manually or automatically triggers generation of due expense entries and advances schedule dates.",
)
def process_recurring_expenses(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    as_of_date: Optional[dt.date] = Query(None, description="Check for schedules due on or before this date"),
) -> ProcessRecurringResponse:
    return recurring_service.process_due_expenses(
        db=db,
        as_of_date=as_of_date,
        user_id=current_user.id,
    )
