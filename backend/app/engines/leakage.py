"""Revenue Leakage Graph and merchant-level insights.

Aggregates open revenue at risk along the dimensions a merchant can act on, then derives
insights from the aggregates themselves. Every insight cites a computed number, so the
narrative cannot drift from the data even when a model writes it.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import EventStatus, PaymentMethod, RootCause
from app.core.money import format_inr
from app.data.catalog import FAILURE_LABELS, METHOD_LABELS, cause_profile
from app.engines.features import IST_OFFSET_HOURS
from app.models.event import RevenueEvent

OPEN_STATUSES = (EventStatus.AT_RISK, EventStatus.IN_RECOVERY, EventStatus.SUPPRESSED)


@dataclass(slots=True)
class Slice:
    key: str
    label: str
    events: int
    amount_paise: int
    expected_recovery_paise: int

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "events": self.events,
            "amount_paise": self.amount_paise,
            "expected_recovery_paise": self.expected_recovery_paise,
        }


async def _slice_by(session: AsyncSession, column, labeller=str) -> list[Slice]:
    stmt = (
        select(
            column,
            func.count(RevenueEvent.id),
            func.coalesce(func.sum(RevenueEvent.amount_paise), 0),
            func.coalesce(func.sum(RevenueEvent.expected_recovery_paise), 0),
        )
        .where(RevenueEvent.is_training.is_(False), RevenueEvent.status.in_(OPEN_STATUSES))
        .group_by(column)
        .order_by(func.sum(RevenueEvent.amount_paise).desc())
    )
    return [
        Slice(
            key=str(key),
            label=labeller(key),
            events=int(count or 0),
            amount_paise=int(amount or 0),
            expected_recovery_paise=int(expected or 0),
        )
        for key, count, amount, expected in (await session.execute(stmt)).all()
    ]


def _cause_label(cause: str) -> str:
    return cause_profile(RootCause(cause)).label


def _method_label(method: str) -> str:
    try:
        return METHOD_LABELS[PaymentMethod(method)]
    except ValueError:
        return str(method)


def _failure_label(code: str | None) -> str:
    if not code:
        return "Not applicable"
    try:
        from app.core.constants import FailureCode

        return FAILURE_LABELS.get(FailureCode(code), code)
    except ValueError:
        return str(code)


async def hourly_profile(session: AsyncSession) -> list[dict]:
    """Amount at risk by local hour of day, used for the time-of-day insight."""
    stmt = select(RevenueEvent.occurred_at, RevenueEvent.amount_paise).where(
        RevenueEvent.is_training.is_(False), RevenueEvent.status.in_(OPEN_STATUSES)
    )
    buckets: dict[int, list[int]] = {hour: [0, 0] for hour in range(24)}
    for occurred_at, amount in (await session.execute(stmt)).all():
        hour = int((occurred_at.hour + IST_OFFSET_HOURS) % 24)
        buckets[hour][0] += 1
        buckets[hour][1] += int(amount or 0)
    # Quiet hours are emitted as zeros: a sparse series drawn as a curve invents a shape.
    return [
        {"hour": hour, "events": events, "amount_paise": amount}
        for hour, (events, amount) in buckets.items()
    ]


async def method_failure_comparison(session: AsyncSession) -> list[dict]:
    """Historical failure share per payment method, for the 2.4x style comparison."""
    lost = func.sum(case((RevenueEvent.status == EventStatus.LOST, 1), else_=0))
    stmt = (
        select(RevenueEvent.payment_method, func.count(RevenueEvent.id), lost)
        .where(RevenueEvent.is_training.is_(True))
        .group_by(RevenueEvent.payment_method)
    )
    rows = []
    for method, total, unrecovered in (await session.execute(stmt)).all():
        total = int(total or 0)
        rows.append(
            {
                "payment_method": str(method),
                "events": total,
                "unrecovered": int(unrecovered or 0),
                "loss_rate": (int(unrecovered or 0) / total) if total else 0.0,
            }
        )
    rows.sort(key=lambda row: row["loss_rate"], reverse=True)
    return rows


async def segment_slices(session: AsyncSession) -> list[Slice]:
    from app.models.customer import Customer

    stmt = (
        select(
            Customer.segment,
            func.count(RevenueEvent.id),
            func.coalesce(func.sum(RevenueEvent.amount_paise), 0),
            func.coalesce(func.sum(RevenueEvent.expected_recovery_paise), 0),
        )
        .join(Customer, Customer.id == RevenueEvent.customer_id)
        .where(RevenueEvent.is_training.is_(False), RevenueEvent.status.in_(OPEN_STATUSES))
        .group_by(Customer.segment)
        .order_by(func.sum(RevenueEvent.amount_paise).desc())
    )
    return [
        Slice(
            key=str(segment),
            label=str(segment).upper(),
            events=int(count or 0),
            amount_paise=int(amount or 0),
            expected_recovery_paise=int(expected or 0),
        )
        for segment, count, amount, expected in (await session.execute(stmt)).all()
    ]


async def build_graph(session: AsyncSession) -> dict:
    by_kind = await _slice_by(session, RevenueEvent.kind)
    by_method = await _slice_by(session, RevenueEvent.payment_method, _method_label)
    by_cause = await _slice_by(session, RevenueEvent.root_cause, _cause_label)
    by_failure = await _slice_by(session, RevenueEvent.failure_code, _failure_label)
    by_route = await _slice_by(session, RevenueEvent.route)
    by_segment = await segment_slices(session)

    totals_stmt = select(
        func.count(RevenueEvent.id),
        func.coalesce(func.sum(RevenueEvent.amount_paise), 0),
        func.coalesce(func.sum(RevenueEvent.expected_recovery_paise), 0),
    ).where(RevenueEvent.is_training.is_(False), RevenueEvent.status.in_(OPEN_STATUSES))
    total_events, total_amount, total_expected = (await session.execute(totals_stmt)).one()

    return {
        "total_events": int(total_events or 0),
        "total_at_risk_paise": int(total_amount or 0),
        "total_expected_recovery_paise": int(total_expected or 0),
        "by_loss_class": [s.as_dict() for s in by_kind],
        "by_payment_method": [s.as_dict() for s in by_method],
        "by_root_cause": [s.as_dict() for s in by_cause],
        "by_failure_code": [s.as_dict() for s in by_failure],
        "by_route": [s.as_dict() for s in by_route],
        "by_segment": [s.as_dict() for s in by_segment],
        "hourly": await hourly_profile(session),
        "method_loss_rates": await method_failure_comparison(session),
    }


def derive_insights(graph: dict) -> list[str]:
    """Deterministic, quantitative findings. Each one cites a number from the graph."""
    insights: list[str] = []
    total = graph["total_at_risk_paise"] or 1

    methods = graph["by_payment_method"]
    if methods:
        top = methods[0]
        share = top["amount_paise"] / total
        if share >= 0.25:
            insights.append(
                f"{share:.0%} of revenue at risk sits on a single payment method "
                f"({top['label']}), worth {format_inr(top['amount_paise'])}."
            )

    causes = graph["by_root_cause"]
    if causes:
        top = causes[0]
        insights.append(
            f"{top['label']} is the largest single cause at {format_inr(top['amount_paise'])} "
            f"across {top['events']} events."
        )

    hourly = graph["hourly"]
    if hourly:
        evening = sum(row["amount_paise"] for row in hourly if row["hour"] >= 19)
        daytime = sum(row["amount_paise"] for row in hourly if 9 <= row["hour"] < 19)
        if daytime > 0 and evening / max(daytime, 1) > 0.55:
            insights.append(
                f"After 7 PM accounts for {format_inr(evening)} at risk against "
                f"{format_inr(daytime)} across the whole working day."
            )

    rates = graph["method_loss_rates"]
    if len(rates) >= 2 and rates[-1]["loss_rate"] > 0:
        ratio = rates[0]["loss_rate"] / rates[-1]["loss_rate"]
        if ratio >= 1.3:
            insights.append(
                f"{_method_label(rates[0]['payment_method'])} loses {ratio:.1f}x more often than "
                f"{_method_label(rates[-1]['payment_method'])} on historical volume."
            )

    routes = graph["by_route"]
    if len(routes) >= 2:
        share = routes[0]["amount_paise"] / total
        if share >= 0.3:
            insights.append(
                f"Gateway {routes[0]['key']} carries {share:.0%} of current exposure "
                f"({format_inr(routes[0]['amount_paise'])})."
            )
    return insights[:5]


async def insights(session: AsyncSession, graph: dict | None = None) -> dict:
    """Deterministic insights, optionally rewritten by the reasoning provider."""
    from app.integrations.llm import get_reasoner

    graph = graph or await build_graph(session)
    deterministic = derive_insights(graph)
    payload = {
        "total_at_risk_rupees": round(graph["total_at_risk_paise"] / 100, 2),
        "by_loss_class": graph["by_loss_class"],
        "by_payment_method": graph["by_payment_method"],
        "by_root_cause": graph["by_root_cause"][:5],
        "hourly": graph["hourly"],
        "method_loss_rates": graph["method_loss_rates"],
    }
    narrated = await get_reasoner().summarise_leakage(payload)
    return {
        "insights": narrated.insights if narrated and narrated.insights else deterministic,
        "deterministic_insights": deterministic,
        "source": "claude" if narrated and narrated.insights else "deterministic",
    }
