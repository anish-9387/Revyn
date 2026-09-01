"""Incremental recovery ledger: gross money in, minus what would have arrived anyway."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import ActionType, AttributionMethod, Cohort
from app.core.db import Base
from app.models.base import TimestampMixin, id_pk


class LedgerEntry(Base, TimestampMixin):
    __tablename__ = "ledger_entries"
    __table_args__ = (Index("ix_ledger_cohort_created", "cohort", "created_at"),)

    id: Mapped[str] = id_pk()
    event_id: Mapped[str] = mapped_column(ForeignKey("revenue_events.id"), index=True)
    journey_id: Mapped[str | None] = mapped_column(
        ForeignKey("recovery_journeys.id"), nullable=True, index=True
    )
    cohort: Mapped[Cohort] = mapped_column(String(12), index=True)
    action: Mapped[ActionType] = mapped_column(String(24))

    gross_recovered_paise: Mapped[int] = mapped_column(Integer, default=0)
    organic_estimate_paise: Mapped[int] = mapped_column(Integer, default=0)
    cost_paise: Mapped[int] = mapped_column(Integer, default=0)
    incremental_net_paise: Mapped[int] = mapped_column(Integer, default=0)

    attribution_method: Mapped[AttributionMethod] = mapped_column(String(12))
    organic_probability: Mapped[float] = mapped_column(Float, default=0.0)
    detail: Mapped[dict[str, Any]] = mapped_column(default=dict)
