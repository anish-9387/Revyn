"""Shared agent context and trace.

The trace is what makes an autonomous decision auditable: every agent records what it
concluded and why, and the whole list is persisted on the decision row.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.clock import utcnow
from app.core.constants import ActionType, AgentName, PolicyVerdict
from app.engines.decision import DecisionOutcome
from app.engines.degradation import DegradationState
from app.engines.risk import RiskAssessment
from app.engines.root_cause import Diagnosis
from app.ml.predictor import ActionProbabilities
from app.models.customer import Customer
from app.models.event import RevenueEvent
from app.models.journey import RecoveryJourney
from app.services.policy import BudgetState, PolicyEngine


@dataclass(slots=True)
class AgentStep:
    agent: AgentName
    summary: str
    detail: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def as_dict(self) -> dict[str, Any]:
        return {
            "agent": str(self.agent),
            "summary": self.summary,
            "detail": self.detail,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass(slots=True)
class AgentTrace:
    steps: list[AgentStep] = field(default_factory=list)

    def add(
        self,
        agent: AgentName,
        summary: str,
        detail: dict[str, Any] | None = None,
        started: float = 0.0,
    ) -> None:
        self.steps.append(
            AgentStep(
                agent=agent,
                summary=summary,
                detail=detail or {},
                duration_ms=(time.perf_counter() - started) * 1000 if started else 0.0,
            )
        )

    def as_list(self) -> list[dict[str, Any]]:
        return [step.as_dict() for step in self.steps]


@dataclass(slots=True)
class RecoveryContext:
    """Carries state through the agent chain for one revenue-loss event."""

    session: AsyncSession
    event: RevenueEvent
    customer: Customer
    policy: PolicyEngine
    degradation: DegradationState
    budget: BudgetState
    now: datetime = field(default_factory=utcnow)
    journey: RecoveryJourney | None = None
    trace: AgentTrace = field(default_factory=AgentTrace)

    risk: RiskAssessment | None = None
    diagnosis: Diagnosis | None = None
    probabilities: ActionProbabilities | None = None
    decision: DecisionOutcome | None = None
    verdict: PolicyVerdict = PolicyVerdict.ALLOW
    verdict_reasons: list[str] = field(default_factory=list)
    learned_rates: dict[ActionType, float] = field(default_factory=dict)
    proposed_order: list[ActionType] = field(default_factory=list)
    strategy_notes: str = ""
    reasoning_provider: str = "deterministic"
    # Narrative refinement is opt-in per event so bulk passes stay fast and cheap.
    allow_reasoner: bool = True
    worth_pursuing: bool = True
    skip_reason: str = ""

    @property
    def degraded_route(self) -> bool:
        health = self.degradation.routes.get(self.event.route)
        return bool(health and health.degraded)

    @property
    def systemic_signal(self):
        return self.degradation.signal_for(self.event.route, str(self.event.payment_method))


class Agent(Protocol):
    name: AgentName

    async def run(self, ctx: RecoveryContext) -> None: ...
