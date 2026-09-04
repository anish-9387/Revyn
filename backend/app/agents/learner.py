"""Agent 8 - Learner. Folds every verified outcome back into the merchant playbook."""

from __future__ import annotations

import time

from app.agents.base import RecoveryContext
from app.core.constants import ActionType, Actor, AgentName, AuditEvent
from app.data.catalog import intervention
from app.engines import learning
from app.models.journey import RecoveryAction
from app.services import audit


class Learner:
    name = AgentName.LEARNER

    async def run(self, ctx: RecoveryContext, action: RecoveryAction, recovered: bool) -> None:
        started = time.perf_counter()
        action_type = ActionType(action.action_type)
        key = learning.context_key(ctx.event.kind, ctx.event.root_cause, ctx.customer.segment)
        stat = await learning.observe(
            ctx.session,
            key=key,
            action=action_type,
            recovered=recovered,
            amount_paise=ctx.event.recovered_amount_paise,
            cost_paise=action.cost_paise or intervention(action_type).cost_paise,
        )
        await audit.record(
            ctx.session,
            event_type=AuditEvent.STRATEGY_UPDATED,
            entity_type="strategy_stat",
            entity_id=stat.id,
            summary=(
                f"{learning.describe_context(key)}: {intervention(action_type).label} "
                f"now recovers {stat.posterior_mean:.0%} over {stat.trials} trials"
            ),
            payload={
                "context_key": key,
                "action": str(action_type),
                "recovered": recovered,
                "trials": stat.trials,
                "posterior_mean": round(stat.posterior_mean, 4),
            },
            actor=Actor.AGENT,
            actor_name=str(self.name),
        )
        ctx.trace.add(
            self.name,
            f"Playbook: {intervention(action_type).label} at {stat.posterior_mean:.0%} "
            f"over {stat.trials} trials",
            {"context_key": key, "posterior_mean": round(stat.posterior_mean, 4)},
            started,
        )
