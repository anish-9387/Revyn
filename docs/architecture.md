# Architecture

## Layering

Dependencies point in one direction:

```
api/v1/routes   HTTP shape, no business logic
    v
services        orchestration, journeys, policy, ledger, audit, idempotency, seeding
    v
agents          8 named roles, one step of the loop each
    v
engines         deterministic scoring; pure functions where possible
    v
models/core     persistence, config, clock, money, vocabularies
```

`integrations/` and `ml/` sit beside engines and are reached only through protocols - callers never know if they talk to a real gateway or the simulator.

## Protocols, not imports

| Protocol | Real | Default / test |
| --- | --- | --- |
| `PaymentGateway` | Razorpay HTTP client | deterministic simulator (injectable faults, NPCI delays) |
| `ReasoningProvider` | Anthropic `claude-sonnet-4-20250514` | deterministic (rule-based hypothesis + Hinglish promise regex) |
| `KeyStore` | Redis | in-process dict with TTLs |
| `Predictor` | calibrated GBDT from joblib | transparent heuristic (`heuristic` badge) |
| `ActionGate` | `PolicyEngine` over live `PolicySpec` | same, with test spec |

Factories read settings once. Swapping never touches callers.

## The loop

**`Orchestrator.scan()` - detection and planning:**

1. Load active `PolicySpec` and run degradation detection (route/method failure rates vs rolling baselines), reconcile windows.
2. Pull at-risk live events no open journey has claimed, largest amount first.
3. Per event run `RecoveryPipeline.plan()`: Sentinel (risk) → Investigator (root cause + `CauseLayer`, incl. `REGULATORY`) → Optimizer (calibrated probability + counterfactual uplift per action) → Strategist (rank by expected value) → Policy Officer (verdict). LLM is consulted for at most `llm_max_events_per_scan` events; its output is advisory only.
4. Persist `Decision` with alternatives, rationale, evidence, agent trace, `reasoning_provider`.
5. Branch: `control` → recorded never acted (incrementality denominator); `do_nothing`/`BLOCK` → suppressed; customer lock held → collision; else open `RecoveryJourney` (`detected → analyzing → planned`), schedule step 0 through the mandate-aware gate (`RETRY_FUTILE`, NPCI budget 4, window 10–13 IST, PDN 24h).

**`Orchestrator.tick()` - execution and verification:**

Due steps are executed by `Executor` (sole gateway holder, always under idempotency key), `Verifier` confirms outcome *with the gateway* before booking (captures `promise_date` via Hinglish extractor), `Learner` updates the playbook, `ledger.book_recovery` books gross/organic/cost separately. `SEND_PDN` updates `mandate.last_pdn_sent_at`; `RETRY_PAYMENT` increments `mandate.attempts_used` and `journey.npci_attempts_used`. `RETRY_FUTILE` blocks increment `futile_retries_prevented`.

## Mandate & Futility Engine

- `models/mandate.py` - per-customer mandate (rail `upi_autopay/card_emandate/nach`, status, `max_amount_paise`, `sequence_number`, `attempts_used` 0..4, `last_pdn_sent_at`).
- `engines/mandate.py` - pure functions `attempts_remaining`, `in_execution_window`, `next_valid_presentation_slot` (salary-cycle aware), `pdn_satisfied`, `is_retry_futile`, `required_remedy`.
- `engines/root_cause.py` + `data/catalog.py` - regulatory causes (`MANDATE_ABSENT`, `MANDATE_REVOKED`, `MANDATE_CAP_EXCEEDED`, `PDN_MISSING`, `AFA_THRESHOLD_BREACH`, `EXECUTION_WINDOW_MISS`) with priors mapping failure codes `mandate_not_found/revoked/amount_exceeds/pdn_not_delivered/afa_required`.
- `services/policy.py` - `RETRY_FUTILE` is a hard `BLOCK` before any scoring; NPCI `npci_max_attempts`, `execution_window_guard`, `pdn_lead_hours` are `PolicySpec` fields (editable at `/policies`, simulatable).

## Hinglish messaging

`integrations/messaging.py` exposes `generate_message()` (LLM per `(cause, channel, segment)` language register) and `validate_message()` (regex amount/date must match record, DLT shape with whitelisted variables, no invented discounts/deadlines, consent/opt-out, length/channel). Failed validation falls back to static template and is audit-logged. `llm/prompts.py` holds Hinglish system prompts; `llm/deterministic.py` extracts Hinglish promises (`paisa Monday tak aa jayega, kal, parso, salary aane ke baad`).

## Journey state machine

13 states - `detected, analyzing, planned, awaiting_approval, approved, executing, verifying, recovered, closed, blocked, failed, paused, expired` - terminal `recovered/closed/blocked/failed/expired`. Transitions via `services/journey.py` (illegal moves rejected), each audited.

## Guardrails

`PolicySpec` is a versioned row, not code: contact/retry/discount/voice caps, discount %, `min_confidence`/`min_expected_value`, approval thresholds, cooldowns, quiet hours, degradation guard, NPCI caps, kill switch. Verdicts `allow/require_approval/block` with machine-readable `PolicyRule` reasons (`RETRY_FUTILE`, `NPCI_BUDGET_EXHAUSTED`, `OUTSIDE_EXECUTION_WINDOW`, `PDN_PRECONDITION_UNMET`). Safety underneath: idempotency keys per gateway call and a distributed customer lock.

## Audit chain

Every event appends a row whose hash covers payload + `previous_hash`. `GET /audit/verify` recomputes and returns first break. Actor is `agent/human/system/gateway`.

## Adding things

**New action:** add to `ActionType`, define cost/gateway/messaging, add to `CONTACT_ACTIONS`/`FINANCIAL_ACTIONS`, add to candidate builder. The decision engine scores it automatically.

**New regulatory cause:** add `FailureCode` → `RootCause` in `data/catalog.py`, add `CauseProfile` with `REGULATORY` layer, teach generator to emit it, add organic rate. Futility blocking applies automatically.

**New agent step:** implement `Agent` protocol, insert into `RecoveryPipeline`, append trace. Keep scoring in `engines/` for unit tests.

**New loss class:** extend `EventKind`, teach generator, add organic cohort rate - ledger/A/B are already kind-keyed.
