"""Recovery Counterfactual Engine.

Gross recovery flatters every recovery product, because some of that money was always
going to arrive. Two independent estimates of the organic rate are kept and blended:

* cohort - the measured recovery rate of the untouched control holdout, per loss class
* model  - the ``P(recover | do nothing)`` the predictor produced for that exact event

The cohort estimate is unbiased but coarse; the model estimate is event-specific but relies
on the model being calibrated. Blending them is more defensible than trusting either alone.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import AttributionMethod, Cohort, EventKind, EventStatus
from app.models.event import RevenueEvent

#: Control observations needed before the cohort rate is trusted for a loss class.
MIN_COHORT_SAMPLE = 40


@dataclass(slots=True)
class CohortRates:
    by_kind: dict[str, tuple[float, int]]
    overall: tuple[float, int]

    def rate_for(self, kind: EventKind | str) -> tuple[float, int]:
        return self.by_kind.get(str(kind), self.overall)


async def cohort_organic_rates(session: AsyncSession) -> CohortRates:
    """Recovery rate among control-cohort events, which received no intervention."""
    recovered = func.sum(case((RevenueEvent.status == EventStatus.RECOVERED, 1), else_=0))
    stmt = (
        select(RevenueEvent.kind, func.count(RevenueEvent.id), recovered)
        .where(
            RevenueEvent.cohort == Cohort.CONTROL,
            RevenueEvent.status.in_([EventStatus.RECOVERED, EventStatus.LOST]),
        )
        .group_by(RevenueEvent.kind)
    )
    rows = (await session.execute(stmt)).all()
    by_kind = {
        str(kind): ((int(hits or 0) / int(total)) if total else 0.0, int(total))
        for kind, total, hits in rows
    }
    total_count = sum(count for _, count in by_kind.values())
    total_rate = (
        sum(rate * count for rate, count in by_kind.values()) / total_count if total_count else 0.0
    )
    return CohortRates(by_kind=by_kind, overall=(total_rate, total_count))


def organic_estimate(
    *,
    amount_paise: int,
    model_probability: float,
    cohort: CohortRates,
    kind: EventKind | str,
) -> tuple[int, float, AttributionMethod]:
    """Rupees of this recovery that should not be claimed as incremental."""
    cohort_rate, sample = cohort.rate_for(kind)
    if sample >= MIN_COHORT_SAMPLE and model_probability > 0:
        probability = 0.5 * cohort_rate + 0.5 * model_probability
        method = AttributionMethod.BLENDED
    elif sample >= MIN_COHORT_SAMPLE:
        probability = cohort_rate
        method = AttributionMethod.COHORT
    else:
        probability = model_probability
        method = AttributionMethod.MODEL
    return int(amount_paise * probability), probability, method


async def ab_comparison(session: AsyncSession) -> dict:
    """Control holdout against the Revyn-managed cohort over live events."""
    recovered_flag = case((RevenueEvent.status == EventStatus.RECOVERED, 1), else_=0)
    stmt = (
        select(
            RevenueEvent.cohort,
            func.count(RevenueEvent.id),
            func.sum(RevenueEvent.amount_paise),
            func.sum(recovered_flag),
            func.sum(RevenueEvent.recovered_amount_paise),
            func.sum(RevenueEvent.contacts_used),
            func.sum(RevenueEvent.recovery_cost_paise),
        )
        .where(RevenueEvent.is_training.is_(False))
        .group_by(RevenueEvent.cohort)
    )
    arms: dict[str, dict] = {}
    for cohort, count, at_risk, recovered, recovered_amount, contacts, cost in (
        await session.execute(stmt)
    ).all():
        count = int(count or 0)
        arms[str(cohort)] = {
            "cohort": str(cohort),
            "events": count,
            "revenue_at_risk_paise": int(at_risk or 0),
            "recovered_events": int(recovered or 0),
            "recovered_paise": int(recovered_amount or 0),
            "customer_contacts": int(contacts or 0),
            "cost_paise": int(cost or 0),
            "recovery_rate": (int(recovered or 0) / count) if count else 0.0,
            "contacts_per_event": (int(contacts or 0) / count) if count else 0.0,
        }
    control = arms.get(str(Cohort.CONTROL), {})
    treatment = arms.get(str(Cohort.TREATMENT), {})
    lift = (treatment.get("recovery_rate", 0.0) or 0.0) - (control.get("recovery_rate", 0.0) or 0.0)
    return {
        "control": control,
        "treatment": treatment,
        "recovery_rate_lift": round(lift, 4),
        "contact_delta_per_event": round(
            (treatment.get("contacts_per_event", 0.0) or 0.0)
            - (control.get("contacts_per_event", 0.0) or 0.0),
            3,
        ),
    }
