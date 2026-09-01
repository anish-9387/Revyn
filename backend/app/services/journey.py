"""Recovery journey state machine.

Explicit transitions are what stop an autonomous agent from drifting into an undefined
state. Any move not listed here raises rather than silently corrupting a journey.
"""

from __future__ import annotations

from datetime import datetime

from app.core.clock import utcnow
from app.core.constants import TERMINAL_JOURNEY_STATES, JourneyState
from app.core.errors import InvalidTransitionError
from app.models.journey import RecoveryJourney

ALLOWED_TRANSITIONS: dict[JourneyState, frozenset[JourneyState]] = {
    JourneyState.DETECTED: frozenset(
        {JourneyState.ANALYZING, JourneyState.BLOCKED, JourneyState.CLOSED}
    ),
    JourneyState.ANALYZING: frozenset(
        {
            JourneyState.PLANNED,
            JourneyState.CLOSED,
            JourneyState.BLOCKED,
            JourneyState.RECOVERED,
        }
    ),
    JourneyState.PLANNED: frozenset(
        {
            JourneyState.AWAITING_APPROVAL,
            JourneyState.EXECUTING,
            JourneyState.BLOCKED,
            JourneyState.FAILED,
            JourneyState.PAUSED,
            JourneyState.CLOSED,
            JourneyState.EXPIRED,
        }
    ),
    JourneyState.AWAITING_APPROVAL: frozenset(
        {
            JourneyState.APPROVED,
            JourneyState.BLOCKED,
            JourneyState.CLOSED,
            JourneyState.EXPIRED,
            JourneyState.PAUSED,
        }
    ),
    JourneyState.APPROVED: frozenset(
        {
            JourneyState.EXECUTING,
            JourneyState.AWAITING_APPROVAL,
            JourneyState.BLOCKED,
            JourneyState.FAILED,
            JourneyState.PAUSED,
            JourneyState.CLOSED,
        }
    ),
    JourneyState.EXECUTING: frozenset(
        {
            JourneyState.VERIFYING,
            JourneyState.FAILED,
            JourneyState.BLOCKED,
            JourneyState.PAUSED,
            JourneyState.CLOSED,
        }
    ),
    JourneyState.VERIFYING: frozenset(
        {
            JourneyState.RECOVERED,
            JourneyState.PLANNED,
            JourneyState.AWAITING_APPROVAL,
            JourneyState.FAILED,
            JourneyState.CLOSED,
            JourneyState.EXPIRED,
            JourneyState.PAUSED,
        }
    ),
    JourneyState.PAUSED: frozenset(
        {JourneyState.PLANNED, JourneyState.CLOSED, JourneyState.EXPIRED, JourneyState.APPROVED}
    ),
    JourneyState.RECOVERED: frozenset({JourneyState.CLOSED}),
    JourneyState.FAILED: frozenset({JourneyState.CLOSED, JourneyState.PLANNED}),
    JourneyState.BLOCKED: frozenset({JourneyState.CLOSED, JourneyState.PLANNED}),
    JourneyState.EXPIRED: frozenset({JourneyState.CLOSED}),
    JourneyState.CLOSED: frozenset(),
}


def can_transition(current: JourneyState, target: JourneyState) -> bool:
    return target in ALLOWED_TRANSITIONS.get(current, frozenset())


def transition(
    journey: RecoveryJourney,
    target: JourneyState,
    *,
    reason: str = "",
    at: datetime | None = None,
) -> RecoveryJourney:
    current = JourneyState(journey.state)
    if current is target:
        return journey
    if not can_transition(current, target):
        raise InvalidTransitionError(
            f"Cannot move journey from {current} to {target}",
            details={"journey_id": journey.id, "from": str(current), "to": str(target)},
        )
    moment = at or utcnow()
    journey.state = target
    # Reassigning keeps the JSON column dirty-tracked on SQLAlchemy.
    journey.transitions = [
        *journey.transitions,
        {"from": str(current), "to": str(target), "at": moment.isoformat(), "reason": reason},
    ]
    if target in TERMINAL_JOURNEY_STATES:
        journey.closed_at = moment
        journey.close_reason = reason or str(target)
        journey.next_action_at = None
    return journey


def is_terminal(journey: RecoveryJourney) -> bool:
    return JourneyState(journey.state) in TERMINAL_JOURNEY_STATES
