# Demo script

Eight steps, mapped to PRD §47. Every number below was produced by an actual run on 2026-09-01
(seed `20260901`, simulator gateway, live Anthropic reasoning). Yours will differ in magnitude and
should hold in shape.

Setup, once:

```bash
cd backend && python -m scripts.seed && uvicorn app.main:app --port 8000
cd frontend && npm run dev
```

`API=http://localhost:8000/api/v1` for the calls below.

---

## Step 1 — Detect

Open `/` (command centre). Headline: **at risk now ₹8.90L**, split across the four loss classes, with
the loop status, the gateway in use, whether reasoning is `claude` or `deterministic`, and the model
version — so the audience knows what is actually running before any claim is made.

`GET $API/dashboard/overview`

## Step 2 — Diagnose

Open `/leakage`. The degradation engine has flagged **route-upi-alpha at 3.9x its baseline failure
rate (critical)** and the **UPI method at 2.81x**. This is the PRD's "failures increased 3.1x and are
concentrated in one payment route" — found, not asserted, by comparing rolling windows to baselines.

`GET $API/degradation/live` and `GET $API/leakage/graph`

## Step 3 — Prioritise

Open `/radar`. Every at-risk event ranked by amount with its risk score, root cause and cause layer.
Detection walks this list largest-first, so the biggest recoverable rupees get the scarce
contact budget.

`GET $API/risk`

## Step 4 — Plan

Click any row into `/decisions/{id}`. For that one event: the chosen action, its calibrated recovery
probability, the organic probability, the uplift, expected value, **every alternative that was
considered and rejected with its own numbers**, the agent trace, and whether the reasoning provider
contributed a hypothesis. Different loss classes get different plans — delayed retry for failed
payments, payment link for abandonment, retry plus reminder for subscriptions, promise-to-pay for
overdue invoices.

`GET $API/decisions` then `GET $API/decisions/{id}`

## Step 5 — Guardrails

Open `/approvals`: large-value and voice/human actions are queued for a person, not executed.
Open `/policies`: the live guardrail spec, editable and versioned. In the measured run, **40 actions
were blocked by policy** and **4 were rejected by a human** — contact caps, cooldowns, quiet hours,
minimum confidence and the degradation retry guard all fired.

Then open `/simulator`, lower `Max contacts per customer`, and run it: the whole open book is
re-scored under the proposed policy, alongside the legacy fixed-retry workflow, and nothing is written
until `Apply to live policy` is pressed.

```bash
curl $API/approvals
curl -X POST $API/approvals/{action_id}/approve -H 'content-type: application/json' -d '{"approver":"demo"}'
curl -X POST $API/simulator/what-if -H 'content-type: application/json' \
     -d '{"overrides":{"max_contacts":1}}'
```

## Step 6 — Execute

Run the loop and watch recoveries book:

```bash
curl -X POST $API/ops/cycle       # scan + tick
```

Measured: **82 actions executed, 0 duplicates, 0 unauthorised**. Per-action incremental net —
WhatsApp ₹1.94L over 28 recoveries, voice ₹0.30L over 10, alternate payment method ₹0.15L over 5,
then payment link, retry and discount in the thousands. Visible live on `/journeys` and `/audit`.

## Step 7 — Failure (the important one)

Force gateway timeouts on payments that have *already succeeded*, then run a cycle:

```bash
curl -X POST $API/ops/inject-timeout -H 'content-type: application/json' \
     -d '{"count":3,"payment_already_succeeded":true}'
curl -X POST $API/ops/cycle
curl "$API/audit?limit=20"
```

The audit chain recorded, in order:

```
action_executed   Gateway state ambiguous, verifying before any retry
outcome_verified  whatsapp returned succeeded
recovery_booked   ...
strategy_updated  ...
journey_closed    ...
```

No retry, no double charge. Verification precedes every booking by construction, so an ambiguous
gateway response can only ever cost a query — never a second charge.

## Step 8 — Final results

Open `/ledger`:

| | |
| --- | --- |
| At risk (start) | ₹8.90L |
| Gross recovered | ₹3.15L |
| Estimated organic | ₹0.59L |
| Recovery cost | ₹185 |
| **Incremental net** | **₹2.43L** |
| Cost per recovery | ₹3.76 |
| Unauthorised actions | **0** |

And the comparison that carries the argument, from `/ledger` or `GET $API/ledger/ab-test`:

| Arm | n | Recovery rate | Contacts per event |
| --- | --- | --- | --- |
| Control (no intervention) | 16 | 18.8% | 0.00 |
| Treatment (Revyn) | 104 | 47.1% | 0.73 |

+28.4pp recovery at under one contact per event. Finish on `/audit`: **chain intact, 781 entries** —
`GET $API/audit/verify` recomputes every hash on demand.

---

## If something is offline

- **No `ANTHROPIC_API_KEY`** — the header reads `reasoning: deterministic` and every step still works.
  Worth showing deliberately: it demonstrates the LLM was never in the control path.
- **No Redis / Postgres** — SQLite and in-process locks are the defaults.
- **Nothing on `/radar`** — the book is worked through; re-seed with `python -m scripts.seed`.
- **Loop paused** — the kill switch on `/policies` is off, or `REVYN_SCHEDULER_ENABLED=false`.
  `POST $API/ops/cycle` drives it manually.
