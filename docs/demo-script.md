# Demo script

Eight steps, §47. Numbers from 2026-09-01 run (seed `20260901`, simulator, `deterministic` or `claude`); magnitudes vary, shapes should hold.

Setup:

```bash
cd backend && python -m scripts.seed && uvicorn app.main:app --port 8000
cd frontend && npm run dev   # http://localhost:3000
```

`API=http://localhost:8000/api/v1`

---

## Step 1 - Detect

Open `/dashboard` (command centre). Headline: **at risk now ₹8.90L** across four loss classes, with gateway, `reasoning: deterministic|claude`, model version, and live NPCI counters. This is what the audience evaluates before any claim.

`GET $API/dashboard/overview` - check `revenue_at_risk_paise`, `jobs.mandates_tracked`, `safety.futile_retries_prevented`.

## Step 2 - Diagnose & regulatory framing

Open `/` landing for the thesis, then `/leakage`. Degradation: **route-upi-alpha ~4.2× baseline (critical)** and **UPI method ~3.1×** - found by comparing rolling windows, not asserted. Leakage slices include regulatory causes (`MANDATE_REVOKED`, `PDN_MISSING`, `MANDATE_CAP_EXCEEDED`).

`GET $API/degradation/live` and `GET $API/leakage/graph`

## Step 3 - Prioritise

Open `/radar`. Events ranked by expected recovery, not amount. Each shows root cause and cause layer (`regulatory` rows are the selling point). Detection pulls largest recoverable first to respect contact budget.

`GET $API/risk`

## Step 4 - Plan & the futility proof

Click any regulatory row into `/decisions/{id}`. You will see: `MANDATE_REVOKED` → `CauseLayer.REGULATORY` → `RETRY_PAYMENT` listed under `alternatives` as `BLOCK` with `RETRY_FUTILE` reason → chosen `REREGISTER_MANDATE` or `AMEND_MANDATE_CAP` with uplift, expected value, and validator badge info from `/journeys/{id}`. Non-regulatory rows show normal `RETRY_PAYMENT` scoring.

`GET $API/decisions` then `GET $API/decisions/{id}`; `GET $API/journeys/{id}` shows `friction_budget` plus `npci_attempts_used`.

## Step 5 - Guardrails & simulation (the chart no one else can show)

Open `/approvals` (high-value/voice queue) and `/policies` (live `PolicySpec` incl. `npci_max_attempts:4`, `execution_window_guard: true`, `pdn_lead_hours:24`). Blocked count includes `RETRY_FUTILE`.

Then `/simulator`: keep defaults and `Run simulation`. The open book is re-scored under proposed vs current vs legacy fixed-retry. Result shows **NPCI retry budget**: baseline ~3.1 wasted / mandate and several mandates auto-revoked vs Revyn ~0.4 wasted, 0 revoked - with `futile_retries_prevented`.

```bash
curl $API/approvals
curl -X POST $API/approvals/{action_id}/approve -H 'content-type: application/json' -d '{"approver":"demo"}'
curl -X POST $API/simulator/what-if -H 'content-type: application/json' -d '{"overrides":{"max_contacts":1}}'
# requires X-API-Key header when REVYN_API_KEY is set
```

## Step 6 - Execute & Hinglish

```bash
curl -X POST $API/ops/cycle   # scan + tick; send X-API-Key if enforced
```

Measured in reference run: **82 executed, 0 duplicates, 0 unauthorised**. Incremental per-action leaders: WhatsApp, voice, alt method. Check `/journeys` for live `SEND_PDN` → wait 24h → present sequences; voice actions carry transcripts like `paisa Monday tak aa jayega` and the `promise_date` captured on the journey. Message renders show validator green/red badge (DLT, amount hallucination guard).

## Step 7 - Failure (the important one)

Force ambiguous gateway state on already-succeeded payments, then cycle:

```bash
curl -X POST $API/ops/inject-timeout -H 'content-type: application/json' -d '{"count":3,"payment_already_succeeded":true}'
curl -X POST $API/ops/cycle
curl "$API/audit?limit=20"
```

Audit in order:

```
action_executed   Gateway state ambiguous, verifying before any retry
outcome_verified  whatsapp returned succeeded
recovery_booked   incremental booked (with attribution method)
strategy_updated  ...
journey_closed    ...
```

No retry, no double charge. Also try Hinglish promise extraction:

```bash
curl -X POST $API/ops/extract-promise -H 'content-type: application/json' -d '{"transcript":"paisa Monday tak aa jayega, thoda time do"}'
```

## Step 8 - Final results

Open `/ledger`:

| | |
| --- | --- |
| At risk (start) | ₹8.90L |
| Gross recovered | ₹3.15L |
| Estimated organic | ₹0.59L |
| Recovery cost | ₹185 |
| **Incremental net** | **₹2.43L** |
| Cost per recovery | ₹3.76 |
| Unauthorised | **0** |

A/B from `/ledger` or `GET $API/ledger/ab-test`:

| Arm | n | Recovery rate | Contacts / event |
| --- | --- | --- | --- |
| Control (no intervention) | 16 | 18.8% | 0.00 |
| Treatment (Revyn) | 104 | 47.1% | 0.73 |

+28.4pp at <1 contact. Close on `/audit`: **chain intact, 781 entries** - `GET $API/audit/verify` recomputes every hash.

---

## If something is offline

- **No `ANTHROPIC_API_KEY`** - header reads `reasoning: deterministic`, Hinglish falls back to static templates + regex promise extractor; loop unaffected. Demonstrate deliberately.
- **No Redis / Postgres** - SQLite + in-process locks are defaults.
- **Empty `/radar`** - book worked through; `python -m scripts.seed` or `POST /ops/seed`.
- **Loop paused** - kill switch on `/policies` or `REVYN_SCHEDULER_ENABLED=false`. Drive manually via `POST /ops/cycle` (add `X-API-Key: $REVYN_API_KEY` header when key is set).
