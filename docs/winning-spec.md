# Revyn - The Selling Point, and how to build it

Track 03, AI Revenue Recovery. This document is written to be handed to a coding agent. It contains
the positioning, the reasoning behind it, and a file-by-file implementation plan against the code
that already exists in this repo.

---

## Part 1 - The selling point, in one sentence

> **In India, the retry is not a free resource. It is a regulated, exhaustible, four-shot budget -
> and a large share of failures cannot be retried at all. Revyn is the only recovery agent that
> knows the difference between a payment that failed and a payment that is *forbidden to retry*.**

Pitch title: **The Retry Budget is a Regulated Resource.**

### Why this is the right selling point

**It is the one thing the track asked for that nobody builds.** The example directions on the track
card include *Mandate retry sequencer* and *Hinglish voice recovery*. Those two bullets are the only
India-specific items on the card, and they are there because Razorpay knows that card-rail dunning
logic - the Stripe/Churn Buster/Butter model that every entrant will reimplement - is structurally
wrong on UPI and NACH rails.

**The facts underneath it are hard, checkable, and recent** (a Razorpay judge will know all of them,
which is exactly why citing them lands):

| Fact | Consequence for a recovery agent |
|---|---|
| UPI AutoPay mandate failures run **8–15%**, vs **2–3%** for card mandates | The Indian recovery problem is *bigger* than the card-world literature assumes |
| Since **1 Aug 2025**, NPCI permits **1 initial presentation + 3 retries = 4 attempts total** per mandate sequence number | The retry budget is finite and regulator-enforced. Wasting one is permanent, irreversible loss |
| NPCI 2026 traffic management pushes recurring debits **out of the 10:00–13:00 IST peak** into before 10:00, 13:00–17:00, or after 21:30 | A debit presented at 10:30 takes a *technical* decline that has nothing to do with the customer. A naive agent then "retries the customer" and burns budget on a scheduling bug |
| RBI e-mandate framework requires a **pre-debit notification ≥24h before every debit**; if the PDN did not land, the debit is blocked **even with a valid mandate** | The PDN is both a compliance precondition *and* the single best recovery touchpoint you get |
| Under UPI AutoPay operating guidelines, **if the first presentation fails, the mandate can be auto-revoked** | The first attempt is worth far more than the others. Order of operations is everything |
| AFA-free ceiling is **₹15,000** (₹1L for SIP / insurance / credit card) | Above it, every renewal needs fresh customer auth. A price increase past the cap silently converts a working subscription into a permanently failing one |
| There are **four structurally distinct mandate failure modes** - no mandate, mandate revoked, charge exceeds cap, PDN not delivered - and **none is fixable by retrying** | The bank returns the identical answer at 2am, at noon and three days later. Each needs a *different customer action*. A generic "update your payment method" email routes all four to the wrong place |

> Verify these against the current NPCI circulars and Razorpay's own subscription docs before you
> record the pitch. They were accurate as researched, but this is a Razorpay audience - quoting a
> superseded number is worse than quoting none.

**It reframes your existing strengths instead of discarding them.** Your uplift-based decision
engine, incrementality ledger, policy gate and audit chain all stay exactly as they are. This adds a
new *cause layer* and a new *budget dimension* to structures that already exist.

**It produces a metric no other entrant can show.** Alongside money recovered:

> **NPCI attempts wasted: baseline 3.1 per mandate → Revyn 0.4.**

That is a number a payments company understands instantly, and it cannot be faked by a team that did
not model the rail.

### The three-line version for the video

1. Every dunning system treats a failed payment as "try again later."
2. In India, four of the most common failure modes are *regulatory states*, not transient errors -
   retrying them is guaranteed to fail, and you only get four attempts before the mandate dies.
3. Revyn diagnoses the regulatory state, spends **zero** attempts on it, and routes the customer to
   the one action that actually resolves it - in their language.

---

## Part 2 - The three pillars to build

Everything below maps to a track-card bullet, so name them that way in the README.

### Pillar A - Mandate Retry Sequencer *(track bullet, verbatim)*

