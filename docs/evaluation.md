# Evaluation

Two separate questions, measured separately: *is the probability honest?* and *did the money exist?*

## 1. Is the probability honest?

The predictor is a `HistGradientBoostingClassifier` wrapped in isotonic calibration, trained on the
synthetic history (`is_training = true` events, 10,000 by default) with a holdout split. Treatment is
a **feature**, not a separate model (S-learner), which is what makes the counterfactual query
"probability with this action minus probability with no action" answerable from one artifact.

Reported by `GET /api/v1/ops/model` and rendered on `/ledger`:

| Metric | Why it is here |
| --- | --- |
| **Brier score** | the headline. Accuracy *and* calibration in one number, and it punishes confident wrongness |
| Log loss | sensitive to the tails, where over-confidence costs real money |
| ROC AUC | ranking quality only - it says nothing about whether 0.7 means 70% |
| Calibration error | mean absolute gap between predicted and observed rate across bins |
| Base rate | the number every other number must be read against |

Calibration bins are rendered as a chart on `/ledger`, not just a scalar: a model with a good Brier
score can still be badly miscalibrated in the band where the spend decisions are actually made.

Last measured (`gbdt-isotonic-202609011424`, holdout n=1,999, base rate 0.3527): Brier **0.19782**,
log loss 0.58011, AUC 0.7197, calibration error 0.0187.

Calibration is load-bearing rather than cosmetic, because the policy engine gates on
`min_confidence` and on `min_expected_value = probability x amount - cost`. A model that says 0.7
when it means 0.4 does not merely mispredict; it authorises spend that the guardrails were written to
prevent. When no artifact is present the system falls back to a transparent heuristic and the UI
says so with a `heuristic` badge, rather than silently reporting numbers from a different estimator.

## 2. Did the money exist?

Gross recovery is trivial to inflate: retry everything and claim every success. The primary KPI is

```
Incremental Net Revenue Recovered = Actual Recovered - Estimated Organic - Recovery Costs
```

**Organic** is what would have arrived with no intervention. `engines/counterfactual.py` estimates it
per recovery and records which method it used:

| Method | Condition |
| --- | --- |
| `cohort` | enough control-cohort events of that kind; use the observed control rate |
| `model` | too few control events; use the model's no-action probability |
| `blended` | both available; a 50/50 average, which is what most bookings use |

Every ledger entry stores gross, organic, cost, incremental and the method, so any figure on `/ledger`
can be traced back to how it was attributed.

**Cost** is charged per action (messaging fees, voice minutes, discount given away), so a recovery
bought with a discount is worth visibly less than one bought with a WhatsApp nudge.

Last measured over a live run: gross ₹3.15L, organic ₹0.59L, cost ₹185, **incremental net ₹2.43L**,
cost per recovery ₹3.76, control organic rate 17.77% (n=2,183).

## 3. The A/B holdout

Live events are split into `control` and `treatment` cohorts at detection. Control events are fully
scored and recorded - decision, probability, rationale - and then deliberately left alone. That gives
the organic rate a real denominator instead of a modelling assumption.

Last measured: control n=16 -> 18.8% recovery at **0.00** contacts per event; treatment n=104 ->
47.1% at **0.73** contacts per event. **+28.4pp** at well under one contact per event, which is the
shape of result worth reporting: more money recovered with less customer friction, not more.

Read it at `GET /api/v1/ledger/ab-test`, rendered on `/` and `/ledger`.

## 4. Safety

Recovery numbers are meaningless if the system also double-charged someone. `GET
/api/v1/dashboard/safety` reports executed actions, duplicate executions, unauthorised actions
(executed without the required approval), policy blocks and human rejections.

Last measured: 82 executed, **0 duplicates**, **0 unauthorised**, 40 blocked by policy, 4 rejected by
a human, audit chain valid across 781 entries.

Zero duplicates is a claim about the idempotency keys and the customer lock, and `tests/test_safety.py`
asserts it directly - including concurrent execution of the same action.

## Reproducing

```bash
cd backend
python -m scripts.seed                    # generate + train
curl -X POST localhost:8000/api/v1/ops/cycle    # scan + tick, repeat 3-4 times
curl localhost:8000/api/v1/ops/model
curl localhost:8000/api/v1/ledger/summary
curl localhost:8000/api/v1/ledger/ab-test
curl localhost:8000/api/v1/dashboard/safety
curl localhost:8000/api/v1/audit/verify
```

Figures move with the seed, the number of cycles and how many approvals a human grants. The
relationships - Brier below the base-rate-only baseline, incremental well under gross, duplicates at
zero - are what should hold every time.
