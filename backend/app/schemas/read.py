"""Response models for the dashboard API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from app.core.constants import (
    ActionStatus,
    ActionType,
    CauseLayer,
    Cohort,
    CustomerSegment,
    EventKind,
    EventStatus,
    JourneyState,
    PaymentMethod,
    PolicyVerdict,
    RootCause,
)
from app.schemas.common import ApiModel


class CustomerRead(ApiModel):
    id: str
    external_ref: str
    name: str
    email: str
    phone: str
    segment: CustomerSegment
    ltv_paise: int
    average_order_value_paise: int
    previous_payment_count: int
    previous_success_rate: float
    historical_recovery_rate: float
    communication_preference: str
    opted_out: bool


class RiskItem(ApiModel):
    """One row of the Revenue Risk Radar."""

    id: str
    external_ref: str
    kind: EventKind
    status: EventStatus
    cohort: Cohort
    amount_paise: int
    occurred_at: datetime
    payment_method: PaymentMethod
    issuer: str
    route: str
    failure_code: str | None
    failure_reason: str | None
    retry_count: int
    risk_score: float
    urgency_score: float
    priority_score: float
    recovery_probability: float
    organic_probability: float
    expected_recovery_paise: int
    root_cause: RootCause
    cause_layer: CauseLayer | None
    cause_confidence: float
    recovered_amount_paise: int
    customer: CustomerRead
    recommended_action: str | None = None
    journey_id: str | None = None
    journey_state: JourneyState | None = None


class ActionRead(ApiModel):
    id: str
    journey_id: str
    decision_id: str | None
    sequence: int
    action_type: ActionType
    status: ActionStatus
    scheduled_at: datetime
    executed_at: datetime | None
    cost_paise: int
    friction_score: float
    discount_pct: float
    provider_ref: str | None
    blocked_reasons: list[str] = Field(default_factory=list)
    error: str | None = None
    result: dict[str, Any] = Field(default_factory=dict)


class DecisionRead(ApiModel):
    """The recovery confidence ledger entry for one decision."""

    id: str
    event_id: str
    #: The event this choice was about, so a log row names the money it moved.
    event_ref: str | None = None
    amount_paise: int | None = None
    journey_id: str | None
    chosen_action: ActionType
    recovery_probability: float
    organic_probability: float
    uplift: float
    expected_recovery_paise: int
    expected_value_paise: int
    policy_verdict: PolicyVerdict
    policy_reasons: list[str] = Field(default_factory=list)
    alternatives: list[dict[str, Any]] = Field(default_factory=list)
    rationale: list[str] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)
    model_version: str
    reasoning_provider: str
    created_at: datetime


class JourneyRead(ApiModel):
    id: str
    event_id: str
    #: Who and what the journey is about, so a row is not just an opaque id.
    event_ref: str | None = None
    amount_paise: int | None = None
    customer_name: str | None = None
    customer_id: str
    state: JourneyState
    strategy_key: str
    step_index: int
    next_action_at: datetime | None
    closed_at: datetime | None
    close_reason: str | None
    contacts_used: int
    retries_used: int
    discounts_used: int
    voice_used: int
    recovered_amount_paise: int
    cost_paise: int
    promise_date: datetime | None
    promise_confidence: float
    plan: list[dict[str, Any]] = Field(default_factory=list)
    transitions: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime


class JourneyDetail(JourneyRead):
    event: RiskItem
    actions: list[ActionRead] = Field(default_factory=list)
    decisions: list[DecisionRead] = Field(default_factory=list)
    friction_budget: dict[str, Any] = Field(default_factory=dict)


class ApprovalItem(ApiModel):
    action: ActionRead
    journey_id: str
    event: RiskItem
    reasons: list[str] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    decision: DecisionRead | None = None


class LedgerEntryRead(ApiModel):
    id: str
    event_id: str
    journey_id: str | None
    cohort: Cohort
    action: ActionType
    gross_recovered_paise: int
    organic_estimate_paise: int
    cost_paise: int
    incremental_net_paise: int
    attribution_method: str
    organic_probability: float
    created_at: datetime


class AuditRead(ApiModel):
    id: str
    sequence: int
    occurred_at: datetime
    actor: str
    actor_name: str
    event_type: str
    entity_type: str
    entity_id: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    entry_hash: str
    previous_hash: str


class PolicyRead(ApiModel):
    id: str
    name: str
    version: int
    automation_enabled: bool
    paused: bool
    max_contacts: int
    max_retries: int
    max_discount_offers: int
    max_voice_attempts: int
    human_approval_amount_paise: int
    discount_approval_pct: float
    voice_approval_amount_paise: int
    min_confidence: float
    min_expected_value_paise: int
    retry_delay_minutes: int
    followup_delay_hours: float
    contact_cooldown_minutes: int
    journey_ttl_hours: float
    quiet_hours_start: int
    quiet_hours_end: int
    quiet_hours_enforced: bool
    degradation_retry_guard: bool
    max_discount_pct: float
    updated_at: datetime


class DegradationRead(ApiModel):
    id: str
    scope_type: str
    scope_value: str
    status: str
    severity: str
    detected_at: datetime
    resolved_at: datetime | None
    baseline_failure_rate: float
    observed_failure_rate: float
    ratio: float
    affected_events: int
    recommendation: str
    detail: dict[str, Any] = Field(default_factory=dict)
