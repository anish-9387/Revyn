# Revyn

In India, the retry is not a free resource. It is a regulated, exhaustible, four-shot budget - and a large share of failures cannot be retried at all.

**AI revenue recovery and autonomous revenue protection.** Revyn watches a merchant's payment stream, works out *why* money is leaking, decides what to do about each individual failure, asks permission when the stakes are high, acts, verifies the result, and books only the revenue it can defend as incremental.

It is a closed loop, not a dashboard:

```
OBSERVE -> DETECT -> DIAGNOSE -> PREDICT -> DECIDE -> GATE -> ACT -> VERIFY -> LEARN
```

Four loss classes are tracked end to end: **failed payments**, **checkout abandonment**, **failed subscription renewals**, and **overdue invoices**.

## Three Pillars

### Mandate Retry Sequencer
Intelligent scheduling of eNACH and UPI AutoPay retries to maximize success within NPCI's strict four-attempt limit.

### Futility Engine
Detects permanent failures (closed accounts, revoked mandates) early to prevent wasting retry budget and incurring unnecessary gateway fees.

### Hinglish Outreach
Hyper-personalized, context-aware messaging over WhatsApp that mixes Hindi and English to reach customers natively, increasing conversion on manual interventions.

## The one rule that shapes the architecture

> **The LLM never controls a financial API.**

Reasoning is advisory. The `ReasoningProvider` returns a hypothesis or `None`; the deterministic engines score every option, the policy engine gates it, and only `Executor` touches the gateway through an idempotency key. Pull the API key and the loop still runs - `reasoning: deterministic` instead of `reasoning: claude`, same guardrails, same audit chain.

## Layout

```
backend/
  app/
    agents/        8 agents: sentinel investigator strategist optimizer
                   policy_officer executor verifier learner
    engines/       deterministic scoring: risk, root_cause, decision, counterfactual,
                   degradation, leakage, learning, simulator, features, mandate
    services/      orchestrator, journey machine, policy, ledger, audit, idempotency, seeding
    ml/            training, calibrated predictor, metrics (Brier / log-loss / AUC / calibration)
    integrations/  razorpay (client + simulator), llm (anthropic + deterministic), messaging
    models/        SQLAlchemy 2.0 async models, mandate
    schemas/       Pydantic read/write contracts
    api/v1/routes/ 45 HTTP endpoints
    core/          config, db, clock, cache, money, logging, errors, constants
    workers/       asyncio scheduler
  scripts/seed.py  synthetic data generator CLI
  tests/           79 tests
frontend/
  src/app/         13 App Router pages
  src/components/  ui / charts / domain / layout
  src/lib/         typed API client, hooks, formatters, theme
docs/              architecture, evaluation, demo script
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

**All mutating API endpoints require an API key via the X-API-Key header. Read endpoints are open for the demo.** There is no session, no role check, and no rate limit. That includes:

| Endpoint | Effect |
| --- | --- |
| `POST /api/v1/ops/seed` | wipes and regenerates the entire database |
| `POST /api/v1/policies/kill-switch` | turns autonomous action on or off |
| `PATCH /api/v1/policies/active` | rewrites every guardrail, including spend limits |
| `POST /api/v1/approvals/{id}/approve` | authorises a real financial action |
| `POST /api/v1/simulator/apply` | promotes a simulated policy to live |
| `POST /api/v1/journeys/{id}/stop` | terminates a customer journey |
| `POST /api/v1/ops/inject-timeout` | injects gateway faults |

CORS is limited to `http://localhost:3000` by default; that is a browser convention, **not** an access control - `curl` ignores it entirely. This is acceptable for a local demo and is not acceptable anywhere else. Before any shared deployment, put authentication in front of the API (a reverse proxy with an auth layer, or FastAPI dependencies on the mutating routers), and treat `POST /ops/*` and the approval routes as privileged.

The Razorpay integration also defaults to `REVYN_GATEWAY=simulator`, so no real money moves until that is deliberately switched and test keys are supplied.

## Configuration

Every backend setting is `REVYN_`-prefixed and lives in `backend/app/core/config.py`; `.env.example` documents the full set. The ones that change behaviour most:

| Variable | Default | Notes |
| --- | --- | --- |
| `REVYN_DATABASE_URL` | `sqlite+aiosqlite:///./revyn.db` | Compose overrides with `postgresql+asyncpg://` |
| `REVYN_REDIS_URL` | unset | falls back to in-process locks and cache |
| `ANTHROPIC_API_KEY` | unset | absent = deterministic reasoning, loop unaffected |
| `REVYN_LLM_MODEL` | `claude-opus-5` | advisory reasoning only |
| `REVYN_GATEWAY` | `simulator` | `razorpay` needs test keys |
| `REVYN_SCHEDULER_ENABLED` | `true` | background OBSERVE/ACT loop |
| `REVYN_SCHEDULER_INTERVAL_SECONDS` | `10` | wall-clock tick |
| `REVYN_CLOCK_SPEEDUP` | `120` | 1 real second = 2 simulated minutes |
| `REVYN_MAX_ACTIONS_PER_TICK` | `25` | blast-radius cap on the executor |
| `REVYN_SYNTHETIC_TRANSACTIONS` | `10000` | training corpus size |
| `NEXT_PUBLIC_API_BASE_URL` | `http://localhost:8000/api/v1` | inlined into the client bundle at build |

## How a recovery happens

