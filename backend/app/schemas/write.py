"""Request payloads. Every mutation the dashboard can perform is typed here."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ApprovalRequest(BaseModel):
    approver: str = Field(default="merchant", max_length=64)
    note: str = Field(default="", max_length=280)


class RejectionRequest(BaseModel):
    approver: str = Field(default="merchant", max_length=64)
    reason: str = Field(default="", max_length=280)


class JourneyActionRequest(BaseModel):
    actor: str = Field(default="merchant", max_length=64)
    reason: str = Field(default="", max_length=280)


class KillSwitchRequest(BaseModel):
    enabled: bool
    actor: str = Field(default="merchant", max_length=64)


class PolicyUpdate(BaseModel):
    """Partial update. Only the supplied fields are written."""

    name: str | None = Field(default=None, max_length=80)
    automation_enabled: bool | None = None
    paused: bool | None = None
    max_contacts: int | None = Field(default=None, ge=0, le=10)
    max_retries: int | None = Field(default=None, ge=0, le=6)
    max_discount_offers: int | None = Field(default=None, ge=0, le=4)
    max_voice_attempts: int | None = Field(default=None, ge=0, le=4)
    human_approval_amount_paise: int | None = Field(default=None, ge=0)
    discount_approval_pct: float | None = Field(default=None, ge=0, le=100)
    voice_approval_amount_paise: int | None = Field(default=None, ge=0)
    min_confidence: float | None = Field(default=None, ge=0, le=1)
    min_expected_value_paise: int | None = Field(default=None, ge=0)
    retry_delay_minutes: int | None = Field(default=None, ge=0, le=1440)
    followup_delay_hours: float | None = Field(default=None, ge=0, le=168)
    contact_cooldown_minutes: int | None = Field(default=None, ge=0, le=1440)
    journey_ttl_hours: float | None = Field(default=None, ge=1, le=720)
    quiet_hours_start: int | None = Field(default=None, ge=0, le=23)
    quiet_hours_end: int | None = Field(default=None, ge=0, le=23)
    quiet_hours_enforced: bool | None = None
    degradation_retry_guard: bool | None = None
    max_discount_pct: float | None = Field(default=None, ge=0, le=60)
    npci_max_attempts: int | None = Field(default=None, ge=1, le=10)
    execution_window_guard: bool | None = None
    pdn_lead_hours: float | None = Field(default=None, ge=0, le=72)
    first_presentation_min_confidence: float | None = Field(default=None, ge=0, le=1)
    afa_free_ceiling_paise: int | None = Field(default=None, ge=0)


class SimulationRequest(BaseModel):
    """Policy overrides to evaluate against the current open book."""

    overrides: PolicyUpdate = Field(default_factory=PolicyUpdate)
    sample_limit: int = Field(default=400, ge=10, le=2000)


class SeedRequest(BaseModel):
    reset: bool = True
    customers: int | None = Field(default=None, ge=50, le=10_000)
    transactions: int | None = Field(default=None, ge=200, le=50_000)
    train_model: bool = True


class TimeoutInjectionRequest(BaseModel):
    """Arms the graceful-failure demo: the next N gateway calls will not resolve."""

    count: int = Field(default=1, ge=1, le=20)
    payment_already_succeeded: bool = True


class PromiseRequest(BaseModel):
    transcript: str = Field(min_length=4, max_length=2000)
