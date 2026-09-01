"""Agent 4 - Optimizer. Prices every candidate and picks the highest expected value."""

from __future__ import annotations

import time

from app.agents.base import RecoveryContext
from app.core.constants import AgentName, EventKind
from app.core.money import format_inr
from app.data.catalog import ALLOWED_ACTIONS
from app.engines.decision import DecisionInputs, decide
from app.engines.risk import priority
from app.ml.predictor import get_predictor


class Optimizer:
    name = AgentName.OPTIMIZER

    async def run(self, ctx: RecoveryContext) -> None:
        started = time.perf_counter()
        from app.engines.features import FeatureContext, build_features

        signal = ctx.systemic_signal
        features = build_features(
            ctx.event,
            ctx.customer,
            FeatureContext(
                degradation_active=signal.route_degraded,
                degradation_ratio=signal.route_ratio,
                method_failure_rate=signal.method_ratio,
            ),
        )
        predictor = get_predictor()
        probabilities = predictor.score(features, list(ALLOWED_ACTIONS[EventKind(ctx.event.kind)]))
        ctx.probabilities = probabilities

        spec = ctx.policy.spec
        gate = ctx.policy.gate_for(
            event=ctx.event,
            customer=ctx.customer,
            budget=ctx.budget,
            degraded_route=ctx.degraded_route,
            now=ctx.now,
        )
        outcome = decide(
            DecisionInputs(
                event=ctx.event,
                customer=ctx.customer,
                diagnosis=ctx.diagnosis,
                risk=ctx.risk,
                probabilities=probabilities,
                contacts_used=ctx.event.prior_contacts + ctx.budget.contacts_used,
                customer_contact_budget=spec.max_contacts,
                degraded_route=ctx.degraded_route,
                min_confidence=spec.min_confidence,
                min_expected_value_paise=spec.min_expected_value_paise,
                max_discount_pct=spec.max_discount_pct,
                learned_rates=ctx.learned_rates,
                model_version=predictor.version,
            ),
            gate,
        )
        ctx.decision = outcome

        chosen = outcome.chosen
        ctx.event.recovery_probability = chosen.probability
        ctx.event.organic_probability = probabilities.organic
        ctx.event.expected_recovery_paise = chosen.expected_recovery_paise
        ctx.event.priority_score = priority(chosen.expected_recovery_paise, ctx.risk, ctx.customer)

        ctx.trace.add(
            self.name,
            f"{chosen.label} at {chosen.probability:.0%} recovery, "
            f"{format_inr(chosen.expected_value_paise)} incremental value",
            {
                "organic_probability": round(probabilities.organic, 4),
                "model_version": predictor.version,
                "ranked": [
                    {
                        "action": str(option.action),
                        "probability": round(option.probability, 4),
                        "expected_value_paise": option.expected_value_paise,
                        "verdict": str(option.verdict),
                    }
                    for option in outcome.options[:6]
                ],
            },
            started,
        )
