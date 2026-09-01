"""Immutable audit trail."""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import func, select

from app.api.deps import PaginationDep, SessionDep
from app.core.constants import AuditEvent
from app.models.audit import AuditLog
from app.schemas.common import Page
from app.schemas.read import AuditRead
from app.services import audit as audit_service

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=Page[AuditRead])
async def list_entries(
    session: SessionDep,
    page: PaginationDep,
    event_type: AuditEvent | None = None,
    entity_id: str | None = None,
) -> Page[AuditRead]:
    filters = []
    if event_type:
        filters.append(AuditLog.event_type == event_type)
    if entity_id:
        filters.append(AuditLog.entity_id == entity_id)
    total = int(
        (await session.execute(select(func.count(AuditLog.id)).where(*filters))).scalar() or 0
    )
    stmt = (
        select(AuditLog)
        .where(*filters)
        .order_by(AuditLog.sequence.desc())
        .limit(page.limit)
        .offset(page.offset)
    )
    rows = (await session.execute(stmt)).scalars().all()
    return Page(
        items=[AuditRead.model_validate(row) for row in rows],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/verify")
async def verify(session: SessionDep) -> dict:
    """Recompute the hash chain to prove no entry was altered after the fact."""
    return await audit_service.verify_chain(session)
