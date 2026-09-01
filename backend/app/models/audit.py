"""Append-only audit trail. Each row is chained to the previous one by hash."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import Actor, AuditEvent
from app.core.db import Base
from app.models.base import id_pk, utc_column


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_seq", "sequence"),
    )

    id: Mapped[str] = id_pk()
    sequence: Mapped[int] = mapped_column(Integer, autoincrement=False, index=True)
    occurred_at: Mapped[datetime] = utc_column(index=True)
    actor: Mapped[Actor] = mapped_column(String(12))
    actor_name: Mapped[str] = mapped_column(String(48), default="")
    event_type: Mapped[AuditEvent] = mapped_column(String(32), index=True)
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str] = mapped_column(String(36))
    summary: Mapped[str] = mapped_column(String(240), default="")
    payload: Mapped[dict[str, Any]] = mapped_column(default=dict)

    previous_hash: Mapped[str] = mapped_column(String(64), default="")
    entry_hash: Mapped[str] = mapped_column(String(64), default="")
