"""Guardrail and Policy Engine.

The reasoning layer proposes; this module decides. It is pure, deterministic and reads
nothing but the policy row, the journey budget and the event itself - which is what makes
"the LLM never touches a financial API directly" an architectural property rather than a
convention.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from typing import Any

from app.core.clock import as_utc, utcnow
from app.core.constants import (
    ActionType,
    EventStatus,
    PolicyRule,
    PolicyVerdict,
)
from app.data.catalog import intervention
from app.engines.decision import GateVerdict
from app.engines.features import IST_OFFSET_HOURS
from app.models.customer import Customer
from app.models.event import RevenueEvent
from app.models.policy import PolicyConfig


@dataclass(slots=True, frozen=True)
class PolicySpec:
    """Serialisable snapshot of a policy, so simulations can vary it without writes."""

    automation_enabled: bool = True
    paused: bool = False
    max_contacts: int = 3
    max_retries: int = 2
    max_discount_offers: int = 1
    max_voice_attempts: int = 1
    human_approval_amount_paise: int = 10_000_00
    discount_approval_pct: float = 10.0
    voice_approval_amount_paise: int = 25_000_00
    min_confidence: float = 0.12
    min_expected_value_paise: int = 50_00
    retry_delay_minutes: int = 25
    followup_delay_hours: float = 6.0
    contact_cooldown_minutes: int = 45
    journey_ttl_hours: float = 72.0
    quiet_hours_start: int = 21
    quiet_hours_end: int = 8
    quiet_hours_enforced: bool = False
    degradation_retry_guard: bool = True
    max_discount_pct: float = 15.0

    @classmethod
    def from_model(cls, config: PolicyConfig) -> PolicySpec:
        return cls(
            automation_enabled=config.automation_enabled,
            paused=config.paused,
            max_contacts=config.max_contacts,
            max_retries=config.max_retries,
            max_discount_offers=config.max_discount_offers,
            max_voice_attempts=config.max_voice_attempts,
            human_approval_amount_paise=config.human_approval_amount_paise,
            discount_approval_pct=config.discount_approval_pct,
            voice_approval_amount_paise=config.voice_approval_amount_paise,
            min_confidence=config.min_confidence,
            min_expected_value_paise=config.min_expected_value_paise,
            retry_delay_minutes=config.retry_delay_minutes,
            followup_delay_hours=config.followup_delay_hours,
            contact_cooldown_minutes=config.contact_cooldown_minutes,
            journey_ttl_hours=config.journey_ttl_hours,
            quiet_hours_start=config.quiet_hours_start,
            quiet_hours_end=config.quiet_hours_end,
            quiet_hours_enforced=config.quiet_hours_enforced,
            degradation_retry_guard=config.degradation_retry_guard,
            max_discount_pct=config.max_discount_pct,
        )

    def with_overrides(self, overrides: dict[str, Any]) -> PolicySpec:
        known = {
            k: v for k, v in overrides.items() if k in self.__dataclass_fields__ and v is not None
        }
        return replace(self, **known)

    def as_dict(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.__dataclass_fields__}


@dataclass(slots=True)
class BudgetState:
    """What this journey has already spent from the customer friction budget."""

    contacts_used: int = 0
    retries_used: int = 0
    discounts_used: int = 0
    voice_used: int = 0
    last_contact_at: datetime | None = None
    journey_paused: bool = False
    journey_started_at: datetime | None = None


@dataclass(slots=True)
class FrictionBudget:
    contacts: tuple[int, int]
    retries: tuple[int, int]
    discounts: tuple[int, int]
    voice: tuple[int, int]
    exhausted: bool
    blocking: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "contacts": {"used": self.contacts[0], "limit": self.contacts[1]},
            "retries": {"used": self.retries[0], "limit": self.retries[1]},
            "discounts": {"used": self.discounts[0], "limit": self.discounts[1]},
            "voice": {"used": self.voice[0], "limit": self.voice[1]},
            "exhausted": self.exhausted,
            "blocking": self.blocking,
        }


class PolicyEngine:
    def __init__(self, spec: PolicySpec) -> None:
        self.spec = spec

    def evaluate(
        self,
        action: ActionType,
        *,
        event: RevenueEvent,
        customer: Customer,
        budget: BudgetState,
        discount_pct: float = 0.0,
        degraded_route: bool = False,
        now: datetime | None = None,
    ) -> GateVerdict:
        now = now or utcnow()
        if action is ActionType.DO_NOTHING:
            return GateVerdict(verdict=PolicyVerdict.ALLOW)

        blocks: list[PolicyRule] = []
        approvals: list[PolicyRule] = []
        spec = self.spec
        details = intervention(action)

        if not spec.automation_enabled:
            blocks.append(PolicyRule.AUTOMATION_DISABLED)
        if spec.paused or budget.journey_paused:
            blocks.append(PolicyRule.JOURNEY_PAUSED)
        if event.status == EventStatus.RECOVERED:
            blocks.append(PolicyRule.ALREADY_RECOVERED)

        if details.consumes_contact:
            if customer.opted_out:
                blocks.append(PolicyRule.CUSTOMER_OPTED_OUT)
            if event.prior_contacts + budget.contacts_used >= spec.max_contacts:
                blocks.append(PolicyRule.CONTACT_BUDGET_EXHAUSTED)
            if self._in_cooldown(budget, now):
                blocks.append(PolicyRule.COOLDOWN_ACTIVE)
            if spec.quiet_hours_enforced and self._in_quiet_hours(now):
                blocks.append(PolicyRule.QUIET_HOURS)

        if action is ActionType.RETRY_PAYMENT:
            if event.retry_count + budget.retries_used >= spec.max_retries:
                blocks.append(PolicyRule.RETRY_BUDGET_EXHAUSTED)
            if degraded_route and spec.degradation_retry_guard:
                blocks.append(PolicyRule.DEGRADATION_ACTIVE)
        if action is ActionType.DISCOUNT and budget.discounts_used >= spec.max_discount_offers:
            blocks.append(PolicyRule.DISCOUNT_BUDGET_EXHAUSTED)
        if action is ActionType.VOICE and budget.voice_used >= spec.max_voice_attempts:
            blocks.append(PolicyRule.VOICE_BUDGET_EXHAUSTED)

        if blocks:
            return GateVerdict(verdict=PolicyVerdict.BLOCK, reasons=blocks)

        if details.touches_gateway and event.amount_paise >= spec.human_approval_amount_paise:
            approvals.append(PolicyRule.HIGH_VALUE_APPROVAL)
        if discount_pct > spec.discount_approval_pct:
            approvals.append(PolicyRule.DISCOUNT_APPROVAL)
        if action is ActionType.VOICE and event.amount_paise >= spec.voice_approval_amount_paise:
            approvals.append(PolicyRule.VOICE_APPROVAL)
        if action is ActionType.HUMAN_ESCALATION:
            approvals.append(PolicyRule.HIGH_VALUE_APPROVAL)

        if approvals:
            return GateVerdict(verdict=PolicyVerdict.REQUIRE_APPROVAL, reasons=approvals)
        return GateVerdict(verdict=PolicyVerdict.ALLOW)

    def gate_for(
        self,
        *,
        event: RevenueEvent,
        customer: Customer,
        budget: BudgetState,
        degraded_route: bool = False,
        now: datetime | None = None,
    ):
        """Bind the context so the decision engine can price options against real limits."""

        def gate(action: ActionType, *, discount_pct: float = 0.0) -> GateVerdict:
            return self.evaluate(
                action,
                event=event,
                customer=customer,
                budget=budget,
                discount_pct=discount_pct,
                degraded_route=degraded_route,
                now=now,
            )

        return gate

    def friction_budget(self, event: RevenueEvent, budget: BudgetState) -> FrictionBudget:
        spec = self.spec
        contacts = (event.prior_contacts + budget.contacts_used, spec.max_contacts)
        retries = (event.retry_count + budget.retries_used, spec.max_retries)
        discounts = (budget.discounts_used, spec.max_discount_offers)
        voice = (budget.voice_used, spec.max_voice_attempts)
        blocking = [
            name
            for name, (used, limit) in {
                "contacts": contacts,
                "retries": retries,
                "discounts": discounts,
                "voice": voice,
            }.items()
            if used >= limit
        ]
        return FrictionBudget(
            contacts=contacts,
            retries=retries,
            discounts=discounts,
            voice=voice,
            exhausted=contacts[0] >= contacts[1] and retries[0] >= retries[1],
            blocking=blocking,
        )

    def _in_cooldown(self, budget: BudgetState, now: datetime) -> bool:
        if budget.last_contact_at is None:
            return False
        elapsed = now - as_utc(budget.last_contact_at)
        return elapsed < timedelta(minutes=self.spec.contact_cooldown_minutes)

    def _in_quiet_hours(self, now: datetime) -> bool:
        hour = (as_utc(now).hour + IST_OFFSET_HOURS) % 24
        start, end = self.spec.quiet_hours_start, self.spec.quiet_hours_end
        if start > end:  # window wraps past midnight
            return hour >= start or hour < end
        return start <= hour < end


RULE_EXPLANATIONS: dict[PolicyRule, str] = {
    PolicyRule.AUTOMATION_DISABLED: "Recovery automation is off at the merchant kill switch",
    PolicyRule.JOURNEY_PAUSED: "This recovery journey is paused",
    PolicyRule.CUSTOMER_OPTED_OUT: "Customer has opted out of recovery communication",
    PolicyRule.CONTACT_BUDGET_EXHAUSTED: "Customer contact budget is exhausted",
    PolicyRule.RETRY_BUDGET_EXHAUSTED: "Payment retry budget is exhausted",
    PolicyRule.DISCOUNT_BUDGET_EXHAUSTED: "Discount offer budget is exhausted",
    PolicyRule.VOICE_BUDGET_EXHAUSTED: "Voice attempt budget is exhausted",
    PolicyRule.COOLDOWN_ACTIVE: "Another contact was made inside the cooldown window",
    PolicyRule.QUIET_HOURS: "Outside the permitted contact window",
    PolicyRule.HIGH_VALUE_APPROVAL: "Amount is above the human approval threshold",
    PolicyRule.DISCOUNT_APPROVAL: "Discount exceeds the auto-approved percentage",
    PolicyRule.VOICE_APPROVAL: "Voice contact on a high-value case needs sign-off",
    PolicyRule.CONFIDENCE_BELOW_THRESHOLD: "Recovery confidence is below the policy floor",
    PolicyRule.VALUE_BELOW_THRESHOLD: "Expected value is below the policy floor",
    PolicyRule.ALREADY_RECOVERED: "Payment has already succeeded",
    PolicyRule.DEGRADATION_ACTIVE: "Payment route is degrading, so retries are suspended",
    PolicyRule.DUPLICATE_ACTION: "An identical action was already executed",
    PolicyRule.COLLISION_DETECTED: "Another journey already owns this customer",
}


def explain(reasons: list[str]) -> list[str]:
    out: list[str] = []
    for reason in reasons:
        try:
            out.append(RULE_EXPLANATIONS[PolicyRule(reason)])
        except ValueError:
            out.append(reason)
    return out


async def get_active_policy(session) -> PolicyConfig:
    """Fetch the active policy row, creating the default on first use."""
    from sqlalchemy import select

    config = (
        await session.execute(select(PolicyConfig).where(PolicyConfig.active.is_(True)).limit(1))
    ).scalar_one_or_none()
    if config is None:
        config = PolicyConfig()
        session.add(config)
        await session.flush()
    return config


async def load_engine(session) -> PolicyEngine:
    return PolicyEngine(PolicySpec.from_model(await get_active_policy(session)))
