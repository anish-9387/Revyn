# Revyn - Track 03 (AI Revenue Recovery) novelty review

Prepared for the Razorpay AI Buildathon submission. Two parts: (1) an honest audit of what in
Revyn is genuinely novel versus table-stakes, (2) the specific unbuilt ideas that would make it
un-copyable, ranked by effort against payoff.

---

## 0. What the track actually asks for

From the official brief:

> **03 - AI Revenue Recovery.** Build an agent that detects revenue at risk, determines the right
> intervention, and executes a bounded recovery workflow: from payment failures and checkout
> abandonment to overdue receivables.
> Example directions: payment degradation → root cause → recovery action, checkout drop-off
> recovery, failed-subscription recovery, B2B receivables chaser, mandate retry sequencer,
> Hinglish voice recovery, promise-to-pay tracker.
> **The bar:** Don't just identify the problem. Show measured money recovered across a batch, with
> compliant escalation, stopping rules, and an audit trail.

Judged on four axes: **Problem Taste, Build Quality, AI Judgment, Failure Recovery.**

Note the exact words in the bar: **"measured money"**, **"compliant escalation"**, **"stopping
rules"**, **"audit trail"**. Three of the four are safety/measurement words, not AI words. That is
the tell for how this track is scored.

Also note the two Indian-specific example directions - **mandate retry sequencer** and **Hinglish
voice recovery**. Razorpay put those in the list on purpose. They are the two things a generic
Stripe-shaped dunning clone cannot do.

---

## 1. Verdict on Revyn as it stands

**Score: strong top-decile submission on execution, currently mid-pack on novelty.**

You will beat 90% of entries on build quality. You will not automatically beat the other 10%,
because the *shape* of your system - agent detects failure → LLM diagnoses → deterministic policy
gates → executor acts with idempotency → audit log - is the exact shape three or four other serious
entrants converged on independently. I found two public ones while researching:

- `srikrishna0603/razorpay-buildathon` - "Revenue Resilience AI": LLM emits a `DiagnosisClass`,
  deterministic policy engine maps it to RETRY / OFFER_ALTERNATE_METHOD / STOP_AND_ESCALATE /
  NO_ACTION, primary-key idempotency to make double-charge physically impossible, economic floor
  (abort if amount < ₹100). That is your "LLM never controls a financial API" rule and your
  `min_expected_value` guardrail, independently invented.
- "RazorRecover AI" - LLM reasoner + deterministic baseline scoring, **9-rule deterministic policy
  engine**, explainable decisions with confidence and decision source, failure→treatment mapping
  (OTP abandonment → resume checkout, insufficient funds → alternate route, bank timeout → delayed
  retry), human-in-the-loop approvals for high-value actions.

So: "LLM advises, deterministic engine decides, idempotency guarantees exactly-once, human approves
high-value" is **the consensus architecture of this track**, not your differentiator. Say it in the
pitch as a *competence signal* and move on in 20 seconds. Do not build the pitch around it.

### 1.1 What IS genuinely novel in Revyn

Four things. In descending order of how rare they are.

| # | Thing | Where | Why it is rare |
|---|---|---|---|
| **1** | **Incrementality as the headline KPI**, with a live control holdout | `engines/counterfactual.py`, `services/ledger.py` | This is the single most defensible thing you built. Everyone reports *gross recovered*. You report `gross − organic − cost` and you have a real untouched control cohort producing the organic denominator. You even blend cohort-rate and model-counterfactual and *store which method was used per ledger row*. Butter Payments, a funded company, charges revenue-share on **vendor-managed attribution** - you did attribution better than a vendor whose entire pricing depends on it. |
| **2** | **Uplift-based action choice, not probability-based** | `engines/decision.py` | You rank by `uplift × amount − cost − discount − friction − systemic penalty`, which is what lets `DO_NOTHING` win honestly. Almost every competitor ranks by `P(recovery)`, which structurally can never choose to leave the customer alone. This is a real ML-judgment differentiator. |
| **3** | **Friction priced in rupees against LTV** | `FRICTION_FLOOR_PAISE + FRICTION_LTV_RATE × ltv` | Making the system *more careful with better customers* is a genuinely good product instinct and I have not seen it elsewhere in this space. Your A/B result - +28.4pp recovery at **0.73 contacts/event** - is the right shape of claim, and it falls directly out of this. |
| **4** | **Calibration treated as a safety property, not a metric** | `docs/evaluation.md`, `ml/metrics.py` | The argument "the policy engine gates on `min_confidence` and `min_expected_value`, so a miscalibrated model doesn't mispredict, it *authorises spend the guardrails were written to prevent*" is the single best sentence in your repo. Isotonic calibration + per-bin calibration chart + Brier as headline. Judges on the AI-judgment axis will notice. |

