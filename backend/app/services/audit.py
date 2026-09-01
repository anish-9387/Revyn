"""Immutable audit trail.

Each entry stores the hash of the previous one, so any later edit to a financial action
breaks the chain and is detectable. Every write goes through :func:`record`.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import as_utc, utcnow
from app.core.constants import Actor, AuditEvent
from app.models.audit import AuditLog

GENESIS_HASH = "0" * 64


def _digest(entry: dict[str, Any]) -> str:
    canonical = json.dumps(entry, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


async def record(
    session: AsyncSession,
    *,
    event_type: AuditEvent,
    entity_type: str,
    entity_id: str,
    summary: str = "",
    payload: dict[str, Any] | None = None,
    actor: Actor = Actor.SYSTEM,
    actor_name: str = "",
) -> AuditLog:
    last = (
        await session.execute(select(AuditLog).order_by(AuditLog.sequence.desc()).limit(1))
    ).scalar_one_or_none()
    sequence = (last.sequence + 1) if last else 1
    previous_hash = last.entry_hash if last else GENESIS_HASH
    occurred_at = utcnow()

    body = {
        "sequence": sequence,
        "occurred_at": occurred_at.isoformat(),
        "actor": str(actor),
        "actor_name": actor_name,
        "event_type": str(event_type),
        "entity_type": entity_type,
        "entity_id": entity_id,
        "summary": summary,
        "payload": payload or {},
        "previous_hash": previous_hash,
    }
    entry = AuditLog(
        sequence=sequence,
        occurred_at=occurred_at,
        actor=actor,
        actor_name=actor_name,
        event_type=event_type,
        entity_type=entity_type,
        entity_id=entity_id,
        summary=summary[:240],
        payload=payload or {},
        previous_hash=previous_hash,
        entry_hash=_digest(body),
    )
    session.add(entry)
    await session.flush()
    return entry


async def verify_chain(session: AsyncSession, *, limit: int | None = None) -> dict[str, Any]:
    """Walk the chain and report the first entry whose hash does not reproduce."""
    stmt = select(AuditLog).order_by(AuditLog.sequence)
    if limit:
        stmt = stmt.limit(limit)
    entries = list((await session.execute(stmt)).scalars().all())
    previous = GENESIS_HASH
    for entry in entries:
        body = {
            "sequence": entry.sequence,
            "occurred_at": as_utc(entry.occurred_at).isoformat(),
            "actor": str(entry.actor),
            "actor_name": entry.actor_name,
            "event_type": str(entry.event_type),
            "entity_type": entry.entity_type,
            "entity_id": entry.entity_id,
            "summary": entry.summary,
            "payload": entry.payload,
            "previous_hash": previous,
        }
        if entry.previous_hash != previous or _digest(body) != entry.entry_hash:
            return {"valid": False, "entries": len(entries), "broken_at": entry.sequence}
        previous = entry.entry_hash
    return {"valid": True, "entries": len(entries), "head": previous}


async def count(session: AsyncSession) -> int:
    return int((await session.execute(select(func.count(AuditLog.id)))).scalar() or 0)
