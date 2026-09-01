"""Idempotency, collision prevention and the tamper-evident audit trail."""

from __future__ import annotations

from app.core.constants import ActionType, AuditEvent
from app.services import audit, idempotency


async def test_an_action_can_only_be_reserved_once(session):
    key = idempotency.build_key("journey-1", ActionType.RETRY_PAYMENT, 0)
    assert await idempotency.reserve(key, "action-1") is True
    assert await idempotency.reserve(key, "action-2") is False
    assert await idempotency.owner_of(key) == "action-1"


async def test_the_same_step_always_derives_the_same_key(session):
    first = idempotency.build_key("journey-1", ActionType.PAYMENT_LINK, 2)
    second = idempotency.build_key("journey-1", ActionType.PAYMENT_LINK, 2)
    other_step = idempotency.build_key("journey-1", ActionType.PAYMENT_LINK, 3)
    assert first == second != other_step


async def test_only_one_journey_can_own_a_customer(session):
    assert await idempotency.claim_customer("cust-1", "journey-a", 60) is True
    assert await idempotency.claim_customer("cust-1", "journey-b", 60) is False
    assert await idempotency.customer_owner("cust-1") == "journey-a"
    await idempotency.release_customer("cust-1")
    assert await idempotency.claim_customer("cust-1", "journey-b", 60) is True


async def test_audit_chain_verifies_and_detects_tampering(session):
    for index in range(4):
        await audit.record(
            session,
            event_type=AuditEvent.ACTION_EXECUTED,
            entity_type="recovery_action",
            entity_id=f"action-{index}",
            summary=f"step {index}",
            payload={"index": index},
        )
    await session.flush()

    healthy = await audit.verify_chain(session)
    assert healthy["valid"] is True
    assert healthy["entries"] == 4

    from sqlalchemy import select

    from app.models.audit import AuditLog

    tampered = (await session.execute(select(AuditLog).where(AuditLog.sequence == 2))).scalar_one()
    tampered.summary = "step 2 (edited after the fact)"
    await session.flush()

    broken = await audit.verify_chain(session)
    assert broken["valid"] is False
    assert broken["broken_at"] == 2


async def test_audit_entries_are_sequential_and_linked(session):
    first = await audit.record(
        session,
        event_type=AuditEvent.DECISION_MADE,
        entity_type="decision",
        entity_id="d1",
        summary="first",
    )
    second = await audit.record(
        session,
        event_type=AuditEvent.ACTION_SCHEDULED,
        entity_type="recovery_action",
        entity_id="a1",
        summary="second",
    )
    assert second.sequence == first.sequence + 1
    assert second.previous_hash == first.entry_hash
    assert first.previous_hash == audit.GENESIS_HASH
