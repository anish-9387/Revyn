# Architecture

## Layering

Dependencies point in one direction only:

```
api/v1/routes   HTTP shape, no business logic
    v
services        orchestration, journeys, policy, ledger, audit, idempotency
    v
agents          8 named roles, each one step of the loop
    v
engines         deterministic scoring; pure functions where possible
    v
models/core     persistence, config, clock, money, vocabularies
```

`integrations/` and `ml/` sit beside the engines and are reached only through protocols, so nothing
above them knows whether it is talking to a real gateway or a simulator.

## Protocols, not imports

Five seams keep the system testable and the demo offline-capable:

| Protocol | Real | Default / test |
| --- | --- | --- |
| `PaymentGateway` | Razorpay HTTP client | deterministic simulator with injectable faults |
| `ReasoningProvider` | Anthropic `claude-opus-5` | deterministic provider (rule-based hypotheses) |
| `KeyStore` | Redis | in-process dict with TTLs |
| `Predictor` | calibrated GBDT from joblib | transparent heuristic |
| `ActionGate` | policy engine over the live spec | same, with a test spec |

Each has a factory that reads settings once. Swapping one never touches a caller.

## The loop, concretely

`Orchestrator.scan()` — detection and planning:

1. Load the active policy and run the degradation engine (route / method / issuer failure rates
   against their rolling baselines), then reconcile the windows.
2. Pull at-risk live events that no open journey has claimed, **largest amount first**.
3. Run `RecoveryPipeline.plan()` per event: Sentinel scores risk, Investigator assigns a root cause
   and cause layer, Optimizer predicts recovery probability and counterfactual uplift for each
   candidate action, Strategist ranks by expected value, Policy Officer returns a verdict.
   The reasoning provider is consulted for at most `llm_max_events_per_scan` events per scan, and
   its output is advisory — it can add a hypothesis, never choose the action.
4. Persist the `Decision` with its full alternatives list, rationale, evidence and agent trace.
5. Branch:
   - control cohort -> recorded, never acted on (this is what makes incrementality measurable);
   - `do_nothing` or `BLOCK` -> event suppressed with reasons;
   - customer lock already held -> deferred as a collision, not double-contacted;
   - otherwise open a journey, transition `detected -> analyzing -> planned`, schedule step 0.

`Orchestrator.tick()` — execution and verification. Due steps are executed by Executor (the only
component holding a gateway handle, always under an idempotency key), Verifier confirms the outcome
*with the gateway* before anything is booked, Learner updates the merchant playbook, and the ledger
books gross, organic and cost separately.

## Journey state machine

13 states — `detected, analyzing, planned, awaiting_approval, approved, executing, verifying,
recovered, closed, blocked, failed, paused, expired` — with `recovered / closed / blocked / failed /
expired` terminal. Transitions go through `services/journey.py`, which rejects illegal moves rather
than silently allowing them, and each one is audited.

## Guardrails

The policy engine is a versioned row, not a code path. It enforces contact caps, retry caps, discount
count and percentage ceilings, minimum confidence, minimum expected value, approval thresholds for
money and for voice/human actions, per-customer cooldowns, quiet hours, a degradation retry guard
(stop spending attempts into a route that is already failing), a per-tick action cap, and a global
kill switch. Verdicts are `allow / require_approval / block`, each with machine-readable reasons.

Two independent safety mechanisms sit underneath: **idempotency keys** on every gateway call, and a
**distributed customer lock** so two journeys can never contact the same person at once.

## Audit chain

Every meaningful event appends a row whose hash covers the payload and the previous row's hash.
`GET /api/v1/audit/verify` recomputes the chain and returns the first sequence number where it
breaks. Actor is always recorded as one of `agent / human / system / gateway`.

## Adding things

**A new action:** add it to `ActionType`, give it a cost and a gateway/messaging implementation, add
it to `CONTACT_ACTIONS` or `FINANCIAL_ACTIONS` so budgets and approvals apply, and add its features
to the candidate builder. The decision engine will start scoring it with no further changes.

**A new agent step:** implement the `Agent` protocol in `agents/`, insert it into
`RecoveryPipeline`, and append to the trace. Keep scoring in `engines/` so it stays unit-testable
without a session.

**A new loss class:** extend `EventKind`, teach the generator to produce it, and add its organic
cohort rate — the ledger and A/B split are already keyed by kind.
