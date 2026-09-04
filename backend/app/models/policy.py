"""Merchant recovery policy. The deterministic gate reads only this row."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import TimestampMixin, id_pk


class PolicyConfig(Base, TimestampMixin):
    __tablename__ = "policy_configs"

    id: Mapped[str] = id_pk()
    name: Mapped[str] = mapped_column(String(80), default="Default recovery policy")
    version: Mapped[int] = mapped_column(Integer, default=1)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # Kill switch and pause, honoured before any action is even scored.
    automation_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)

    # Friction budget, per customer per journey.
    max_contacts: Mapped[int] = mapped_column(Integer, default=3)
    max_retries: Mapped[int] = mapped_column(Integer, default=2)
    max_discount_offers: Mapped[int] = mapped_column(Integer, default=1)
    max_voice_attempts: Mapped[int] = mapped_column(Integer, default=1)

    # Human-approval thresholds.
    human_approval_amount_paise: Mapped[int] = mapped_column(Integer, default=10_000_00)
    discount_approval_pct: Mapped[float] = mapped_column(Float, default=10.0)
    voice_approval_amount_paise: Mapped[int] = mapped_column(Integer, default=25_000_00)

    # Economic floors. Below these Revyn deliberately does nothing.
    min_confidence: Mapped[float] = mapped_column(Float, default=0.12)
    min_expected_value_paise: Mapped[int] = mapped_column(Integer, default=50_00)

    # Journey cadence, in real-world units before the demo clock speedup.
    retry_delay_minutes: Mapped[int] = mapped_column(Integer, default=25)
    followup_delay_hours: Mapped[float] = mapped_column(Float, default=6.0)
    contact_cooldown_minutes: Mapped[int] = mapped_column(Integer, default=45)
    journey_ttl_hours: Mapped[float] = mapped_column(Float, default=72.0)

    # Contact windows, IST hours. Outside them only silent actions are allowed.
    quiet_hours_start: Mapped[int] = mapped_column(Integer, default=21)
    quiet_hours_end: Mapped[int] = mapped_column(Integer, default=8)
    quiet_hours_enforced: Mapped[bool] = mapped_column(Boolean, default=False)

    # Suppress aggressive retries while a payment route is degrading.
    degradation_retry_guard: Mapped[bool] = mapped_column(Boolean, default=True)
    max_discount_pct: Mapped[float] = mapped_column(Float, default=15.0)

    npci_max_attempts: Mapped[int] = mapped_column(Integer, default=4)
    execution_window_guard: Mapped[bool] = mapped_column(Boolean, default=True)
    pdn_lead_hours: Mapped[float] = mapped_column(Float, default=24.0)
    first_presentation_min_confidence: Mapped[float] = mapped_column(Float, default=0.55)
    afa_free_ceiling_paise: Mapped[int] = mapped_column(Integer, default=15_000_00)

    notes: Mapped[dict[str, Any]] = mapped_column(default=dict)
