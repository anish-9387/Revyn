"""HTTP contract for the dashboard, exercised against a seeded database."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.db import SessionFactory
from app.main import create_app
from app.services import seeding
from app.services.orchestrator import orchestrator

PREFIX = "/api/v1"


@pytest_asyncio.fixture
async def client(session):
    async with SessionFactory() as db:
        await seeding.seed(
            db, reset_first=True, customers=60, transactions=300, train_model=False, live_scale=0.08
        )
        await orchestrator.scan(db, limit=40)
        await db.commit()

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


async def test_health_and_readiness(client):
    assert (await client.get(f"{PREFIX}/health")).json()["status"] == "ok"
    ready = (await client.get(f"{PREFIX}/health/ready")).json()
    assert ready["seeded"] is True
    assert ready["gateway"] == "simulator"


async def test_overview_exposes_the_headline_numbers(client):
    body = (await client.get(f"{PREFIX}/dashboard/overview")).json()
    for key in (
        "revenue_at_risk_paise",
        "expected_recovery_paise",
        "gross_recovered_paise",
        "incremental_net_paise",
        "at_risk_by_kind",
        "safety",
        "ab_test",
        "runtime",
    ):
        assert key in body
    assert body["revenue_at_risk_paise"] > 0
    assert body["safety"]["duplicate_executions"] == 0
    assert body["runtime"]["reasoning_provider"] == "deterministic"


async def test_risk_queue_is_ordered_by_priority(client):
    body = (await client.get(f"{PREFIX}/risk", params={"limit": 20})).json()
    assert body["total"] > 0
    scores = [item["priority_score"] for item in body["items"]]
    assert scores == sorted(scores, reverse=True)


async def test_risk_filters_apply(client):
    body = (await client.get(f"{PREFIX}/risk", params={"kind": "cart_abandonment"})).json()
    assert all(item["kind"] == "cart_abandonment" for item in body["items"])


async def test_journey_detail_carries_plan_and_budget(client):
    journeys = (await client.get(f"{PREFIX}/journeys", params={"limit": 5})).json()
    if not journeys["items"]:
        pytest.skip("no journeys in this sample")
    journey_id = journeys["items"][0]["id"]
    detail = (await client.get(f"{PREFIX}/journeys/{journey_id}")).json()
    assert detail["id"] == journey_id
    assert "friction_budget" in detail
    assert detail["event"]["amount_paise"] > 0
    assert isinstance(detail["actions"], list)


async def test_decision_explains_itself(client):
    decisions = (await client.get(f"{PREFIX}/decisions", params={"limit": 1})).json()
    assert decisions["total"] > 0
    decision_id = decisions["items"][0]["id"]
    body = (await client.get(f"{PREFIX}/decisions/{decision_id}")).json()
    assert body["decision"]["rationale"]
    assert body["decision"]["agent_trace"]
    assert len(body["considered"]) > 1
    agents = {step["agent"] for step in body["decision"]["agent_trace"]}
    assert {"sentinel", "investigator", "strategist", "optimizer", "policy_officer"} <= agents


async def test_leakage_graph_and_insights(client):
    graph = (await client.get(f"{PREFIX}/leakage/graph")).json()
    assert graph["total_at_risk_paise"] > 0
    assert graph["by_loss_class"]
    insights = (await client.get(f"{PREFIX}/leakage/insights")).json()
    assert insights["source"] == "deterministic"
    assert isinstance(insights["insights"], list)


async def test_degradation_is_detected_and_charted(client):
    live = (await client.get(f"{PREFIX}/degradation/live")).json()
    assert live["routes"]
    assert live["active"], "the seeded incident must be visible"
    incident = live["active"][0]
    params = {"value": incident["scope_value"], "scope": incident["scope_type"]}
    series = (await client.get(f"{PREFIX}/degradation/series", params=params)).json()
    assert series["points"], "every degraded scope must be chartable, method as well as route"
    assert len({point["at"] for point in series["points"]}) == len(series["points"])


async def test_what_if_simulation_reports_a_delta(client):
    payload = {"overrides": {"max_contacts": 4, "retry_delay_minutes": 20}, "sample_limit": 60}
    body = (await client.post(f"{PREFIX}/simulator/what-if", json=payload)).json()
    assert body["sample_size"] > 0
    assert body["changed_fields"]["max_contacts"]["to"] == 4
    assert "net_expected_delta_paise" in body["delta"]
    assert body["legacy_baseline"]["interventions"] >= body["current"]["interventions"]


async def test_policy_patch_and_kill_switch(client):
    updated = (await client.patch(f"{PREFIX}/policies/active", json={"max_contacts": 5})).json()
    assert updated["max_contacts"] == 5

    halted = (await client.post(f"{PREFIX}/policies/kill-switch", json={"enabled": False})).json()
    assert halted["automation_enabled"] is False
    tick = (await client.post(f"{PREFIX}/ops/tick")).json()
    assert tick["executed"] == 0


async def test_audit_trail_verifies(client):
    body = (await client.get(f"{PREFIX}/audit", params={"limit": 5})).json()
    assert body["total"] > 0
    assert (await client.get(f"{PREFIX}/audit/verify")).json()["valid"] is True


async def test_playbook_and_ledger_endpoints(client):
    playbook = (await client.get(f"{PREFIX}/playbook")).json()
    assert playbook["entries"]
    summary = (await client.get(f"{PREFIX}/ledger/summary")).json()
    assert "incremental_net_paise" in summary
    ab = (await client.get(f"{PREFIX}/ledger/ab-test")).json()
    assert "control" in ab and "treatment" in ab


async def test_promise_extraction_reads_a_commitment(client):
    body = (
        await client.post(
            f"{PREFIX}/ops/extract-promise",
            json={"transcript": "Sorry, I will pay Rs 72,000 tomorrow once funds clear."},
        )
    ).json()
    assert body["result"]["promised"] is True
    assert body["result"]["amount_rupees"] == 72000.0
    assert body["result"]["promise_date"]


async def test_timeout_injection_is_armed(client):
    body = (await client.post(f"{PREFIX}/ops/inject-timeout", json={"count": 2})).json()
    assert body["timeouts_armed"] == 2
    from app.integrations.razorpay.factory import simulator

    simulator().faults.timeouts_remaining = 0