Two more that are good-but-not-novel: the hash-chained audit log (several entrants have it; it is
table stakes for the bar) and the S-learner treatment-as-feature design (correct, elegant, but a
standard uplift technique).

### 1.2 The honest weaknesses

- **`reasoning: claude` is nearly decorative.** By your own design the LLM contributes an advisory
  hypothesis for ≤ `llm_max_events_per_scan` events and can never change an action. A judge on the
  AI-judgment axis may ask "so why is the LLM here at all?" - and today the strongest honest answer
  is "promise-to-pay extraction from voice transcripts." That is one real use. Everything else is
  narration. *This is a defensible position* (the brief literally warns against using AI where
  deterministic logic is better) but you must have the answer rehearsed, and you should give the
  LLM at least one job only an LLM can do (see §2).
- **Nothing in Revyn is India-specific.** Grep for `npci`, `mandate`, `autopay`, `rbi`, `nach`,
  `dlt`, `hinglish` in `backend/app`: zero hits. `UPI` appears only as a `PaymentMethod` enum value,
  a `route-upi-alpha` string and a `METHOD_FALLBACKS` entry. Your system would be identical if you
  renamed UPI to ACH. **For a Razorpay hackathon this is the biggest single miss** and it is also
  where the cheapest novelty lives.
- **Simulated demand, simulated supply.** Synthetic generator → simulator gateway → simulated
  outcome function → measured recovery. The loop is closed but it is closed on itself: the ledger
  numbers are ultimately a property of `app/data/outcome.py`. Judges will spot this. Mitigate by
  (a) running at least one path against real Razorpay **test-mode** APIs, and (b) saying out loud in
  the pitch "the numbers are synthetic; the *methodology* is what's transferable, and here is the
  code that computes it."
- **The API is unauthenticated and your README says so loudly.** The candour is genuinely good and
  will read well. But `POST /ops/seed` wiping the DB and `POST /approvals/{id}/approve` authorising
  a financial action being open is, on a track whose bar is "compliant escalation", an easy point to
  lose. A single API-key dependency on the mutating routers is ~30 lines and removes the objection
  entirely. Do this.
- **Surface area vs depth.** 45 endpoints, 13 pages, 8 agents, 4 loss classes. Impressive, but the
  brief's own advice is "solve one specific problem exceptionally well" and warns against "the
  world's most powerful AI financial platform." Do not demo all 13 pages. Demo three.

---

## 2. Where the real, unclaimed novelty is

The gap in this entire track - and in the commercial market, not just the hackathon - is that
**every recovery system in the world is built on card-rail assumptions, and India does not run on
cards.** Research summary:

- UPI AutoPay mandate failure rates run **8–15%**, versus **2–3%** for card mandates, because
  authorization is real-time against a bank account rather than against a credit line.
- Since **1 Aug 2025**, NPCI caps mandate execution at **one initial attempt plus three retries**
  per mandate sequence number - **four attempts total, and that is a hard regulatory ceiling, not a
  tuning parameter.** Spend one on a bad retry and it is gone forever.
- NPCI also enforces **execution windows**: recurring debits are pushed out of the 10:00–13:00 peak
  and into before 10:00, 13:00–17:00, or after 21:30. A mandate presented at 10:30 now takes a
  *technical* decline that has nothing to do with the customer's balance.
