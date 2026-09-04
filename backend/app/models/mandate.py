from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import MandateRail, MandateStatus
from app.core.db import Base
from app.models.base import TimestampMixin, id_pk, utc_column


class Mandate(Base, TimestampMixin):
    __tablename__ = "mandates"

    id: Mapped[str] = id_pk()
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    external_ref: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    rail: Mapped[MandateRail] = mapped_column(String(20))
    status: Mapped[MandateStatus] = mapped_column(String(24), default=MandateStatus.ACTIVE)
    max_amount_paise: Mapped[int] = mapped_column(Integer, default=15_000_00)
    sequence_number: Mapped[int] = mapped_column(Integer, default=1)
    attempts_used: Mapped[int] = mapped_column(Integer, default=0)
    last_pdn_sent_at: Mapped[datetime | None] = utc_column(nullable=True)
    registered_at: Mapped[datetime | None] = utc_column(nullable=True)
    revoked_at: Mapped[datetime | None] = utc_column(nullable=True)
    next_due_at: Mapped[datetime | None] = utc_column(nullable=True)
