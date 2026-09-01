"""Recovery journeys, the actions they schedule and the decisions behind them."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ActionStatus, ActionType, JourneyState, PolicyVerdict
from app.core.db import Base
from app.models.base import TimestampMixin, id_pk, utc_column

if TYPE_CHECKING:
    from app.models.event import RevenueEvent


class RecoveryJourney(Base, TimestampMixin):
    """One adaptive journey. At most one open journey may own a customer."""

    __tablename__ = "recovery_journeys"
    __table_args__ = (
        Index("ix_journeys_state_next", "state", "next_action_at"),
        Index("ix_journeys_customer_state", "customer_id", "state"),
    )

    id: Mapped[str] = id_pk()
    event_id: Mapped[str] = mapped_column(ForeignKey("revenue_events.id"), index=True)
    event: Mapped[RevenueEvent] = relationship(back_populates="journeys", lazy="joined")
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)

    state: Mapped[JourneyState] = mapped_column(
        String(24), default=JourneyState.DETECTED, index=True
    )
    strategy_key: Mapped[str] = mapped_column(String(96), default="", index=True)
    step_index: Mapped[int] = mapped_column(Integer, default=0)
    next_action_at: Mapped[datetime | None] = utc_column(nullable=True, index=True)
    closed_at: Mapped[datetime | None] = utc_column(nullable=True)
    close_reason: Mapped[str | None] = mapped_column(String(160), nullable=True)

    # Friction budget consumption, tracked on the journey that owns the customer.
    contacts_used: Mapped[int] = mapped_column(Integer, default=0)
    retries_used: Mapped[int] = mapped_column(Integer, default=0)
    discounts_used: Mapped[int] = mapped_column(Integer, default=0)
    voice_used: Mapped[int] = mapped_column(Integer, default=0)

    recovered_amount_paise: Mapped[int] = mapped_column(Integer, default=0)
    cost_paise: Mapped[int] = mapped_column(Integer, default=0)
    promise_date: Mapped[datetime | None] = utc_column(nullable=True)
    promise_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    plan: Mapped[list[Any]] = mapped_column(default=list)
    transitions: Mapped[list[Any]] = mapped_column(default=list)

    # Journeys are never useful without their steps, so both collections load eagerly.
    actions: Mapped[list[RecoveryAction]] = relationship(
        back_populates="journey",
        order_by="RecoveryAction.sequence",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    decisions: Mapped[list[Decision]] = relationship(
        back_populates="journey",
        order_by="Decision.created_at",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class RecoveryAction(Base, TimestampMixin):
    """A single scheduled step of a journey, gated before it can execute."""

    __tablename__ = "recovery_actions"
    __table_args__ = (
        Index("ix_actions_status_scheduled", "status", "scheduled_at"),
        Index("uq_actions_idempotency", "idempotency_key", unique=True),
    )

    id: Mapped[str] = id_pk()
    journey_id: Mapped[str] = mapped_column(ForeignKey("recovery_journeys.id"), index=True)
    journey: Mapped[RecoveryJourney] = relationship(back_populates="actions", lazy="selectin")
    decision_id: Mapped[str | None] = mapped_column(ForeignKey("decisions.id"), nullable=True)

    sequence: Mapped[int] = mapped_column(Integer, default=0)
    action_type: Mapped[ActionType] = mapped_column(String(24), index=True)
    status: Mapped[ActionStatus] = mapped_column(
        String(20), default=ActionStatus.PLANNED, index=True
    )
    idempotency_key: Mapped[str] = mapped_column(String(80))

    scheduled_at: Mapped[datetime] = utc_column(index=True)
    executed_at: Mapped[datetime | None] = utc_column(nullable=True)
    cost_paise: Mapped[int] = mapped_column(Integer, default=0)
    friction_score: Mapped[float] = mapped_column(Float, default=0.0)
    discount_pct: Mapped[float] = mapped_column(Float, default=0.0)

    provider_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)
    blocked_reasons: Mapped[list[Any]] = mapped_column(default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict[str, Any]] = mapped_column(default=dict)


class Decision(Base, TimestampMixin):
    """The recovery confidence ledger: every automated choice, fully explained."""

    __tablename__ = "decisions"
    __table_args__ = (Index("ix_decisions_event_created", "event_id", "created_at"),)

    id: Mapped[str] = id_pk()
    journey_id: Mapped[str | None] = mapped_column(
        ForeignKey("recovery_journeys.id"), nullable=True, index=True
    )
    journey: Mapped[RecoveryJourney | None] = relationship(back_populates="decisions")
    event_id: Mapped[str] = mapped_column(ForeignKey("revenue_events.id"), index=True)

    chosen_action: Mapped[ActionType] = mapped_column(String(24), index=True)
    recovery_probability: Mapped[float] = mapped_column(Float, default=0.0)
    organic_probability: Mapped[float] = mapped_column(Float, default=0.0)
    uplift: Mapped[float] = mapped_column(Float, default=0.0)
    expected_recovery_paise: Mapped[int] = mapped_column(Integer, default=0)
    expected_value_paise: Mapped[int] = mapped_column(Integer, default=0)

    policy_verdict: Mapped[PolicyVerdict] = mapped_column(String(20), index=True)
    policy_reasons: Mapped[list[Any]] = mapped_column(default=list)
    alternatives: Mapped[list[Any]] = mapped_column(default=list)
    rationale: Mapped[list[Any]] = mapped_column(default=list)
    evidence: Mapped[list[Any]] = mapped_column(default=list)
    agent_trace: Mapped[list[Any]] = mapped_column(default=list)

    model_version: Mapped[str] = mapped_column(String(48), default="heuristic")
    reasoning_provider: Mapped[str] = mapped_column(String(24), default="deterministic")
