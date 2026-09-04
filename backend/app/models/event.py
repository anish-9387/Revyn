"""A single unit of revenue at risk, whatever loss class produced it."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import (
    ActionType,
    CauseLayer,
    Cohort,
    EventKind,
    EventStatus,
    FailureCode,
    PaymentMethod,
    RootCause,
)
from app.core.db import Base
from app.models.base import TimestampMixin, id_pk, utc_column

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.journey import RecoveryJourney


class RevenueEvent(Base, TimestampMixin):
    """Failed payment, abandoned cart, failed renewal or overdue invoice.

    Rows flagged ``is_training`` are resolved history used to fit and calibrate the
    recovery model; the rest are live opportunities the orchestrator works on.
    """

    __tablename__ = "revenue_events"
    __table_args__ = (
        Index("ix_events_status_priority", "status", "priority_score"),
        Index("ix_events_kind_occurred", "kind", "occurred_at"),
        Index("ix_events_training_kind", "is_training", "kind"),
    )

    id: Mapped[str] = id_pk()
    external_ref: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    kind: Mapped[EventKind] = mapped_column(String(24), index=True)
    status: Mapped[EventStatus] = mapped_column(String(16), default=EventStatus.AT_RISK, index=True)
    cohort: Mapped[Cohort] = mapped_column(String(12), default=Cohort.TREATMENT, index=True)
    is_training: Mapped[bool] = mapped_column(Boolean, default=False, index=True)

    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    customer: Mapped[Customer] = relationship(back_populates="events", lazy="joined")
    mandate_id: Mapped[str | None] = mapped_column(ForeignKey("mandates.id"), nullable=True, index=True)

    amount_paise: Mapped[int] = mapped_column(Integer)
    occurred_at: Mapped[datetime] = utc_column(index=True)
    resolved_at: Mapped[datetime | None] = utc_column(nullable=True)
    due_date: Mapped[datetime | None] = utc_column(nullable=True)

    payment_method: Mapped[PaymentMethod] = mapped_column(String(20), index=True)
    issuer: Mapped[str] = mapped_column(String(48), index=True)
    # Gateway route the attempt travelled through; the unit degradation is scoped to.
    route: Mapped[str] = mapped_column(String(48), index=True)
    failure_code: Mapped[FailureCode | None] = mapped_column(String(32), nullable=True, index=True)
    failure_reason: Mapped[str | None] = mapped_column(String(240), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    prior_contacts: Mapped[int] = mapped_column(Integer, default=0)

    checkout_duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cart_items: Mapped[int | None] = mapped_column(Integer, nullable=True)

    order_ref: Mapped[str | None] = mapped_column(String(48), nullable=True)
    payment_ref: Mapped[str | None] = mapped_column(String(48), nullable=True)
    subscription_ref: Mapped[str | None] = mapped_column(String(48), nullable=True)
    invoice_ref: Mapped[str | None] = mapped_column(String(48), nullable=True)

    # Scores written by the risk, prediction and decision engines.
    risk_score: Mapped[float] = mapped_column(Float, default=0.0)
    urgency_score: Mapped[float] = mapped_column(Float, default=0.0)
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    recovery_probability: Mapped[float] = mapped_column(Float, default=0.0)
    organic_probability: Mapped[float] = mapped_column(Float, default=0.0)
    expected_recovery_paise: Mapped[int] = mapped_column(Integer, default=0)

    root_cause: Mapped[RootCause] = mapped_column(String(32), default=RootCause.UNKNOWN, index=True)
    cause_layer: Mapped[CauseLayer | None] = mapped_column(String(16), nullable=True)
    cause_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    diagnosis: Mapped[dict[str, Any]] = mapped_column(default=dict)

    # Outcome. On training rows this is observed history; on live rows Revyn writes it.
    applied_action: Mapped[ActionType | None] = mapped_column(String(24), nullable=True, index=True)
    recovered_amount_paise: Mapped[int] = mapped_column(Integer, default=0)
    recovery_cost_paise: Mapped[int] = mapped_column(Integer, default=0)
    contacts_used: Mapped[int] = mapped_column(Integer, default=0)

    journeys: Mapped[list[RecoveryJourney]] = relationship(back_populates="event")

    @property
    def is_open(self) -> bool:
        return self.status in (EventStatus.AT_RISK, EventStatus.IN_RECOVERY)