A scheduler that treats NPCI attempts as a spendable budget and refuses to waste one.

- Hard **4-attempt ledger** per mandate sequence number, surfaced in the UI as "attempts remaining."
- **Execution-window guard**: never present inside 10:00–13:00 IST. Defer, don't spend.
- **PDN precondition**: a presentation is unschedulable unless a PDN was sent ≥24h earlier. `SEND_PDN`
  becomes an action the agent *chooses*, and is treated as a recovery touchpoint (balance top-up
  nudge inside the 24h window), not a compliance chore.
- **First-presentation protection**: because a failed first presentation can revoke the mandate, the
  first attempt requires a materially higher predicted success than later ones. Model this as a
  policy rule, not a constant.
- **Salary-cycle timing** for insufficient-balance: bias presentation toward 1st–3rd and 25th–31st.

### Pillar B - The Futility Engine *(the actual novelty)*

The part that makes judges sit up. A new `CauseLayer.REGULATORY` whose causes are **hard-blocked
from retry**, each mapped to the one action that resolves it.

| Root cause | What retrying does | Correct action |
|---|---|---|
| `MANDATE_ABSENT` | Fails identically, forever | `REREGISTER_MANDATE` - AFA link (3DS for card, UPI PIN for UPI) |
| `MANDATE_REVOKED` | Fails identically, forever | `REREGISTER_MANDATE` + copy acknowledging the customer chose to cancel |
| `MANDATE_CAP_EXCEEDED` | Fails identically, forever | `AMEND_MANDATE_CAP` at the new amount |
| `PDN_NOT_DELIVERED` | Fails identically, forever | `RESEND_PDN`, then present ≥24h later |
| `AFA_REQUIRED` (amount > ₹15,000) | Fails until the customer authenticates | Outreach *inside* the 24h pre-debit window with an auth link |

The headline guardrail: **`RETRY_FUTILE` - for any regulatory-layer cause, `RETRY_PAYMENT` is
hard-blocked with `PolicyVerdict.BLOCK`, not merely down-weighted.**

Say this on camera: *"A generic dunning agent burns all four NPCI attempts on a mandate that was
revoked. It cannot succeed - not once. Revyn spends zero, and sends a re-registration link instead."*

### Pillar C - Hinglish outreach with a deterministic validator *(track bullet, and your answer to "why an LLM?")*

Today `integrations/messaging.py` holds four hardcoded English templates and six canned voice
replies. Replace with a two-stage design:

1. **LLM generates** the message in the customer's language register - Hinglish, Tamil-English,
   formal B2B English - chosen from customer signals, matched to the specific regulatory cause.
2. **A deterministic validator gates every generated message before send**, and a failed validation
   falls back to the static template. Checks:
   - every number, amount and date in the output must match the event record exactly (regex-extract
     and compare - this kills hallucinated amounts, the one unforgivable failure in fintech);
   - the message must map to an approved DLT template shape with only whitelisted variables;
   - no commitment the merchant did not authorise (no invented discounts, deadlines or waivers);
   - consent and opt-out state honoured; quiet hours respected;
   - length and channel constraints.
3. **Hinglish promise-to-pay extraction**: extend the extractor your `Verifier` already calls so it
   handles *"paisa Monday tak aa jayega, thoda time do"* → `{promised: true, date: <next Monday>,
   confidence: 0.72}`. Your `RecoveryJourney` already has `promise_date` and `promise_confidence`
   columns and a `PROMISE_FOLLOWUP` action - this is mostly prompt and test work.

This gives you a clean, rehearsed answer to the hardest question on the AI Judgment axis:

> *"The LLM does two things deterministic code cannot: generate natural language in a code-mixed
> register, and understand unstructured speech. It does not choose actions, it does not touch the
> gateway, and even its language output is validated by deterministic code before it reaches a
> customer. Everything else in Revyn is deterministic on purpose."*

---

## Part 3 - Implementation plan

Ordered so that the demo is winnable even if you stop after Phase 2.

