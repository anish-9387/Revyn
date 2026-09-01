"""Agent 5 - Policy Officer. The deterministic gate in front of every financial action.

This agent contains no model call and no randomness. It re-evaluates the chosen action
against the live policy, so a decision priced a moment ago cannot execute if the budget has
since been spent or the kill switch has been thrown.
"""

from __future__ import annotations

import time

from app.agents.base import RecoveryContext
from app.core.constants import ActionType, AgentName, PolicyVerdict
from app.services.policy import explain


class PolicyOfficer:
    name = AgentName.POLICY_OFFICER

    async def run(self, ctx: RecoveryContext) -> None:
        started = time.perf_counter()
        chosen = ctx.decision.chosen
        if chosen.action is ActionType.DO_NOTHING:
            ctx.verdict = PolicyVerdict.ALLOW
            ctx.verdict_reasons = []
            ctx.trace.add(
                self.name, "No action proposed, nothing to gate", {"verdict": "allow"}, started
            )
            return

        verdict = ctx.policy.evaluate(
            chosen.action,
            event=ctx.event,
            customer=ctx.customer,
            budget=ctx.budget,
            discount_pct=chosen.discount_pct,
            degraded_route=ctx.degraded_route,
            now=ctx.now,
        )
        ctx.verdict = verdict.verdict
        ctx.verdict_reasons = [str(reason) for reason in verdict.reasons]

        summary = {
            PolicyVerdict.ALLOW: f"{chosen.label} allowed",
            PolicyVerdict.REQUIRE_APPROVAL: f"{chosen.label} needs human approval",
            PolicyVerdict.BLOCK: f"{chosen.label} blocked",
        }[verdict.verdict]
        ctx.trace.add(
            self.name,
            summary,
            {
                "verdict": str(verdict.verdict),
                "reasons": ctx.verdict_reasons,
                "explanations": explain(ctx.verdict_reasons),
                "friction_budget": ctx.policy.friction_budget(ctx.event, ctx.budget).as_dict(),
            },
            started,
        )
