"""Contracts for the reasoning layer.

Every provider returns a validated structure drawn from a closed vocabulary supplied in
the prompt. A provider may decline by returning ``None``, in which case the deterministic
engine result stands. That is what keeps the model out of the execution path.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, Field


class CauseNarrative(BaseModel):
    """Refined diagnosis. ``cause`` must be one of the candidates given in the prompt."""

    cause: str
    confidence: float = Field(ge=0.0, le=1.0)
    headline: str = Field(max_length=140)
    explanation: str = Field(max_length=600)
    evidence: list[str] = Field(default_factory=list, max_length=5)


class RankedAction(BaseModel):
    action: str
    reason: str = Field(max_length=220)
    suggested_delay_minutes: float = Field(ge=0.0, le=4320.0)


class StrategyProposal(BaseModel):
    """A shortlist of candidate journeys, still subject to pricing and the policy gate."""

    ranked_actions: list[RankedAction] = Field(default_factory=list, max_length=4)
    stop_condition: str = Field(default="", max_length=220)
    notes: str = Field(default="", max_length=400)


class LeakageInsights(BaseModel):
    insights: list[str] = Field(default_factory=list, max_length=5)


class PromiseExtraction(BaseModel):
    """Promise-to-pay intelligence pulled out of a customer conversation."""

    promised: bool
    promise_date: str | None = None
    amount_rupees: float | None = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    quote: str = Field(default="", max_length=240)


class ReasoningProvider(Protocol):
    name: str

    async def diagnose(self, context: dict) -> CauseNarrative | None: ...

    async def propose_strategy(self, context: dict) -> StrategyProposal | None: ...

    async def summarise_leakage(self, context: dict) -> LeakageInsights | None: ...

    async def extract_promise(self, transcript: str, context: dict) -> PromiseExtraction | None: ...

    async def close(self) -> None: ...