### Phase 0 - Credibility fixes (do first, ~1 hour)

**0.1 Authenticate the mutating API.** `POST /ops/seed` wipes the DB and
`POST /approvals/{id}/approve` authorises a financial action - both currently open. On a track whose
bar is *compliant escalation*, this is a free point to lose.

- Add `REVYN_API_KEY` to `app/core/config.py`.
- Add `require_api_key` dependency in `app/api/deps.py`, checking the `X-API-Key` header.
- Apply to every mutating router: `ops`, `policies`, `approvals`, `simulator/apply`, `journeys`
  (pause/resume/stop). Leave reads open for the demo.
- Frontend sends the key from a server-side env var.
- Update the README security section from "the API is unauthenticated" to "mutating routes require
  an API key; reads are open for the demo."

**0.2 One real Razorpay test-mode call.** Flip `REVYN_GATEWAY=razorpay` for a single scripted path,
create a real test-mode payment link or subscription, let `Executor` call it, and show the real
`plink_...` / `sub_...` id landing in the audit chain. Keep the simulator for the batch. This kills
"it's all synthetic" in fifteen seconds.

### Phase 1 - The Futility Engine (the novelty; build this even if nothing else ships)

**1.1 `app/core/constants.py`**
```python
class CauseLayer(StrEnum):
    ...
    REGULATORY = "regulatory"          # NEW

class FailureCode(StrEnum):
    ...
    MANDATE_NOT_FOUND      = "mandate_not_found"
    MANDATE_REVOKED        = "mandate_revoked"
    MANDATE_AMOUNT_EXCEEDS = "mandate_amount_exceeds"
    PDN_NOT_DELIVERED      = "pdn_not_delivered"
    AFA_REQUIRED           = "afa_required"
    MANDATE_PAUSED         = "mandate_paused"

class RootCause(StrEnum):
    ...
    MANDATE_ABSENT        = "mandate_absent"
    MANDATE_REVOKED       = "mandate_revoked"
    MANDATE_CAP_EXCEEDED  = "mandate_cap_exceeded"
    PDN_MISSING           = "pdn_missing"
    AFA_THRESHOLD_BREACH  = "afa_threshold_breach"
    EXECUTION_WINDOW_MISS = "execution_window_miss"   # technical decline, NOT customer fault

class ActionType(StrEnum):
    ...
    REREGISTER_MANDATE = "reregister_mandate"
    AMEND_MANDATE_CAP  = "amend_mandate_cap"
    SEND_PDN           = "send_pdn"
    SWITCH_RAIL        = "switch_rail"       # card e-mandate -> UPI AutoPay

class PolicyRule(StrEnum):
    ...
    RETRY_FUTILE            = "retry_futile"
    NPCI_BUDGET_EXHAUSTED   = "npci_budget_exhausted"
    OUTSIDE_EXECUTION_WINDOW = "outside_execution_window"
    PDN_PRECONDITION_UNMET  = "pdn_precondition_unmet"
    FIRST_PRESENTATION_GUARD = "first_presentation_guard"
```
Add the new mandate actions to `CONTACT_ACTIONS` / `FINANCIAL_ACTIONS` as appropriate (`SEND_PDN`
is a contact; `REREGISTER_MANDATE` and `AMEND_MANDATE_CAP` are financial and should require
approval above a threshold).

