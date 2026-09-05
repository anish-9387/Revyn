# Revyn

In India, the retry is not a free resource. It is a regulated, exhaustible, four-shot budget - and a large share of failures cannot be retried at all.

**AI revenue recovery and autonomous revenue protection.** Revyn watches a merchant's payment stream, works out *why* money is leaking, decides what to do about each individual failure, asks permission when the stakes are high, acts, verifies the result, and books only the revenue it can defend as incremental.

It is a closed loop, not a dashboard:

```
OBSERVE -> DETECT -> DIAGNOSE -> PREDICT -> DECIDE -> GATE -> ACT -> VERIFY -> LEARN
```

Four loss classes are tracked end to end: **failed payments**, **checkout abandonment**, **failed subscription renewals**, and **overdue invoices**.

## Three Pillars - The Retry Budget is a Regulated Resource

**Mandate Retry Sequencer** - Hard 4-attempt ledger per mandate sequence number, NPCI execution-window guard (never 10:00–13:00 IST), PDN 24h precondition, first-presentation protection, and salary-cycle timing. Attempts remaining are surfaced in the UI.

**Futility Engine** - `CauseLayer.REGULATORY` with `RETRY_FUTILE` hard-blocking `RETRY_PAYMENT` (`PolicyVerdict.BLOCK`, not down-weight). Covers `MANDATE_ABSENT`, `MANDATE_REVOKED`, `MANDATE_CAP_EXCEEDED`, `PDN_MISSING`, `AFA_THRESHOLD_BREACH`, `EXECUTION_WINDOW_MISS`. Generic dunning wastes 3.1 attempts/mandate; Revyn wastes ~0.4 and saves mandates from auto-revocation.

**Hinglish Outreach with Deterministic Validator** - LLM generates code-mixed outreach per `(cause, channel, segment)`; a deterministic validator gates every message before send (amount/date must match the event record exactly, DLT shape, no invented discounts/deadlines, consent and window respected). Hinglish promise extraction handles `paisa Monday tak aa jayega, kal, parso, salary aane ke baad` → `promise_date` on the journey.

## The one rule that shapes the architecture

> **The LLM never controls a financial API.**

Reasoning is advisory. The `ReasoningProvider` returns a hypothesis or `None`; the deterministic engines score every option, the policy engine gates it, and only `Executor` touches the gateway through an idempotency key. Pull the API key and the loop still runs - `reasoning: deterministic` instead of `reasoning: claude`, same guardrails, same audit chain.

## Layout

```
backend/
  app/
    agents/        8 agents: sentinel investigator strategist optimizer
                   policy_officer executor verifier learner
    engines/       risk, root_cause, decision, counterfactual, degradation,
                   leakage, learning, simulator, features, mandate
    services/      orchestrator, journey, policy, ledger, audit, idempotency, seeding
    ml/            HistGradientBoosting + isotonic calibration + metrics
    integrations/  razorpay (client + simulator), llm (anthropic + deterministic), messaging
                   └ messaging: generate_message → validate_message (DLT, amount hallucination guard)
    models/        SQLAlchemy 2.0 async: customer, event, mandate, journey, policy, audit, ledger
    schemas/       Pydantic read/write contracts
    api/v1/routes/ health, dashboard, risk, journeys, decisions, approvals, policies,
                   simulator, ledger, leakage, playbook, audit, ops
    core/          config, db, clock, cache, money, logging, errors, constants
    workers/       asyncio scheduler
  scripts/seed.py  synthetic generator + mandate factory
  tests/           79 tests + mandate invariants
frontend/
  src/app/         (marketing) landing + (dashboard) 12 operator pages (App Router)
  src/components/  ui / charts / domain / layout (light premium, lucide-react + framer-motion)
  src/lib/         api client (X-API-Key), hooks, formatters, theme, icons, motion
docs/              architecture.md, evaluation.md, demo-script.md, winning-spec.md
```

## Quick start

### Docker (everything, including Postgres and Redis)

```bash
cp .env.example .env          # optional: add ANTHROPIC_API_KEY
docker compose up --build
```

Backend on `http://localhost:8000` (docs at `/docs`), frontend on `http://localhost:3000`. The `seed` service runs once and exits after generating data and training the model.

### Local, without Docker

Backend:

```bash
cd backend
python -m venv venv
venv/Scripts/activate            # PowerShell: venv\Scripts\Activate.ps1
                                  # macOS/Linux: source venv/bin/activate
pip install -e ".[dev]"
python -m scripts.seed            # ~1400 customers, 10000 training events, then trains
uvicorn app.main:app --reload --port 8000
```

Frontend, in a second shell:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Python 3.11+ and Node 20+. SQLite is the default database, so nothing else is required.

### Make targets

A `Makefile` wraps the above (`make setup`, `seed`, `dev`, `test`, `lint`, `typecheck`, `build`, `cycle`, `metrics`, `up`, `down`, `clean`; `make help` lists them). It is untested on Windows without `make` installed - the raw commands above and below are the source of truth there.

