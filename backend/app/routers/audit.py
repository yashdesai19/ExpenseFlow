from typing import Annotated, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.dependencies.auth import get_current_active_user
from app.models.user import User
from app.schemas.audit import PaginatedAuditLogResponse
from app.services.audit_service import audit_service

router = APIRouter(prefix="/audit-logs", tags=["Audit & Security Logs"])


@router.get(
    "",
    response_model=PaginatedAuditLogResponse,
    status_code=status.HTTP_200_OK,
    summary="List security and transaction audit logs",
    description="Returns an immutable chronological log of actions, security events, and entity modifications.",
)
def list_audit_logs(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[Session, Depends(get_db)],
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Records per page"),
    action: Optional[str] = Query(None, description="Filter by event action (e.g. USER_LOGIN, EXPENSE_CREATED)"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type (e.g. expense, budget, auth)"),
) -> PaginatedAuditLogResponse:
    return audit_service.list_audit_logs(
        db=db,
        user=current_user,
        page=page,
        limit=limit,
        action=action,
        resource_type=resource_type,
    )
