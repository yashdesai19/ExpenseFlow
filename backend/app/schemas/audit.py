import datetime as dt
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class AuditLogResponse(BaseModel):
    """Immutable audit record schema."""
    id: int
    user_id: Optional[int]
    action: str
    resource_type: str
    resource_id: Optional[str]
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    created_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedAuditLogResponse(BaseModel):
    """Paginated list of system and security audit entries."""
    items: List[AuditLogResponse]
    total: int
    page: int
    limit: int
    total_pages: int