- The RBI e-mandate framework requires a **pre-debit notification at least 24h before every debit**.
  If the PDN was not delivered, the debit is blocked *even though the mandate is valid*. Under
  Decentro's UPI AutoPay flow the PDN must land 24–48h ahead, and **if the first presentation fails
  the mandate is auto-revoked.**
- AFA-free ceiling is **₹15,000** (₹1L for SIP/insurance/credit-card). Above it, every single
  renewal needs fresh customer authentication.
- Consequently there are **four structurally distinct mandate failure modes** - no mandate,
  mandate revoked by customer, charge exceeds mandate cap, pre-debit notification failure - and
  **not one of them is fixable by retrying.** The bank returns the same answer at 2am, at noon, and
  three days later. Each requires a *different* customer action, and sending a generic "update your
  payment method" email to all four routes the customer to the wrong action and collapses recovery.

That last sentence is a product thesis nobody in this track is building on.

### 2.1 The recommendation - **make Revyn a mandate-aware, compliance-constrained recovery agent**

Reframe the pitch from "AI recovers revenue" (crowded) to:

> **In India the retry budget is a regulated, exhaustible resource. Revyn is the only recovery agent
> that treats it that way.**

Concretely, four additions. All four fit your existing architecture cleanly - they are new
guardrails, new causes and new actions in structures you already have.

**(a) Mandate lifecycle as a first-class object, with the four non-retryable failure modes.**
Add `RootCause` entries `MANDATE_ABSENT`, `MANDATE_REVOKED`, `MANDATE_CAP_EXCEEDED`,
`PDN_NOT_DELIVERED`, all in a new `CauseLayer.REGULATORY`. Add actions `REREGISTER_MANDATE` (AFA /
3DS / UPI-PIN re-auth link), `AMEND_MANDATE_CAP`, `RESEND_PDN`, `SWITCH_RAIL_TO_UPI_AUTOPAY`. Then
add the killer policy rule: **`RETRY_FUTILE` - for any regulatory-layer cause, `RETRY_PAYMENT` is
hard-blocked, not merely down-weighted.** Money quote for the pitch: *"a generic dunning system
burns all four NPCI attempts on a decline that is a compliance state, not a balance problem. Revyn
spends zero."*

**(b) A real mandate retry sequencer that is budget- and window-aware.** You already have a
scheduler and a journey machine, so this is mostly policy. Enforce:
- a hard **4-attempt** ledger per mandate sequence number, with the remaining budget shown in the UI;
- **NPCI execution windows** - never present a mandate in the 10:00–13:00 IST peak (you already have
  `IST_OFFSET_HOURS` in `engines/features.py` and a `QUIET_HOURS` rule to model it on);
- **PDN-first sequencing** - no presentation is schedulable unless a PDN was sent ≥24h earlier;
  make `SEND_PDN` an action the agent chooses, and treat the PDN as a *recovery touchpoint* (a
  balance-top-up nudge inside the 24h window) rather than a compliance chore;
- **salary-cycle-aware timing** for insufficient-funds, which is the one place timing genuinely moves
  the number.

This alone converts you from "another dunning agent" into the **mandate retry sequencer** the brief
explicitly asked for, and every constraint above is verifiable by a judge who works at Razorpay.

**(c) Give the LLM a job only an LLM can do: Hinglish, TRAI/DLT-compliant outreach.**
Right now `integrations/messaging.py` has four hardcoded English templates and six canned voice
replies. Replace with: LLM generates the recovery message in the customer's language register
(Hinglish / Tamil-English / formal B2B English), chosen from customer signals - **but** every
generated message is validated against a deterministic checker before send: approved DLT template
variables only, no invented amounts or dates (numbers must match the event record exactly), no
promises the merchant did not authorise, consent + opt-out honoured. Then extend your promise-to-pay
extractor to Hinglish transcripts ("paisa aa jayega Monday tak, thoda time do"), which your
`Verifier` already has the hook for. Now the answer to "why is the LLM here?" is *"language
generation and unstructured-speech comprehension - the two things deterministic code cannot do - and
even there the output is validated by deterministic code before it reaches a customer."* That is a
perfect answer on the AI-judgment axis.

