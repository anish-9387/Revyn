"""Test configuration.

The database URL and demo dials are set before any application module is imported, because
the engine and settings are constructed at import time.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

_DB_PATH = Path(tempfile.gettempdir()) / "revyn_test.db"
os.environ.update(
    {
        "REVYN_ENV": "test",
        "REVYN_DATABASE_URL": f"sqlite+aiosqlite:///{_DB_PATH.as_posix()}",
        "REVYN_SCHEDULER_ENABLED": "false",
        "REVYN_LLM_ENABLED": "false",
        "REVYN_GATEWAY": "simulator",
        "REVYN_CLOCK_SPEEDUP": "100000",
        "REVYN_LOG_LEVEL": "CRITICAL",
    }
)
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.core.cache import close_keystore  # noqa: E402
from app.core.clock import utcnow  # noqa: E402
from app.core.constants import (  # noqa: E402
    CommunicationPreference,
    CustomerSegment,
    EventKind,
    EventStatus,
    FailureCode,
    PaymentMethod,
    RootCause,
)
from app.core.db import Base, SessionFactory, engine  # noqa: E402
from app.models.customer import Customer  # noqa: E402
from app.models.event import RevenueEvent  # noqa: E402
from app.models.policy import PolicyConfig  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _database_file() -> None:
    if _DB_PATH.exists():
        _DB_PATH.unlink()


@pytest_asyncio.fixture
async def session():
    import app.models  # noqa: F401  (registers every mapper)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with SessionFactory() as db:
        yield db
        await db.rollback()
    await close_keystore()


def make_customer(**overrides) -> Customer:
    defaults = {
        "external_ref": "C9001",
        "name": "Ananya Iyer",
        "email": "ananya@example.com",
        "phone": "+919812345678",
        "segment": CustomerSegment.HIGH,
        "ltv_paise": 4_50_000_00,
        "average_order_value_paise": 8_000_00,
        "purchase_frequency": 2.4,
        "preferred_payment_method": PaymentMethod.UPI,
        "communication_preference": CommunicationPreference.WHATSAPP,
        "previous_payment_count": 14,
        "previous_success_rate": 0.92,
        "historical_recovery_rate": 0.38,
        "tenure_days": 420,
        "opted_out": False,
        "lifetime_contacts": 0,
    }
    return Customer(**{**defaults, **overrides})


def make_event(customer: Customer, **overrides) -> RevenueEvent:
    defaults = {
        "external_ref": "EVT9001",
        "kind": EventKind.PAYMENT_FAILURE,
        "status": EventStatus.AT_RISK,
        "is_training": False,
        "amount_paise": 7_499_00,
        "occurred_at": utcnow(),
        "payment_method": PaymentMethod.UPI,
        "issuer": "HDFC Bank",
        "route": "route-upi-alpha",
        "failure_code": FailureCode.ISSUER_DECLINED,
        "failure_reason": "Declined by issuing bank",
        "retry_count": 0,
        "prior_contacts": 0,
        "root_cause": RootCause.TRANSIENT_BANK_DECLINE,
        "cause_confidence": 0.7,
        "diagnosis": {},
        "order_ref": "order_evt9001",
        "payment_ref": "pay_evt9001",
        "recovered_amount_paise": 0,
        "recovery_cost_paise": 0,
        "contacts_used": 0,
    }
    event = RevenueEvent(**{**defaults, **overrides})
    event.customer = customer
    return event


def make_policy(**overrides) -> PolicyConfig:
    return PolicyConfig(**overrides)
