from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from app.models.audit_log import AuditLog


class AuditLogRepository:
    """Data Access Layer for immutable audit trail records."""

    @staticmethod
    def list_paginated(
        db: Session,
        user_id: Optional[int] = None,
        page: int = 1,
        limit: int = 20,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
    ) -> Tuple[List[AuditLog], int]:
        filters = []
        if user_id is not None:
            filters.append(AuditLog.user_id == user_id)
        if action is not None:
            filters.append(AuditLog.action == action)
        if resource_type is not None:
            filters.append(AuditLog.resource_type == resource_type)

        # Count total
        count_stmt = select(func.count(AuditLog.id)).where(*filters)
        total = db.scalar(count_stmt) or 0

        # Query paginated rows
        offset = (page - 1) * limit
        stmt = (
            select(AuditLog)
            .where(*filters)
            .order_by(desc(AuditLog.created_at), desc(AuditLog.id))
            .offset(offset)
            .limit(limit)
        )
        items = list(db.scalars(stmt).all())

        return items, total

    @staticmethod
    def create(
        db: Session,
        action: str,
        resource_type: str,
        user_id: Optional[int] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        audit = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)
        return audit


audit_repo = AuditLogRepository()
