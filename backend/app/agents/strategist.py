"""Agent 3 - Strategist. Assembles the candidate set the optimizer will price.

The candidate set comes from the catalog, never from the model. The reasoning provider can
reorder it and add a stop condition; anything outside the allowed list is discarded.
"""

from __future__ import annotations

import time

from app.agents.base import RecoveryContext
from app.core.constants import ActionType, AgentName, EventKind
from app.core.money import paise_to_rupees
from app.data.catalog import ALLOWED_ACTIONS, intervention
from app.engines import learning
from app.integrations.llm import get_reasoner


class Strategist:
    name = AgentName.STRATEGIST

    async def run(self, ctx: RecoveryContext) -> None:
        started = time.perf_counter()
        key = learning.context_key(ctx.event.kind, ctx.event.root_cause, ctx.customer.segment)
        ctx.learned_rates = await learning.learned_rates(ctx.session, key)
        allowed = ALLOWED_ACTIONS[EventKind(ctx.event.kind)]

        proposal = (
            await get_reasoner().propose_strategy(self._context(ctx, allowed, key))
            if ctx.allow_reasoner
            else None
        )
        if proposal is not None:
            valid = [
                ActionType(item.action)
                for item in proposal.ranked_actions
                if item.action in {str(a) for a in allowed}
            ]
            ctx.proposed_order = valid
            ctx.strategy_notes = proposal.stop_condition or proposal.notes

        ctx.trace.add(
            self.name,
            f"{len(allowed)} candidate actions, {len(ctx.learned_rates)} with learned rates",
            {
                "context_key": key,
                "allowed_actions": [str(a) for a in allowed],
                "learned_rates": {str(k): round(v, 3) for k, v in ctx.learned_rates.items()},
                "proposed_order": [str(a) for a in ctx.proposed_order],
                "stop_condition": ctx.strategy_notes,
            },
            started,
        )

    @staticmethod
    def _context(ctx: RecoveryContext, allowed: tuple[ActionType, ...], key: str) -> dict:
        budget = ctx.policy.friction_budget(ctx.event, ctx.budget)
        return {
            "loss_class": str(ctx.event.kind),
            "amount_rupees": round(paise_to_rupees(ctx.event.amount_paise), 2),
            "diagnosis": {
                "cause": str(ctx.diagnosis.cause) if ctx.diagnosis else "unknown",
                "label": ctx.diagnosis.label if ctx.diagnosis else "",
                "confidence": round(ctx.diagnosis.confidence, 3) if ctx.diagnosis else 0.0,
                "transient": ctx.diagnosis.transient if ctx.diagnosis else False,
                "retryable": ctx.diagnosis.retryable if ctx.diagnosis else False,
            },
            "customer": {
                "segment": str(ctx.customer.segment),
                "communication_preference": str(ctx.customer.communication_preference),
                "opted_out": ctx.customer.opted_out,
                "historical_recovery_rate": ctx.customer.historical_recovery_rate,
            },
            "friction_budget": budget.as_dict(),
            "route_degraded": ctx.degraded_route,
            "merchant_learned_rates": {
                str(action): round(rate, 3) for action, rate in ctx.learned_rates.items()
            },
            "context_key": key,
            "allowed_actions": [
                {
                    "action": str(action),
                    "label": intervention(action).label,
                    "cost_rupees": round(paise_to_rupees(intervention(action).cost_paise), 2),
                    "friction_score": intervention(action).friction_score,
                    "consumes_contact": intervention(action).consumes_contact,
                }
                for action in allowed
            ],
        }
