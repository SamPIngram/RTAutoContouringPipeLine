import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.models.audit_log import AuditLog

logger = logging.getLogger(__name__)
router = APIRouter()


class AuditLogResponse(BaseModel):
    id: int
    event_type: str
    entity_type: str
    entity_id: str | None
    user_or_system: str
    payload: dict
    timestamp: datetime

    class Config:
        from_attributes = True


@router.get(
    "/audit/logs",
    response_model=list[AuditLogResponse],
    summary="Query audit log entries",
)
async def list_audit_logs(
    event_type: str | None = Query(None, description="Filter by event type"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: str | None = Query(None, description="Filter by entity ID"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[AuditLog]:
    query = select(AuditLog).order_by(AuditLog.timestamp.desc())

    if event_type:
        query = query.where(AuditLog.event_type == event_type)
    if entity_type:
        query = query.where(AuditLog.entity_type == entity_type)
    if entity_id:
        query = query.where(AuditLog.entity_id == entity_id)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()