| Stage | Agent | What it produces |
| --- | --- | --- |
| DETECT | Sentinel | at-risk events, degradation signals per route/method/issuer |
| DIAGNOSE | Investigator | a root cause layered as `gateway / issuer / customer / product / behavioural` |
| PREDICT | Optimizer | calibrated recovery probability + counterfactual uplift per candidate action |
| DECIDE | Strategist | ranked options by expected value, with the reasoning trace |
| GATE | Policy Officer | allow / block / require-approval against the live guardrails |
| ACT | Executor | the only component that calls the gateway, always with an idempotency key |
| VERIFY | Verifier | confirms the outcome with the gateway before booking anything |
| LEARN | Learner | updates the per-merchant playbook: which action wins in which context |

Guardrails are data, not code: contact caps, retry caps, discount ceilings, minimum confidence, minimum expected value, approval thresholds, quiet hours, cooldowns, a degradation retry guard, and a kill switch - all editable at `/policies` and all versioned.

Every state change is appended to a **hash-chained audit log**; `GET /api/v1/audit/verify` recomputes the chain and reports the first broken link, if any.

## API surface

45 endpoints under `/api/v1`, grouped as: `health`, `dashboard` (overview / activity / safety), `risk`, `decisions`, `journeys` (+ pause/resume/stop), `approvals` (+ approve/reject), `degradation` (live / series), `leakage` (graph / insights), `ledger` (summary / entries / ab-test), `playbook`, `policies` (active / kill-switch), `simulator` (what-if / apply), and `ops` (seed, scan, cycle, tick, scheduler start/stop, model, model/train, inject-timeout, extract-promise).

Interactive docs at `http://localhost:8000/docs`.

## Interface

Thirteen pages, all reading the same API the way an operator would:

`/` command centre &middot; `/radar` every at-risk rupee ranked &middot; `/journeys` (+ detail) workflows in flight &middot; `/approvals` actions waiting on a human &middot; `/decisions` (+ detail) why each action was chosen &middot; `/leakage` where revenue escapes &middot; `/simulator` score a policy before it ships &middot; `/ledger` the credit Revyn can defend &middot; `/playbook` what works for this merchant &middot; `/policies` guardrails and kill switch &middot; `/audit` the hash chain.

Charts follow a fixed hue-per-entity palette, never a dual axis, and every chart has a table view; status colour is always paired with an icon and a label. Both themes are contrast-checked.

## Measured results

From the run recorded on 2026-09-01 (seed `20260901`, simulator gateway, live Anthropic reasoning), after 4 cycles and ~20 scheduler ticks over a freshly generated book:

**Model** - `gbdt-isotonic-202609011424`, holdout n=1,999, base rate 0.3527

| Metric | Value |
| --- | --- |
| Brier score | 0.19782 |
| Log loss | 0.58011 |
| ROC AUC | 0.7197 |
| Calibration error | 0.0187 |

**Money** - the headline KPI is *incremental* net, not gross:

| Figure | Value |
| --- | --- |
| At risk (start of run) | ₹8.90L |
| Gross recovered | ₹3.15L |
| Estimated organic (would have paid anyway) | ₹0.59L |
| Recovery cost | ₹185 |
| **Incremental net revenue recovered** | **₹2.43L** |
| Cost per recovery | ₹3.76 |

**A/B, control vs treatment** - the result that matters is more money with *less* customer friction:

| Arm | n | Recovery rate | Contacts per event |
| --- | --- | --- | --- |
| Control (fixed retry schedule) | 16 | 18.8% | 0.00 |
| Treatment (Revyn) | 104 | 47.1% | 0.73 |

+28.4pp recovery lift. Per-action incremental net: WhatsApp ₹1.94L (28 recoveries), voice ₹0.30L (10), alternate payment method ₹0.15L (5), payment link ₹0.02L, retry ₹0.02L, discount ₹0.01L.

**NPCI Mandate Metrics** - optimizing within the four-shot budget:

| Metric | Value |
| --- | --- |
| Futile retries skipped | 100% |
| Success within 4-shot limit | 89% |
| Avg attempts per recovery | 1.8 |

**Safety** - 82 actions executed, **0 duplicate executions**, **0 unauthorised actions**, 40 blocked by policy, 4 rejected by a human, audit chain `valid: true` across 781 entries.

**Graceful failure** - `POST /api/v1/ops/inject-timeout {"count":3,"payment_already_succeeded":true}` then one cycle: Revyn logged *"gateway state ambiguous, verifying before any retry"*, queried the gateway, discovered the payment had already succeeded, booked the recovery and closed the journey. No double charge. See `docs/demo-script.md`.

Re-run these yourself: `python -m scripts.seed` then `POST /api/v1/ops/cycle` a few times, and read `GET /api/v1/ledger/summary`, `/ledger/ab-test`, `/dashboard/safety`, `/ops/model`, `/audit/verify`. Numbers will differ with a different seed or a different number of cycles.

## Quality gates

```bash
cd backend  && pytest -q && ruff check .        # 79 passed, ruff clean
cd frontend && npm run typecheck && npm run lint && npm run build
```

All five were green at the last run: 79 tests passing, `ruff` clean, `tsc --noEmit` exit 0, `eslint .` exit 0, `next build` producing 11 static and 2 dynamic routes.

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

- `docs/architecture.md` - how the layers fit, and where to put a new agent or action
- `docs/evaluation.md` - how the probability model and the money attribution are measured
- `docs/demo-script.md` - a walkthrough with the exact calls, in order