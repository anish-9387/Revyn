"""Customer intelligence: value, behaviour and contact preferences."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import CommunicationPreference, CustomerSegment, PaymentMethod
from app.core.db import Base
from app.models.base import TimestampMixin, id_pk

if TYPE_CHECKING:
    from app.models.event import RevenueEvent


class Customer(Base, TimestampMixin):
    __tablename__ = "customers"
    __table_args__ = (Index("ix_customers_segment_ltv", "segment", "ltv_paise"),)

    id: Mapped[str] = id_pk()
    external_ref: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(160))
    phone: Mapped[str] = mapped_column(String(24))

    segment: Mapped[CustomerSegment] = mapped_column(String(16), index=True)
    ltv_paise: Mapped[int] = mapped_column(Integer, default=0)
    average_order_value_paise: Mapped[int] = mapped_column(Integer, default=0)
    purchase_frequency: Mapped[float] = mapped_column(Float, default=0.0)
    preferred_payment_method: Mapped[PaymentMethod] = mapped_column(String(20))
    communication_preference: Mapped[CommunicationPreference] = mapped_column(String(16))

    previous_payment_count: Mapped[int] = mapped_column(Integer, default=0)
    previous_success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    historical_recovery_rate: Mapped[float] = mapped_column(Float, default=0.0)
    tenure_days: Mapped[int] = mapped_column(Integer, default=0)

    opted_out: Mapped[bool] = mapped_column(Boolean, default=False)
    # Contacts already spent outside Revyn, folded into the friction budget.
    lifetime_contacts: Mapped[int] = mapped_column(Integer, default=0)

    events: Mapped[list[RevenueEvent]] = relationship(back_populates="customer")

    @property
    def value_weight(self) -> float:
        """Multiplier applied to priority and friction tolerance."""
        return {
            CustomerSegment.VIP: 1.6,
            CustomerSegment.HIGH: 1.3,
            CustomerSegment.MEDIUM: 1.0,
            CustomerSegment.LOW: 0.8,
            CustomerSegment.NEW: 0.9,
        }[CustomerSegment(self.segment)]
