from __future__ import annotations

from datetime import datetime

from app.core.clock import as_utc
from app.core.constants import ActionType, RootCause
from app.engines.features import IST_OFFSET_HOURS

REGULATORY_FUTILE_CAUSES: frozenset[RootCause] = frozenset(
    {
        RootCause.MANDATE_ABSENT,
        RootCause.MANDATE_REVOKED,
        RootCause.MANDATE_CAP_EXCEEDED,
        RootCause.PDN_MISSING,
        RootCause.AFA_THRESHOLD_BREACH,
    }
)

REMEDY_MAP: dict[RootCause, ActionType] = {
    RootCause.MANDATE_ABSENT: ActionType.REREGISTER_MANDATE,
    RootCause.MANDATE_REVOKED: ActionType.REREGISTER_MANDATE,
    RootCause.MANDATE_CAP_EXCEEDED: ActionType.AMEND_MANDATE_CAP,
    RootCause.PDN_MISSING: ActionType.SEND_PDN,
    RootCause.AFA_THRESHOLD_BREACH: ActionType.REREGISTER_MANDATE,
    RootCause.EXECUTION_WINDOW_MISS: ActionType.RETRY_PAYMENT,
}


def attempts_remaining(attempts_used: int, max_attempts: int = 4) -> int:
    return max(0, max_attempts - attempts_used)


def in_execution_window(when: datetime) -> bool:
    hour = (as_utc(when).hour + as_utc(when).minute / 60.0 + IST_OFFSET_HOURS) % 24.0
    return not (10.0 <= hour < 13.0)


def next_valid_presentation_slot(after: datetime, *, prefer_salary_cycle: bool = False) -> datetime:
    from datetime import timedelta

    candidate = after
    for _ in range(96):
        if in_execution_window(candidate):
            if prefer_salary_cycle:
                day = as_utc(candidate).day
                if day in range(1, 4) or day >= 25:
                    return candidate
                # try next day same hour
                candidate += timedelta(hours=24)
                continue
            return candidate
        candidate += timedelta(minutes=30)
    return candidate


def pdn_satisfied(last_pdn_sent_at: datetime | None, present_at: datetime, *, lead_hours: float = 24.0) -> bool:
    if last_pdn_sent_at is None:
        return False
    delta = (as_utc(present_at) - as_utc(last_pdn_sent_at)).total_seconds() / 3600.0
    return delta >= lead_hours


def is_retry_futile(root_cause: RootCause) -> bool:
    return root_cause in REGULATORY_FUTILE_CAUSES


def required_remedy(root_cause: RootCause) -> ActionType:
    return REMEDY_MAP.get(root_cause, ActionType.DO_NOTHING)
