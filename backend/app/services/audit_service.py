import math
from typing import Optional
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.audit import AuditLogResponse, PaginatedAuditLogResponse
from app.repositories.audit_repo import audit_repo


class AuditService:
    """Service layer for compliance, security event logs, and operational history."""

    @staticmethod
    def list_audit_logs(
        db: Session,
        user: User,
        page: int = 1,
        limit: int = 20,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> PaginatedAuditLogResponse:
        page = max(1, page)
        limit = min(max(1, limit), 100)

        # Superusers can inspect system-wide audit logs; standard users see only their own actions
        user_filter = None if user.is_superuser else user.id

        items, total = audit_repo.list_paginated(
            db=db,
            user_id=user_filter,
            page=page,
            limit=limit,
            action=action,
            resource_type=resource_type,
        )

        total_pages = math.ceil(total / limit) if total > 0 else 1

        return PaginatedAuditLogResponse(
            items=[AuditLogResponse.model_validate(item) for item in items],
            total=total,
            page=page,
            limit=limit,
            total_pages=total_pages,
        )


audit_service = AuditService()
