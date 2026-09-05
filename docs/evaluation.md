# Evaluation

Two questions, measured separately: *is the probability honest?* and *did the money exist?* A third - *did we waste the regulated budget?* - is reported alongside.

## 1. Is the probability honest?

`HistGradientBoostingClassifier` wrapped in isotonic calibration, trained on synthetic `is_training=true` history (10,000 default) with holdout split. Treatment is a **feature** (S-learner), so `P(recovery|action) − P(recovery|no action)` comes from one artifact.

Reported by `GET /ops/model` and on `/ledger`:

| Metric | Why |
| --- | --- |
| **Brier score** | headline - accuracy + calibration, punishes confident wrongness |
| Log loss | sensitive to tails where over-confidence buys bad spend |
| ROC AUC | ranking only |
| Calibration error | mean gap predicted vs observed across bins |
| Base rate | context for the others |

Calibration bins are a chart on `/ledger`, not just a scalar - a good Brier can hide miscalibration in the spend region.

Last measured (`gbdt-isotonic-202609011424`, holdout n=1,999, base rate 0.3527): Brier **0.19782**, log loss 0.58011, AUC 0.7197, calibration error 0.0187.

Calibration is safety-critical: the gate checks `min_confidence` and `min_expected_value = uplift×amount − cost − friction`. A model saying 0.7 when it means 0.4 authorises spend the guardrails should block. Without an artifact the system falls back to a heuristic and shows a `heuristic` badge.

## 2. Did the money exist?

Headline KPI (not gross):

```
Incremental Net = Actual Recovered − Estimated Organic − Recovery Costs
```

**Organic** - what would have arrived alone - is per-recovery via `engines/counterfactual.py`:

| Method | Condition |
| --- | --- |
| `cohort` | enough control events of that kind - observed control rate |
| `model` | too few controls - model no-action probability |
| `blended` | both - 50/50 average (most bookings) |

Each ledger row stores gross, organic, cost, incremental, and method; every figure on `/ledger` is traceable.

**Cost** per action (messaging, voice, discount given away) makes a discount-bought recovery visibly worth less than a WhatsApp nudge. Regulatory causes have near-zero organic rates (they never self-heal) and futile `RETRY_PAYMENT` is −4.5 lift.

Last run: gross ₹3.15L, organic ₹0.59L, cost ₹185, **incremental net ₹2.43L**, cost per recovery ₹3.76, control organic 17.77% (n=2,183).

## 3. The A/B holdout

Live events are `control`/`treatment` at detection. Controls are fully scored (decision, probability, rationale) then left alone - giving the organic rate a real denominator.

Last run: control n=16 → 18.8% at **0.00** contacts/event; treatment n=104 → 47.1% at **0.73** contacts/event. **+28.4pp** at <1 contact - more money with less friction.

Read at `GET /ledger/ab-test`, surfaced on `/` and `/ledger`.

## 4. Did we waste the regulated budget? (NPCI)

Mandate attempts are exhaustible (4 per sequence number). `simulator` scores the open book under three policies and reports:

| Field | Meaning |
| --- | --- |
| `npci_wasted` | RETRY spent on regulatory causes (never could succeed) |
| `futile_retries_prevented` | RETRY_FUTILE hard-blocks (`mandate_revoked`, `cap_exceeded`, `pdn_missing`, `afa`) |
| `npci_attempts_spent` / `mandates_tracked` | Σ over journeys/mandates, in `/ledger/summary` and `/dashboard/safety` |

Last run: generic baseline **3.1 wasted / mandate, 8 mandates auto-revoked** → Revyn **~0.4 wasted, 0 revoked**. `RETRY_FUTILE` is visible on `/decisions/[id]` alternatives with the block reason. Re-run via `POST /simulator/what-if`.

## 5. Hinglish validation

Every LLM-generated message is validated before send: extracted amounts/dates must match the event record exactly, DLT template shape with only whitelisted variables, no invented discounts/deadlines, consent/opt-out and quiet hours respected, length/channel limits. Failed validation falls back to the static template and is audit-logged. Promise extraction on voice transcripts handles Hinglish (`paisa Monday tak aa jayega`, `kal`, `parso`, `salary aane ke baad`) - `POST /ops/extract-promise`.

## 6. Safety

`GET /dashboard/safety` reports executed, duplicates, unauthorised, policy blocks (incl. `RETRY_FUTILE`), human rejects, plus NPCI counters. Last: 82 executed, **0 duplicates, 0 unauthorised**, 40 blocked, 4 rejected, audit `valid:true` across 781 entries. Zero duplicates is about idempotency keys + customer lock, asserted in `tests/test_safety.py` (incl. concurrent same action).

## Reproducing

```bash
cd backend
python -m scripts.seed                    # generate + train
curl -X POST localhost:8000/api/v1/ops/cycle   # scan + tick, repeat 3-4
curl localhost:8000/api/v1/ops/model
curl localhost:8000/api/v1/ledger/summary      # includes npci_* / futile_*
curl localhost:8000/api/v1/ledger/ab-test
curl localhost:8000/api/v1/dashboard/safety
curl localhost:8000/api/v1/audit/verify
curl -X POST localhost:8000/api/v1/simulator/what-if -H 'content-type: application/json' -d '{"overrides":{}}'  # npci_wasted comparison
```

Figures move with seed/cycles/approvals. Invariants that should hold: Brier < base-rate baseline, incremental << gross, duplicates 0, Revyn `npci_wasted` << baseline.