**1.2 `app/data/catalog.py`** - add `Intervention` entries for the four new actions (cost, friction,
base success), add `REGULATORY` cause profiles with their `ALLOWED_ACTIONS` sets (**note:
`RETRY_PAYMENT` must be absent from every regulatory cause's allowed set**), and extend
`FAILURE_LABELS` and the failure-code → root-cause mapping.

**1.3 `app/engines/root_cause.py`** - map the new failure codes to the new causes with
`CauseLayer.REGULATORY`. This must be **deterministic and confident**: these are unambiguous
regulatory states read off a code, not a judgement call. The LLM must not be able to override a
regulatory diagnosis - call that out explicitly in the pitch.

**1.4 `app/services/policy.py`** - the guardrail itself:
```python
# In the gate, before any scoring:
if diagnosis.cause_layer is CauseLayer.REGULATORY and action is ActionType.RETRY_PAYMENT:
    return GateVerdict(PolicyVerdict.BLOCK, [PolicyRule.RETRY_FUTILE])
```
Add `PolicySpec` fields: `npci_max_attempts: int = 4`,
`execution_window_guard: bool = True`, `pdn_lead_hours: float = 24.0`,
`first_presentation_min_confidence: float = 0.55`, `afa_free_ceiling_paise: int = 15_000_00`.
They are then automatically editable at `/policies`, versioned, and simulatable - which is a nice
thing to point out on camera.

**1.5 `app/engines/decision.py`** - regulatory causes should surface a strong `rationale` string
("retry is futile: mandate revoked by customer on <date>; only re-registration can resolve this"),
and the futile-retry option must appear in `alternatives` **with its block reason visible**, so
`/decisions/[id]` shows the judge the road not taken. That page is your best evidence artifact.

**1.6 Data + tests** - teach `app/data/generator.py` to emit mandate-failure events (target ~15% of
`SUBSCRIPTION_FAILURE`), give them realistic organic rates in `app/data/outcome.py` (near-zero
organic recovery for revoked mandates - they genuinely never self-heal), and add
`backend/tests/test_mandate.py` asserting: retry is BLOCKED for every regulatory cause; the NPCI
budget never exceeds 4; nothing is presented in the peak window; no presentation without a PDN ≥24h
prior.

### Phase 2 - The Sequencer and the metric that wins

**2.1 New model `app/models/mandate.py`**
```python
class Mandate(Base, TimestampMixin):
    __tablename__ = "mandates"
    id, customer_id, external_ref
    rail: MandateRail          # upi_autopay | card_emandate | nach
    status: MandateStatus      # active | revoked | paused | expired | pending_registration
    max_amount_paise: int      # the cap; breaching it is MANDATE_CAP_EXCEEDED
    sequence_number: int
    attempts_used: int         # 0..4  <-- the regulated budget
    last_pdn_sent_at: datetime | None
    registered_at, revoked_at, next_due_at
```
Add `mandate_id` FK to `RevenueEvent`, and `npci_attempts_used` to `RecoveryJourney` alongside the
existing `retries_used` - keep them separate, because they mean different things and the distinction
is the point.

**2.2 New engine `app/engines/mandate.py`** - pure functions, unit-testable without a session:
```python
def attempts_remaining(mandate) -> int
def in_execution_window(when: datetime) -> bool            # False for 10:00-13:00 IST
def next_valid_presentation_slot(after, *, prefer_salary_cycle: bool) -> datetime
def pdn_satisfied(mandate, present_at, *, lead_hours=24.0) -> bool
def is_retry_futile(root_cause) -> bool
def required_remedy(root_cause) -> ActionType
```
Reuse `IST_OFFSET_HOURS` from `app/engines/features.py`.

**2.3 `app/services/orchestrator.py`** - when scheduling a mandate presentation, defer rather than
spend if outside the window, refuse if the budget is exhausted, and require the PDN precondition.
Every deferral must be audited with its reason - this is your "compliant escalation, stopping rules"
evidence.

**2.4 The metric.** Add to `GET /api/v1/ledger/summary` and `/dashboard/safety`:
```
npci_attempts_available, npci_attempts_spent, npci_attempts_wasted,
futile_retries_prevented, mandates_saved_from_revocation
```
where *wasted* = an attempt spent on a regulatory cause that could never succeed. Then extend
`app/engines/simulator.py`'s `LEGACY_WORKFLOW` baseline to report the same fields, so `/simulator`
renders one chart:

> **Generic dunning: 3.1 attempts wasted per mandate, 8 mandates auto-revoked, ₹X lost.
> Revyn: 0.4 wasted, 0 revoked, ₹Y recovered.**

That chart is the single most valuable asset in the whole submission. Build it.

### Phase 3 - Hinglish (highest pitch value per line of code)

**3.1 `app/integrations/messaging.py`** - introduce `generate_message(...)` that calls the reasoner
for a code-mixed message, then `validate_message(...)` which returns `(ok, violations)` and forces
the static template on failure. Log every validation failure to the audit chain - *showing the LLM
being caught and overridden is a stronger demo than showing it succeed.*

**3.2 `app/integrations/llm/prompts.py`** - Hinglish generation prompt per (cause, channel,
segment); extend the promise-extraction prompt with Hinglish examples and relative-date handling
(*kal, parso, agle Monday, salary aane ke baad*).

**3.3 Frontend** - on `/journeys/[id]`, show the generated message, the language register, and a
green/red validator badge. On `/decisions/[id]`, show the blocked futile retry with its
`RETRY_FUTILE` reason.

**3.4 `POST /api/v1/ops/extract-promise`** already exists - add Hinglish examples to `/docs` so a
judge can paste one in and watch it work. Cheap, memorable.

### Do not build

More pages, more endpoints, more agents, a chat interface, a second ML model. You already have more
surface than you can demo in five minutes. Depth on one rail beats breadth across four.

---

## Part 4 - The five-minute pitch

| Time | Beat |
|---|---|
| 0:00–0:40 | **The hook.** "UPI AutoPay fails 5x more often than card mandates, and NPCI gives you exactly four attempts - ever. Four of the most common failure modes are regulatory states that *cannot* be retried. Every dunning system on the market retries them anyway, burns the budget, and the mandate gets revoked. That is not a missed recovery, that is a customer you can never bill again." |
| 0:40–1:00 | **The claim.** "Revyn treats the retry budget as the regulated, exhaustible resource it is." |
| 1:00–2:20 | **The live path.** Mandate failure → diagnosed `MANDATE_REVOKED`, `CauseLayer.REGULATORY` → `/decisions/[id]` showing `RETRY_PAYMENT` **blocked, `RETRY_FUTILE`**, attempts spent **0** → Hinglish re-registration message, validator green → recovered → audit chain entry with the real test-mode ref. |
| 2:20–3:20 | **Measured money across a batch.** Gross vs **incremental** - and explicitly say the smaller number is the honest one and why. A/B: +28.4pp at 0.73 contacts/event. Then the killer chart: **attempts wasted, baseline vs Revyn.** |
| 3:20–4:05 | **AI judgment.** The LLM never controls a financial API - it has exactly two jobs, language and unstructured speech, and even those are deterministically validated. Show a validator *catch* a bad generation. One line on calibration-as-safety: "a miscalibrated model doesn't just mispredict, it authorises spend the guardrails exist to prevent." |
| 4:05–4:45 | **Failure recovery.** The injected ambiguous gateway timeout where the payment had already succeeded - "gateway state ambiguous, verifying before any retry" → verified → booked → no double charge. Then your real dev failure (hydration / SDK detection) as diagnose → fix → learn. |
| 4:45–5:00 | **Honest limits.** Synthetic corpus, simulator by default, real API on one path, what you'd build next. |

**README first paragraph must be rewritten to lead with the retry-budget thesis.** Right now it opens
with "AI revenue recovery and autonomous revenue protection," which is what every other entry says.

---

## Part 5 - Why this wins on all four axes

| Axis | The argument |
|---|---|
| **Problem taste** | You found a problem that is real, Indian, regulatory, expensive, and invisible to anyone who learned dunning from Stripe's docs. You can name the exact NPCI circular behind it. |
| **Build quality** | Already your strongest axis: 79 tests, ruff/tsc/eslint clean, protocol seams, hash-chained audit. Phase 0 removes the one soft spot. |
| **AI judgment** | You can point at a large deterministic system and say precisely where the LLM is *not*, and give it two jobs it uniquely deserves - with a validator that overrides it on camera. |
| **Failure recovery** | Two layers: the ambiguous-gateway path already built, plus a real development war story. |

The incrementality ledger stays your integrity proof. The Futility Engine becomes your idea. Lead
with the idea, close with the integrity.