**(d) One demo path against real Razorpay test-mode APIs.** Create a real test-mode subscription /
payment link, let the executor actually call it, show the real `pay_` / `plink_` id in the audit
chain. Keep the simulator for the batch. This kills "it's all fake" in fifteen seconds of video.

### 2.2 A second, smaller differentiator worth 30 seconds of pitch

**Sell your incrementality ledger as an adversarial claim.** Frame it as: *"a recovery vendor is
paid on what it claims to have recovered, so the vendor's own attribution is a conflict of interest.
Revyn ships the holdout, the organic estimate, the attribution method per row, and the cost - and
therefore reports a number that is 23% smaller than the one it could have reported."* Showing the
number you *didn't* claim is a much stronger trust signal than showing a big one. Put
`gross ₹3.15L → incremental ₹2.43L` on one slide with the delta highlighted.

---

## 3. Prioritised plan

Assuming limited time before submission.

**P0 - do these no matter what**
1. API key on all mutating routers (~30 lines). Removes the only "compliance" own-goal in the repo.
2. Re-cut README + pitch around **one** thesis: the regulated retry budget. Lead with it in the
   first 20 seconds of the video.
3. One real Razorpay test-mode call in the demo path.

**P1 - the novelty, in build order**
4. `CauseLayer.REGULATORY` + the four mandate failure causes + `RETRY_FUTILE` hard block.
5. Mandate attempt-budget ledger (4 max) + NPCI execution-window guard + PDN-24h precondition.
6. Teach the generator to emit mandate-failure events so the batch numbers include them, and add a
   `regulatory` row to the `/leakage` graph.

**P2 - if time remains**
7. LLM Hinglish message generation behind a deterministic validator; Hinglish promise extraction.
8. A `/simulator` scenario comparing "generic dunning" vs "mandate-aware" on the same book, reporting
   **NPCI attempts wasted** as a first-class metric alongside money. This is a chart no other
   entrant can produce.

**Do not do:** more pages, more endpoints, more agents, a chat interface.

---

## 4. Pitch structure (5:00)

| Time | Beat |
|---|---|
| 0:00–0:35 | UPI AutoPay fails 8–15% vs 2–3% for cards. NPCI allows **4 attempts, ever**. Four common failure modes are regulatory and **cannot be retried at all** - yet every dunning system retries them, burning the budget and auto-revoking the mandate. |
| 0:35–1:00 | Revyn: a recovery agent that treats the retry budget as a regulated, exhaustible resource. |
| 1:00–2:15 | Live: a mandate failure → diagnosed as `MANDATE_REVOKED` → `RETRY_FUTILE` hard-block, attempts spent **0** → re-registration link in Hinglish → recovered. Show the audit chain entry. |
| 2:15–3:15 | Batch results. Gross vs **incremental** - and say why the smaller number is the honest one. A/B: +28.4pp at 0.73 contacts/event. NPCI attempts wasted: baseline N, Revyn ~0. |
| 3:15–4:00 | AI judgment: architecture diagram, "the LLM never controls a financial API", the LLM's two real jobs (language, unstructured speech), both validated deterministically. Calibration-as-safety in one line. |
| 4:00–4:40 | Failure recovery: the injected gateway timeout where the payment had already succeeded - "gateway state ambiguous, verifying before any retry" - verified, booked, no double charge. Then your real dev failure (the hydration/SDK-detection bug) told as diagnose → fix → learn. |
| 4:40–5:00 | Limits, honestly: synthetic corpus, simulator by default, what you would build next. |

---

## 5. Bottom line

Revyn already clears the bar. Its real intellectual contribution is **honest incrementality
accounting and uplift-based (rather than probability-based) action selection** - keep those front
and centre, and frame the incrementality work as an integrity claim, not a metrics claim.

But the architecture you currently lead with is the consensus architecture of this track, and the
system is India-agnostic at a Razorpay hackathon. The unclaimed ground is the **regulated retry
budget**: NPCI's four-attempt ceiling, the execution windows, the 24h pre-debit notification, and
the four mandate failure modes that no retry can ever fix. Build that, and your project stops being
"a very well-engineered dunning agent" and starts being the only entry that understands the rail it
is running on.