from typing import Annotated, List
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.group import (
    GroupCreate,
    GroupUpdate,
    GroupResponse,
    GroupMemberAdd,
    GroupMemberResponse,
)
from app.schemas.group_expense import GroupExpenseCreate, GroupExpenseResponse
from app.schemas.balance import GroupBalanceResponse
from app.schemas.settlement import GroupSettlementCreate, GroupSettlementResponse
from app.schemas.common import MessageResponse
from app.services.group_service import group_service
from app.services.group_expense_service import group_expense_service
from app.services.balance_service import balance_service
from app.services.settlement_service import settlement_service

router = APIRouter(prefix="/groups", tags=["Groups"])


@router.post(
    "",
    response_model=GroupResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new group",
    description="Creates a new expense sharing group and automatically registers the creator as an admin.",
)
def create_group(
    group_in: GroupCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GroupResponse:
    client_ip = request.client.host if request.client else None
    group = group_service.create_group(db=db, group_in=group_in, user=current_user, ip_address=client_ip)
    return GroupResponse.model_validate(group)


@router.get(
    "",
    response_model=List[GroupResponse],
    status_code=status.HTTP_200_OK,
    summary="List all groups",
    description="Returns a list of all sharing groups the current user is a member of.",
)
def list_groups(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> List[GroupResponse]:
    groups = group_service.list_groups(db=db, user=current_user)
    return [GroupResponse.model_validate(g) for g in groups]


@router.get(
    "/{group_id}",
    response_model=GroupResponse,
    status_code=status.HTTP_200_OK,
    summary="Get group details",
    description="Retrieves a specific group's metadata and member list. Fails with 403 if the user is not a member.",
)
def get_group(
    group_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GroupResponse:
    group = group_service.get_group(db=db, group_id=group_id, user=current_user)
    return GroupResponse.model_validate(group)


@router.patch(
    "/{group_id}",
    response_model=GroupResponse,
    status_code=status.HTTP_200_OK,
    summary="Update group",
    description="Updates group metadata. Restrict to group admins/owner.",
)
def update_group(
    group_id: int,
    group_in: GroupUpdate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GroupResponse:
    client_ip = request.client.host if request.client else None
    group = group_service.update_group(
        db=db, group_id=group_id, group_in=group_in, user=current_user, ip_address=client_ip
    )
    return GroupResponse.model_validate(group)


@router.delete(
    "/{group_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete group",
    description="Deletes a group. Restrict to group owner. Fails if active expenses exist.",
)
def delete_group(
    group_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    client_ip = request.client.host if request.client else None
    group_service.delete_group(db=db, group_id=group_id, user=current_user, ip_address=client_ip)
    return MessageResponse(message="Group successfully deleted.")


@router.post(
    "/{group_id}/members",
    response_model=GroupMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add member to group",
    description="Adds a user to the group by their email address. Requires admin/owner status.",
)
def add_member(
    group_id: int,
    member_in: GroupMemberAdd,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GroupMemberResponse:
    client_ip = request.client.host if request.client else None
    member = group_service.add_member(
        db=db, group_id=group_id, email=member_in.email, user=current_user, ip_address=client_ip
    )
    return GroupMemberResponse.model_validate(member)


@router.delete(
    "/{group_id}/members/{user_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Remove member from group",
    description="Removes a member from the group. Allows self-leaving or removal by admin/owner.",
)
def remove_member(
    group_id: int,
    user_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    client_ip = request.client.host if request.client else None
    group_service.remove_member(
        db=db, group_id=group_id, target_user_id=user_id, user=current_user, ip_address=client_ip
    )
    return MessageResponse(message="Member successfully removed from group.")


@router.post(
    "/{group_id}/expenses",
    response_model=GroupExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a group expense",
    description="Logs a new group expense, validates payments, runs the split engine, and records participant shares.",
)
def create_group_expense(
    group_id: int,
    expense_in: GroupExpenseCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GroupExpenseResponse:
    client_ip = request.client.host if request.client else None
    expense = group_expense_service.create_group_expense(
        db=db, group_id=group_id, expense_in=expense_in, user=current_user, ip_address=client_ip
    )
    return GroupExpenseResponse.model_validate(expense)


@router.get(
    "/{group_id}/expenses",
    response_model=List[GroupExpenseResponse],
    status_code=status.HTTP_200_OK,
    summary="List group expenses",
    description="Retrieves a paginated list of shared expenses logged in the group.",
)
def list_group_expenses(
    group_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = 1,
    limit: int = 20,
) -> List[GroupExpenseResponse]:
    expenses, _ = group_expense_service.list_group_expenses(
        db=db, group_id=group_id, user=current_user, page=page, limit=limit
    )
    return [GroupExpenseResponse.model_validate(e) for e in expenses]


@router.get(
    "/{group_id}/expenses/{expense_id}",
    response_model=GroupExpenseResponse,
    status_code=status.HTTP_200_OK,
    summary="Get group expense details",
    description="Retrieves specific group expense with payment and participant splits breakdown.",
)
def get_group_expense(
    group_id: int,
    expense_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GroupExpenseResponse:
    expense = group_expense_service.get_group_expense(
        db=db, group_id=group_id, expense_id=expense_id, user=current_user
    )
    return GroupExpenseResponse.model_validate(expense)


@router.delete(
    "/{group_id}/expenses/{expense_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete group expense",
    description="Deletes shared group expense.",
)
def delete_group_expense(
    group_id: int,
    expense_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    client_ip = request.client.host if request.client else None
    group_expense_service.delete_group_expense(
        db=db, group_id=group_id, expense_id=expense_id, user=current_user, ip_address=client_ip
    )
    return MessageResponse(message="Group expense successfully deleted.")


@router.get(
    "/{group_id}/balances",
    response_model=GroupBalanceResponse,
    status_code=status.HTTP_200_OK,
    summary="Get group-wise balance sheet",
    description="Calculates net member balances and generates simplified debt settlement directions.",
)
def get_group_balances(
    group_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GroupBalanceResponse:
    return balance_service.get_group_balances(db=db, group_id=group_id, user=current_user)


@router.post(
    "/{group_id}/settlements",
    response_model=GroupSettlementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a settlement payment",
    description="Records a peer-to-peer settlement payment within the group, updating net balances.",
)
def create_settlement(
    group_id: int,
    settlement_in: GroupSettlementCreate,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> GroupSettlementResponse:
    client_ip = request.client.host if request.client else None
    settlement = settlement_service.create_settlement(
        db=db, group_id=group_id, settlement_in=settlement_in, user=current_user, ip_address=client_ip
    )
    return GroupSettlementResponse.model_validate(settlement)


@router.get(
    "/{group_id}/settlements",
    response_model=List[GroupSettlementResponse],
    status_code=status.HTTP_200_OK,
    summary="Get settlement history",
    description="Returns a chronological list of settlement payments recorded in the group.",
)
def list_settlements(
    group_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> List[GroupSettlementResponse]:
    settlements = settlement_service.list_settlements(db=db, group_id=group_id, user=current_user)
    return [GroupSettlementResponse.model_validate(s) for s in settlements]


@router.delete(
    "/{group_id}/settlements/{settlement_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Reverse a settlement",
    description="Deletes a settlement payment record.",
)
def delete_settlement(
    group_id: int,
    settlement_id: int,
    request: Request,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
) -> MessageResponse:
    client_ip = request.client.host if request.client else None
    settlement_service.delete_settlement(
        db=db, group_id=group_id, settlement_id=settlement_id, user=current_user, ip_address=client_ip
    )
    return MessageResponse(message="Settlement successfully deleted.")
