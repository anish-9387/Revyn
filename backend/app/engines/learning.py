"""Merchant Recovery Memory.

Each (loss class, cause layer, value band, action) cell carries a Beta posterior over its
recovery rate. Posteriors are bootstrapped from resolved history and then updated after
every verified outcome, so the playbook a merchant ends up with is theirs rather than a
generic default.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import (
    ActionType,
    CauseLayer,
    CustomerSegment,
    EventKind,
    EventStatus,
    RootCause,
)
from app.data.catalog import KIND_LABELS, cause_profile, intervention
from app.models.event import RevenueEvent
from app.models.insight import StrategyStat

#: Trials needed before a posterior is trusted enough to blend into a decision.
MIN_TRIALS_FOR_CONFIDENCE = 12

VALUE_BANDS: dict[CustomerSegment, str] = {
    CustomerSegment.VIP: "high",
    CustomerSegment.HIGH: "high",
    CustomerSegment.MEDIUM: "mid",
    CustomerSegment.LOW: "low",
    CustomerSegment.NEW: "low",
}


def value_band(segment: CustomerSegment | str) -> str:
    return VALUE_BANDS.get(CustomerSegment(segment), "mid")


def context_key(
    kind: EventKind | str, cause: RootCause | str, segment: CustomerSegment | str
) -> str:
    layer: CauseLayer = cause_profile(RootCause(cause)).layer
    return f"{EventKind(kind)}|{layer}|{value_band(segment)}"


def describe_context(key: str) -> str:
    """The same cell as a phrase, for prose that a merchant reads rather than parses."""
    kind, _, rest = key.partition("|")
    layer, _, band = rest.partition("|")
    head = KIND_LABELS.get(EventKind(kind), kind.replace("_", " ")) if kind else key
    return " · ".join(part for part in (head, layer, f"{band} ticket" if band else "") if part)


@dataclass(slots=True)
class LearnedRate:
    action: ActionType
    posterior_mean: float
    trials: int
    successes: int
    recovered_paise: int

    @property
    def confident(self) -> bool:
        return self.trials >= MIN_TRIALS_FOR_CONFIDENCE


async def learned_rates(session: AsyncSession, key: str) -> dict[ActionType, float]:
    """Posterior means for actions with enough evidence to be worth blending in."""
    stats = (
        (await session.execute(select(StrategyStat).where(StrategyStat.context_key == key)))
        .scalars()
        .all()
    )
    return {
        ActionType(stat.action): stat.posterior_mean
        for stat in stats
        if stat.trials >= MIN_TRIALS_FOR_CONFIDENCE
    }


async def observe(
    session: AsyncSession,
    *,
    key: str,
    action: ActionType,
    recovered: bool,
    amount_paise: int,
    cost_paise: int,
) -> StrategyStat:
    stat = (
        await session.execute(
            select(StrategyStat).where(
                StrategyStat.context_key == key, StrategyStat.action == action
            )
        )
    ).scalar_one_or_none()
    if stat is None:
        prior = intervention(action).base_success
        # Counters are set explicitly: column defaults only land at flush time, and the
        # posterior is updated below before this row is written.
        stat = StrategyStat(
            context_key=key,
            action=action,
            trials=0,
            successes=0,
            alpha=1.0 + 4.0 * prior,
            beta=1.0 + 4.0 * (1.0 - prior),
            recovered_paise=0,
            cost_paise=0,
        )
        session.add(stat)
    stat.trials += 1
    stat.cost_paise += cost_paise
    if recovered:
        stat.successes += 1
        stat.alpha += 1.0
        stat.recovered_paise += amount_paise
    else:
        stat.beta += 1.0
    await session.flush()
    return stat


async def bootstrap(session: AsyncSession) -> int:
    """Seed posteriors from resolved history so the playbook is never cold."""
    existing = (await session.execute(select(StrategyStat.id).limit(1))).first()
    if existing is not None:
        return 0

    stmt = select(RevenueEvent).where(
        RevenueEvent.is_training.is_(True),
        RevenueEvent.status.in_([EventStatus.RECOVERED, EventStatus.LOST]),
        RevenueEvent.applied_action.is_not(None),
    )
    events = (await session.execute(stmt)).unique().scalars().all()
    buckets: dict[tuple[str, ActionType], list[int]] = {}
    for event in events:
        key = context_key(event.kind, event.root_cause, event.customer.segment)
        bucket = buckets.setdefault((key, ActionType(event.applied_action)), [0, 0, 0, 0])
        bucket[0] += 1
        if event.status == EventStatus.RECOVERED:
            bucket[1] += 1
            bucket[2] += event.recovered_amount_paise
        bucket[3] += event.recovery_cost_paise

    for (key, action), (trials, successes, recovered, cost) in buckets.items():
        prior = intervention(action).base_success
        session.add(
            StrategyStat(
                context_key=key,
                action=action,
                trials=trials,
                successes=successes,
                alpha=1.0 + 4.0 * prior + successes,
                beta=1.0 + 4.0 * (1.0 - prior) + (trials - successes),
                recovered_paise=recovered,
                cost_paise=cost,
            )
        )
    await session.flush()
    return len(buckets)


async def playbook(session: AsyncSession) -> list[dict]:
    """Best-known action per context, which is the merchant recovery playbook."""
    stats = (await session.execute(select(StrategyStat))).scalars().all()
    by_context: dict[str, list[StrategyStat]] = {}
    for stat in stats:
        by_context.setdefault(stat.context_key, []).append(stat)

    entries: list[dict] = []
    for key, group in by_context.items():
        eligible = [s for s in group if s.trials >= MIN_TRIALS_FOR_CONFIDENCE] or group
        best = max(eligible, key=lambda s: s.posterior_mean)
        kind, layer, band = key.split("|")
        entries.append(
            {
                "context_key": key,
                "loss_class": kind,
                "cause_layer": layer,
                "value_band": band,
                "best_action": str(best.action),
                "best_action_label": intervention(ActionType(best.action)).label,
                "recovery_rate": round(best.posterior_mean, 4),
                "trials": best.trials,
                "recovered_paise": best.recovered_paise,
                "alternatives": [
                    {
                        "action": str(s.action),
                        "label": intervention(ActionType(s.action)).label,
                        "recovery_rate": round(s.posterior_mean, 4),
                        "trials": s.trials,
                    }
                    for s in sorted(group, key=lambda s: s.posterior_mean, reverse=True)
                    if s.action != best.action
                ][:4],
            }
        )
    entries.sort(key=lambda entry: entry["recovered_paise"], reverse=True)
    return entries