## Security

**Mutating routes require `X-API-Key` when `REVYN_API_KEY` is set; reads are open.** If `REVYN_API_KEY` is empty (default), mutating routes are open - fine for local demo, not for shared deploy. No session/role/rate-limit beyond that.

Protected mutating routes: `POST /ops/seed|scan|tick|cycle|inject-timeout`, `PATCH /policies/active`, `POST /policies/kill-switch`, `POST /approvals/{id}/approve|reject`, `POST /simulator/apply`, `POST /journeys/{id}/pause|resume|stop`. Frontend sends the key via `NEXT_PUBLIC_API_KEY` (inlined at build).

CORS is limited to `http://localhost:3000` - browser-only, not access control. For shared deploy, also front the API with a proxy/auth layer.

`REVYN_GATEWAY=simulator` by default, so no real money moves. Switch to `razorpay` only with test keys; one real `plink_...`/`sub_...` path is enough to prove the loop against live APIs while batching stays synthetic.

## Configuration

All settings are `REVYN_`-prefixed in `backend/app/core/config.py`; `.env.example` is the complete reference.

**Must set to run against your own infra:**

| Variable | Default | When to set |
| --- | --- | --- |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | Always - must match backend `REVYN_API_PREFIX` |
| `REVYN_DATABASE_URL` | `sqlite+aiosqlite:///./revyn.db` | Production - `postgresql+asyncpg://revyn:revyn@postgres:5432/revyn` |
| `REVYN_API_KEY` + `NEXT_PUBLIC_API_KEY` (same value) | unset (open) | Any shared/demo URL - otherwise anyone can `POST /ops/seed` or approve a financial action |
| `ANTHROPIC_API_KEY` | unset (deterministic) | To enable Hinglish generation + promise extraction via `claude` (falls back silently when absent or unreachable) |
| `REVYN_GATEWAY` + `REVYN_RAZORPAY_KEY_ID/SECRET` | `simulator` | To run one live Razorpay test-mode path; leave `simulator` for offline batch |

**Tuning (optional):** `REVYN_REDIS_URL` (multi-replica locks), `REVYN_LLM_MODEL` (`claude-sonnet-4-20250514`), `REVYN_SCHEDULER_ENABLED`/`INTERVAL_SECONDS`/`CLOCK_SPEEDUP` (120× demo), `REVYN_MAX_ACTIONS_PER_TICK` (25), `REVYN_SYNTHETIC_TRANSACTIONS` (10000), `REVYN_CORS_ORIGINS`.

## How a recovery happens

| Stage | Agent | What it produces |
| --- | --- | --- |
| DETECT | Sentinel | at-risk events, degradation signals per route/method/issuer |
| DIAGNOSE | Investigator | root cause with `CauseLayer` - `customer/payment/merchant/systemic/intent/receivable/regulatory` |
| PREDICT | Optimizer | calibrated recovery probability + counterfactual uplift per action |
| DECIDE | Strategist | ranked options by **uplift × amount − cost − friction** (not probability) |
| GATE | Policy Officer | `allow / require_approval / block` + `RETRY_FUTILE` + NPCI window/budget/PDN guards |
| ACT | Executor | only caller of the gateway; mandate-aware, always idempotent |
| VERIFY | Verifier | confirms with gateway before booking; captures `promise_date` via Hinglish extractor |
| LEARN | Learner | updates per-merchant playbook: which action wins in which context |

Guardrails are data, not code: contact/retry/discount/voice caps, discount ceilings, `min_confidence`/`min_expected_value`, approval thresholds, quiet hours/cooldowns, degradation guard, NPCI `npci_max_attempts` (4), `execution_window_guard` (10–13 IST), `pdn_lead_hours` (24), kill switch - all at `GET/PATCH /policies/active`, versioned and simulatable (`/simulator/what-if`).

Mandate state is tracked per sequence number; every regulatory cause hard-blocks `RETRY_PAYMENT`. Messaging is LLM-generated in Hinglish then deterministically validated (amount/date must match record, DLT shape, no invented offers) before send. Every state change is hash-chained; `GET /audit/verify` recomputes the chain.

## API surface

46 endpoints under `/api/v1`: `health`, `dashboard` (overview/activity/safety + NPCI `npci_attempts_spent`/`futile_retries_prevented`), `risk`, `decisions`, `journeys` (+ pause/resume/stop), `approvals` (+ approve/reject), `degradation` (live/series), `leakage` (graph/insights), `ledger` (summary/entries/ab-test + mandate `npci` stats), `playbook`, `policies` (active/kill-switch + NPCI fields), `simulator` (what-if/apply + `npci_wasted`), `ops` (seed/scan/cycle/tick/scheduler, model/train, inject-timeout, extract-promise). Reads are open; mutating routes enforce `X-API-Key` when `REVYN_API_KEY` is set.

Interactive docs at `http://localhost:8000/docs`.

## Interface

