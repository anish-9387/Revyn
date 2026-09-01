"""Idempotency for financial actions.

A key is derived from the journey, action type and sequence, so a retried tick can never
charge a customer twice. Reservations survive in the key store for long enough to cover
gateway retries and scheduler restarts.
"""

from __future__ import annotations

import hashlib

from app.core.cache import get_keystore
from app.core.constants import ActionType

RESERVATION_TTL_SECONDS = 6 * 60 * 60


def build_key(journey_id: str, action: ActionType, sequence: int, salt: str = "") -> str:
    raw = f"{journey_id}:{action}:{sequence}:{salt}"
    return hashlib.sha256(raw.encode()).hexdigest()[:48]


async def reserve(key: str, owner: str) -> bool:
    """True when this caller now owns the key, False when it was already claimed."""
    return await get_keystore().set_if_absent(f"idem:{key}", owner, RESERVATION_TTL_SECONDS)


async def owner_of(key: str) -> str | None:
    return await get_keystore().get(f"idem:{key}")


async def release(key: str) -> None:
    await get_keystore().delete(f"idem:{key}")


async def claim_customer(customer_id: str, journey_id: str, ttl_seconds: int) -> bool:
    """Recovery collision prevention: only one journey may own a customer at a time."""
    return await get_keystore().set_if_absent(
        f"lock:customer:{customer_id}", journey_id, ttl_seconds
    )


async def customer_owner(customer_id: str) -> str | None:
    return await get_keystore().get(f"lock:customer:{customer_id}")


async def release_customer(customer_id: str) -> None:
    await get_keystore().delete(f"lock:customer:{customer_id}")
