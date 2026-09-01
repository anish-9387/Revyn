"""Agent chain for the planning half of the loop.

    Sentinel -> Investigator -> Strategist -> Optimizer -> Policy Officer

Execution, verification and learning are driven by the orchestrator as outcomes arrive,
because those steps are event-driven rather than part of a single synchronous pass.
"""

from __future__ import annotations

from app.agents.base import RecoveryContext
from app.agents.investigator import Investigator
from app.agents.optimizer import Optimizer
from app.agents.policy_officer import PolicyOfficer
from app.agents.sentinel import Sentinel
from app.agents.strategist import Strategist
from app.core.constants import AgentName


class RecoveryPipeline:
    """Runs the planning agents in order and short-circuits on a Sentinel skip."""

    def __init__(self) -> None:
        self.sentinel = Sentinel()
        self.investigator = Investigator()
        self.strategist = Strategist()
        self.optimizer = Optimizer()
        self.policy_officer = PolicyOfficer()

    async def plan(self, ctx: RecoveryContext) -> RecoveryContext:
        await self.sentinel.run(ctx)
        if not ctx.worth_pursuing:
            ctx.trace.add(AgentName.SENTINEL, f"Stopping early: {ctx.skip_reason}")
            return ctx
        await self.investigator.run(ctx)
        await self.strategist.run(ctx)
        await self.optimizer.run(ctx)
        await self.policy_officer.run(ctx)
        return ctx