Landing `/` (product & why it wins) plus 12 operator pages: `/dashboard` command centre · `/radar` ranked rupees · `/journeys` workflows & mandates · `/approvals` human queue · `/decisions` why + blocked `RETRY_FUTILE` · `/leakage` where revenue escapes · `/simulator` score policy + NPCI wasted chart · `/ledger` defendable credit + calibration · `/playbook` what works · `/policies` guardrails + NPCI knobs · `/audit` hash chain.

Light premium theme (white/light-grey, `lucide-react` icons, framer-motion stagger), table view for every chart, fixed hue per entity, never dual-axis.

## Measured results

From run `20260901` (seed `20260901`, simulator gateway, `claude` or deterministic), after 4 cycles / ~20 ticks on a fresh book:

**Model** - `gbdt-isotonic-202609011424`, holdout n=1,999, base rate 0.3527

| Metric | Value |
| --- | --- |
| Brier score | 0.19782 |
| Log loss | 0.58011 |
| ROC AUC | 0.7197 |
| Calibration error | 0.0187 |

**Money** - headline is *incremental* net, not gross:

| Figure | Value |
| --- | --- |
| At risk (start) | ₹8.90L |
| Gross recovered | ₹3.15L |
| Estimated organic | ₹0.59L |
| Recovery cost | ₹185 |
| **Incremental net** | **₹2.43L** |
| Cost per recovery | ₹3.76 |

**A/B, control vs treatment** - more money, less friction:

| Arm | n | Recovery rate | Contacts / event |
| --- | --- | --- | --- |
| Control (fixed retry) | 16 | 18.8% | 0.00 |
| Treatment (Revyn) | 104 | 47.1% | 0.73 |

+28.4pp lift. Per-action incremental net: WhatsApp ₹1.94L (28), voice ₹0.30L (10), alt method ₹0.15L (5), link/retry/discount single-digit thousands.

**NPCI mandate metrics** - within the 4-shot budget:

| Metric | Value (last run) |
| --- | --- |
| Generic wasted attempts / mandate | 3.1 |
| Revyn wasted / mandate | 0.4 (`/simulator` reports live) |
| Mandates auto-revoked (baseline → Revyn) | 8 → 0 |
| `futile_retries_prevented` (Σ journeys) | surfaces in `/dashboard/safety` and `/ledger/summary` |
| Cost per recovery (incremental) | ₹3.76 |

**Safety** - 82 executed, **0 duplicates**, **0 unauthorised**, 40 blocked by policy (incl. `RETRY_FUTILE`), 4 human rejects, audit `valid:true` across 781 entries. `RETRY_FUTILE` is visible on `/decisions/[id]` alternatives.

**Graceful failure** - `POST /ops/inject-timeout {"count":3,"payment_already_succeeded":true}` then `POST /ops/cycle` → audit shows `gateway state ambiguous, verifying before any retry` → queried → booked, no double charge. See `docs/demo-script.md`.

Re-run: `python -m scripts.seed` then `POST /ops/cycle` ×3–4, read `GET /ledger/summary`, `/ledger/ab-test`, `/dashboard/safety`, `/ops/model`, `/audit/verify`.

## Quality gates

```bash
cd backend  && pytest -q && ruff check .        # 79 passed, ruff clean
cd frontend && npm run lint && npm run build    # eslint + next build (light premium)
```

All were green at last run: 79 tests, `ruff` clean, `eslint` 0, `next build` 13 pages (landing + 12 dashboard). `tsc` via `next lint` - `lucide-react`/`framer-motion` bundled via `src/lib/icons.tsx` shim.

## Deviations from the PRD

Deliberate, and each one traded a dependency for something that actually runs on a laptop:

| PRD | Built | Why |
| --- | --- | --- |
| Celery + Redis workers | asyncio scheduler in-process | one process, no broker; Redis stays optional and is used only for locks/cache when present |
| XGBoost / LightGBM | scikit-learn `HistGradientBoostingClassifier` + isotonic calibration | no compiled wheels to fight, and calibration matters more than raw AUC when the probability feeds a spend decision |
| pandas feature pipeline | numpy + explicit feature builder | fewer moving parts, and every feature stays inspectable in `engines/features.py` |
| Live Razorpay | deterministic simulator by default | the demo must work offline; the real client is implemented behind the same `PaymentGateway` protocol |
| Redis-backed idempotency | pluggable `KeyStore`, in-process by default | same interface, no infrastructure requirement |

The synthetic corpus, the 13-state journey machine, all 4 loss classes, all 8 agents, the guardrail set, the hash-chained audit, the counterfactual ledger, the A/B harness and the graceful-failure path are implemented as specified.

## Docs

- `docs/architecture.md` - layers, protocols, mandate/futility, Hinglish validator, adding actions/agents
- `docs/evaluation.md` - probability honesty, incrementality, A/B, safety + NPCI wasted
- `docs/demo-script.md` - 8-step walkthrough with exact calls; includes regulatory and Hinglish paths