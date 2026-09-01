"""The journey state machine bounds what an autonomous agent can do next."""

from __future__ import annotations

import pytest

from app.core.constants import TERMINAL_JOURNEY_STATES, JourneyState
from app.core.errors import InvalidTransitionError
from app.models.journey import RecoveryJourney
from app.services import journey as journey_service


def build_journey(state: JourneyState = JourneyState.DETECTED) -> RecoveryJourney:
    return RecoveryJourney(
        id="j1",
        event_id="e1",
        customer_id="c1",
        state=state,
        plan=[],
        transitions=[],
        contacts_used=0,
        retries_used=0,
        discounts_used=0,
        voice_used=0,
        recovered_amount_paise=0,
        cost_paise=0,
        promise_confidence=0.0,
        step_index=0,
    )


def test_happy_path_reaches_recovered_and_closes():
    journey = build_journey()
    for state in (
        JourneyState.ANALYZING,
        JourneyState.PLANNED,
        JourneyState.EXECUTING,
        JourneyState.VERIFYING,
        JourneyState.RECOVERED,
        JourneyState.CLOSED,
    ):
        journey_service.transition(journey, state, reason="test")
    assert JourneyState(journey.state) is JourneyState.CLOSED
    assert len(journey.transitions) == 6


def test_illegal_transition_is_rejected():
    journey = build_journey(JourneyState.DETECTED)
    with pytest.raises(InvalidTransitionError):
        journey_service.transition(journey, JourneyState.RECOVERED)


def test_closed_is_absorbing():
    journey = build_journey(JourneyState.CLOSED)
    with pytest.raises(InvalidTransitionError):
        journey_service.transition(journey, JourneyState.PLANNED)


def test_transition_to_same_state_is_a_no_op():
    journey = build_journey(JourneyState.PLANNED)
    journey_service.transition(journey, JourneyState.PLANNED)
    assert journey.transitions == []


def test_terminal_states_record_a_close_reason():
    journey = build_journey(JourneyState.VERIFYING)
    journey_service.transition(journey, JourneyState.FAILED, reason="No response")
    assert journey.closed_at is not None
    assert journey.close_reason == "No response"
    assert journey.next_action_at is None
    assert journey_service.is_terminal(journey)


def test_a_failed_journey_can_be_replanned():
    journey = build_journey(JourneyState.FAILED)
    journey_service.transition(journey, JourneyState.PLANNED, reason="Next step")
    assert JourneyState(journey.state) is JourneyState.PLANNED


def test_every_state_is_reachable_or_terminal():
    """No state may be a dead end unless it is meant to be terminal."""
    for state in JourneyState:
        targets = journey_service.ALLOWED_TRANSITIONS[state]
        if state is JourneyState.CLOSED:
            assert targets == frozenset()
        elif state in TERMINAL_JOURNEY_STATES:
            assert JourneyState.CLOSED in targets
        else:
            assert targets, f"{state} has no outgoing transitions"
