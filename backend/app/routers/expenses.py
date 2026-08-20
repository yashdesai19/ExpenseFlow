from datetime import date
from decimal import Decimal
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    PaginatedExpenseResponse,
)
from app.schemas.common import MessageResponse
from app.services.expense_service import expense_service

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.get(
    "",
    response_model=PaginatedExpenseResponse,
    status_code=status.HTTP_200_OK,
    summary="List expenses with filtering and pagination",
    description=(
        "Returns a paginated list of expenses belonging exclusively to the current user. "
        "Supports filtering by category, payment account, date range, min/max amount, text search, and custom sorting."
    ),
)
def list_expenses(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Number of expenses per page"),
    category_id: Optional[int] = Query(None, description="Filter by Category ID"),
    account: Optional[str] = Query(None, description="Filter by account (e.g. Credit Card, Cash)"),
    start_date: Optional[date] = Query(None, description="Filter expenses on or after this date"),
    end_date: Optional[date] = Query(None, description="Filter expenses on or before this date"),
    min_amount: Optional[Decimal] = Query(None, ge=0, description="Minimum expense amount"),
    max_amount: Optional[Decimal] = Query(None, ge=0, description="Maximum expense amount"),
    search: Optional[str] = Query(None, description="Search term in description or notes"),
    sort_by: str = Query("date", pattern="^(date|amount|created_at)$", description="Sort field"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort direction"),
) -> PaginatedExpenseResponse:
    return expense_service.list_expenses(
        db=db,
        user=current_user,
        page=page,
        limit=limit,
        category_id=category_id,
        account=account,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        search=search,
        sort_by=sort_by,
        order=order,
    )


@router.post(
    "",
    response_model=ExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new expense",
    description="Logs a new expense transaction for the authenticated user.",
)
def create_expense(
    expense_in: ExpenseCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ExpenseResponse:
    client_ip = request.client.host if request.client else None
    expense = expense_service.create_expense(
        db=db,
        expense_in=expense_in,
        user=current_user,
        ip_address=client_ip,
    )
    return ExpenseResponse.model_validate(expense)


@router.get(
    "/{expense_id}",
    response_model=ExpenseResponse,
    status_code=status.HTTP_200_OK,
    summary="Get single expense by ID",
    description="Retrieves a specific expense record. Fails with 404 if not found or owned by another user.",
)
def get_expense(
    expense_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ExpenseResponse:
    expense = expense_service.get_expense(db=db, expense_id=expense_id, user=current_user)
    return ExpenseResponse.model_validate(expense)


@router.patch(
    "/{expense_id}",
    response_model=ExpenseResponse,
    status_code=status.HTTP_200_OK,
    summary="Update an existing expense",
    description="Partially updates an existing expense record.",
)
def update_expense(
    expense_id: int,
    expense_in: ExpenseUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> ExpenseResponse:
    client_ip = request.client.host if request.client else None
    expense = expense_service.update_expense(
        db=db,
        expense_id=expense_id,
        expense_in=expense_in,
        user=current_user,
        ip_address=client_ip,
    )
    return ExpenseResponse.model_validate(expense)


@router.delete(
    "/{expense_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete an expense",
    description="Permanently deletes an expense record owned by the authenticated user.",
)
def delete_expense(
    expense_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    client_ip = request.client.host if request.client else None
    expense_service.delete_expense(
        db=db,
        expense_id=expense_id,
        user=current_user,
        ip_address=client_ip,
    )
    return MessageResponse(message="Expense successfully deleted.")
