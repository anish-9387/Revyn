"use client";

import Link from "next/link";

export default function LandingPage() {
  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-[#0f1f3a] via-[#123060] to-[#0d4a3e] px-6 py-16 text-white sm:px-10 lg:px-14 lg:py-20">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,rgba(59,130,246,0.25),transparent_50%),radial-gradient(circle_at_80%_80%,rgba(16,185,129,0.2),transparent_50%)]" />
        <div className="relative mx-auto max-w-6xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1.5 text-xs font-semibold tracking-widest backdrop-blur">
            <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" /> TRACK 03 - AI REVENUE RECOVERY · RAZORPAY BUILDATHON
          </div>
          <h1 className="max-w-3xl text-4xl font-extrabold leading-[0.95] tracking-tight sm:text-5xl lg:text-[56px]">
            The retry budget is a <span className="bg-gradient-to-r from-emerald-300 to-sky-300 bg-clip-text text-transparent">regulated resource.</span>
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-relaxed text-white/80">
            In India, UPI AutoPay fails <span className="font-semibold text-white">8–15%</span> of the time - 5× card mandates. NPCI gives you <span className="font-semibold text-white">4 attempts, ever.</span> Four common failure modes cannot be retried at all. Every generic dunning system retries them anyway, burns the budget, and the mandate is revoked.
          </p>
          <p className="mt-3 max-w-2xl text-sm font-medium text-emerald-200">Revyn is the only recovery agent that knows the difference between a payment that failed and a payment that is forbidden to retry.</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/" className="rounded-full bg-white px-6 py-3 text-sm font-bold text-[#0f1f3a] shadow-lg hover:bg-white/90 transition">Open Command Centre →</Link>
            <Link href="/dashboard" className="rounded-full bg-white px-6 py-3 text-sm font-bold text-[#0f1f3a] shadow-lg hover:bg-white/90 transition">Open Command Centre →</Link>
            <Link href="/simulator" className="rounded-full border border-white/20 bg-white/10 px-6 py-3 text-sm font-semibold text-white backdrop-blur hover:bg-white/15 transition">Test the Futility Engine</Link>
            <Link href="/ledger" className="rounded-full border border-white/20 px-6 py-3 text-sm font-semibold text-white hover:bg-white/10 transition">View Incremental Ledger</Link>
          </div>
          <div className="mt-10 grid grid-cols-3 gap-4 max-w-2xl text-center">
            <div className="rounded-2xl bg-white/10 p-4 backdrop-blur">
              <div className="text-2xl font-extrabold">4</div>
              <div className="text-[11px] tracking-widest text-white/60">NPCI ATTEMPTS MAX</div>
            </div>
            <div className="rounded-2xl bg-white/10 p-4 backdrop-blur">
              <div className="text-2xl font-extrabold">0</div>
              <div className="text-[11px] tracking-widest text-white/60">WASTED ON REGULATORY</div>
            </div>
            <div className="rounded-2xl bg-white/10 p-4 backdrop-blur">
              <div className="text-2xl font-extrabold">+28.4pp</div>
              <div className="text-[11px] tracking-widest text-white/60">RECOVERY LIFT</div>
            </div>
          </div>
        </div>
      </section>

      {/* Problem */}
      <section className="bg-white px-6 py-14 sm:px-10 lg:px-14">
        <div className="mx-auto max-w-6xl">
          <div className="grid gap-10 lg:grid-cols-2">
            <div>
              <p className="text-xs font-bold tracking-widest text-blue-600">THE PROBLEM</p>
              <h2 className="mt-2 text-3xl font-bold tracking-tight text-zinc-900">Card-rail logic is structurally wrong on UPI.</h2>
              <p className="mt-4 text-sm leading-relaxed text-zinc-600">Every recovery system in the world assumes a retry is free. In India it is not. Since 1 Aug 2025, NPCI caps mandate execution at <b>1 initial + 3 retries = 4 attempts total</b> per sequence number. Execution is pushed out of the 10:00–13:00 IST peak. RBI requires a <b>pre-debit notification ≥24h before every debit</b>. If the first presentation fails, the mandate can be auto-revoked. The AFA-free ceiling is ₹15,000.</p>
              <div className="mt-6 rounded-xl border border-zinc-200 bg-zinc-50 p-4">
                <p className="text-xs font-semibold text-zinc-700">Four failure modes that retry can never fix:</p>
                <ul className="mt-2 space-y-1.5 text-sm text-zinc-600">
                  <li>→ <b>No mandate on file</b> - needs re-registration</li>
                  <li>→ <b>Mandate revoked</b> - needs re-registration with acknowledgement</li>
                  <li>→ <b>Charge exceeds cap</b> - needs cap amendment</li>
                  <li>→ <b>PDN not delivered</b> - needs RESEND_PDN, then wait 24h</li>
                </ul>
                <p className="mt-3 text-xs text-zinc-500">Sending &quot;update your payment method&quot; to all four routes the customer to the wrong action.</p>
              </div>
            </div>
            <div className="rounded-2xl border border-zinc-200 bg-zinc-50 p-6">
              <h3 className="text-sm font-bold text-zinc-900">What happens without Revyn</h3>
              <div className="mt-4 space-y-3">
                <div className="flex gap-3 rounded-xl bg-white p-4 shadow-sm border border-zinc-100">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-red-100 text-sm">✕</span>
                  <div>
                    <p className="text-sm font-semibold text-zinc-900">Generic dunning: 3.1 wasted attempts / mandate</p>
                    <p className="text-xs text-zinc-500">Burns all four attempts on a revoked mandate. Mandate auto-revoked. Customer lost forever.</p>
                  </div>
                </div>
                <div className="flex gap-3 rounded-xl bg-white p-4 shadow-sm border border-emerald-100">
                  <span className="flex h-8 w-8 items-center justify-center rounded-full bg-emerald-100 text-sm">✓</span>
                  <div>
                    <p className="text-sm font-semibold text-zinc-900">Revyn: 0.4 wasted, 0 revoked</p>
                    <p className="text-xs text-zinc-500">Diagnoses REGULATORY, blocks RETRY_FUTILE, sends re-registration link in Hinglish.</p>
                  </div>
                </div>
                <div className="mt-4 grid grid-cols-2 gap-3 text-center">
                  <div className="rounded-xl bg-red-50 p-3"><div className="text-lg font-bold text-red-600">₹ lost</div><div className="text-[11px] text-zinc-500">Baseline</div></div>
                  <div className="rounded-xl bg-emerald-50 p-3"><div className="text-lg font-bold text-emerald-600">₹Y recovered</div><div className="text-[11px] text-zinc-500">Revyn incremental</div></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Three Pillars */}
      <section className="bg-zinc-50 px-6 py-14 sm:px-10 lg:px-14">
        <div className="mx-auto max-w-6xl">
          <p className="text-center text-xs font-bold tracking-widest text-blue-600">THREE PILLARS</p>
          <h2 className="mt-2 text-center text-3xl font-bold tracking-tight text-zinc-900">Mandate-aware. Budget-aware. Language-aware.</h2>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {[
              { title: "Mandate Retry Sequencer", icon: "◈", desc: "Hard 4-attempt ledger per sequence, execution-window guard (never 10:00–13:00 IST), PDN 24h precondition, first-presentation protection, salary-cycle timing.", bullets: ["Attempts remaining surfaced in UI", "Defer, don't spend", "PDN as recovery touchpoint"] },
              { title: "Futility Engine", icon: "⬢", desc: "New CauseLayer.REGULATORY with 6 causes. RETRY_FUTILE hard-blocks RETRY_PAYMENT with PolicyVerdict.BLOCK - not down-weighted, blocked.", bullets: ["MANDATE_ABSENT → REREGISTER_MANDATE", "CAP_EXCEEDED → AMEND_MANDATE_CAP", "PDN_MISSING → SEND_PDN (24h wait)"] },
              { title: "Hinglish + Validator", icon: "✦", desc: "LLM generates code-mixed outreach, deterministic validator gates every message before send. Amount hallucination impossible.", bullets: ["DLT template shape enforced", "Opt-out & quiet hours honoured", "Hinglish promise extraction: 'paisa Monday tak aa jayega'"] },
            ].map((p) => (
              <div key={p.title} className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm">
                <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-600 text-white">{p.icon}</div>
                <h3 className="mt-4 text-base font-bold text-zinc-900">{p.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-zinc-600">{p.desc}</p>
                <ul className="mt-4 space-y-1.5 text-xs text-zinc-500">{p.bullets.map((b)=> <li key={b}>• {b}</li>)}</ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Why trust */}
      <section className="bg-white px-6 py-14 sm:px-10 lg:px-14">
        <div className="mx-auto max-w-6xl grid gap-10 lg:grid-cols-2">
          <div>
            <p className="text-xs font-bold tracking-widest text-blue-600">WHY TRUST REVYN</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight text-zinc-900">Incrementality as the headline KPI.</h2>
            <p className="mt-4 text-sm leading-relaxed text-zinc-600">Everyone reports <i>gross recovered</i>. Revyn reports <b>gross − organic − cost</b> and has a real untouched control holdout producing the organic denominator. Method stored per ledger row: cohort-rate vs model-counterfactual vs blended.</p>
            <div className="mt-6 rounded-xl bg-zinc-900 p-5 text-white">
              <p className="text-xs tracking-widest text-white/60">INCREMENTAL LEDGER</p>
              <p className="mt-2 text-lg">Gross <span className="font-bold">₹3.15L</span> → Organic <span className="text-white/60">₹0.59L</span> → Cost <span className="text-white/60">₹185</span></p>
              <p className="text-2xl font-extrabold text-emerald-400">= Incremental net ₹2.43L</p>
              <p className="mt-2 text-xs text-white/50">A vendor paid on what it claims to have recovered has a conflict of interest. Revyn ships the number that is 23% smaller than it could have claimed - and that&apos;s why it&apos;s honest.</p>
            </div>
          </div>
          <div className="space-y-4">
            <div className="rounded-2xl border border-zinc-200 p-6">
              <h4 className="text-sm font-bold text-zinc-900">Uplift-based decision, not probability-based</h4>
              <p className="mt-1 text-sm text-zinc-600">Ranked by <code className="rounded bg-zinc-100 px-1 py-0.5 text-xs">uplift × amount − cost − discount − friction − penalty</code>. Lets DO_NOTHING win honestly. +28.4pp lift at 0.73 contacts/event.</p>
            </div>
            <div className="rounded-2xl border border-zinc-200 p-6">
              <h4 className="text-sm font-bold text-zinc-900">Friction priced in rupees against LTV</h4>
              <p className="mt-1 text-sm text-zinc-600">FRICTION_FLOOR + FRICTION_LTV_RATE × ltv. More careful with better customers - product instinct competitors don&apos;t have.</p>
            </div>
            <div className="rounded-2xl border border-zinc-200 p-6">
              <h4 className="text-sm font-bold text-zinc-900">Calibration as safety, not a metric</h4>
              <p className="mt-1 text-sm text-zinc-600">Isotonic calibration, Brier as headline. Policy gates on min_confidence &amp; min_expected_value - miscalibrated model authorises spend the guardrails exist to prevent.</p>
            </div>
            <div className="rounded-2xl border border-blue-200 bg-blue-50 p-6">
              <h4 className="text-sm font-bold text-blue-900">The LLM&apos;s two real jobs</h4>
              <p className="mt-1 text-sm text-blue-800">&quot;The LLM never controls a financial API. It generates natural language in code-mixed registers and understands unstructured speech. Both are validated by deterministic code before reaching a customer.&quot;</p>
            </div>
          </div>
        </div>
      </section>

      {/* Metrics / NPCI chart mock */}
      <section className="bg-zinc-900 px-6 py-14 text-white sm:px-10 lg:px-14">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-2xl font-bold">The chart no other entrant can produce</h2>
          <p className="mt-2 text-sm text-white/60">/simulator compares generic dunning vs mandate-aware on the same book - with NPCI attempts wasted as a first-class metric.</p>
          <div className="mt-8 grid gap-6 md:grid-cols-3">
            <div className="rounded-2xl bg-white/5 p-6 border border-white/10">
              <p className="text-xs tracking-widest text-white/50">ATTEMPTS WASTED / MANDATE</p>
              <p className="mt-2 text-3xl font-extrabold"><span className="text-red-400">3.1</span> → <span className="text-emerald-400">0.4</span></p>
              <p className="mt-1 text-xs text-white/50">Generic vs Revyn</p>
            </div>
            <div className="rounded-2xl bg-white/5 p-6 border border-white/10">
              <p className="text-xs tracking-widest text-white/50">MANDATES AUTO-REVOKED</p>
              <p className="mt-2 text-3xl font-extrabold"><span className="text-red-400">8</span> → <span className="text-emerald-400">0</span></p>
              <p className="mt-1 text-xs text-white/50">Prevented by RETRY_FUTILE</p>
            </div>
            <div className="rounded-2xl bg-white/5 p-6 border border-white/10">
              <p className="text-xs tracking-widest text-white/50">COST PER RECOVERY</p>
              <p className="mt-2 text-3xl font-extrabold">₹3.76</p>
              <p className="mt-1 text-xs text-white/50">Incremental net basis</p>
            </div>
          </div>
        </div>
      </section>

      {/* Architecture */}
      <section className="bg-zinc-50 px-6 py-14 sm:px-10 lg:px-14">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-2xl font-bold tracking-tight text-zinc-900">Architecture at a glance</h2>
          <div className="mt-6 rounded-2xl border border-zinc-200 bg-white p-6 font-mono text-xs leading-relaxed text-zinc-700">
            OBSERVE → DETECT → DIAGNOSE (<span className="font-bold text-blue-600">REGULATORY layer</span>) → PREDICT → DECIDE (uplift) → GATE (<span className="font-bold text-red-600">RETRY_FUTILE</span> / NPCI budget / window / PDN) → ACT (mandate-aware) → VERIFY → LEARN
            <br /><br />
            <span className="text-zinc-500">Idempotency: primary-key guarantees exactly-once. Audit: hash-chained. Policy: versioned, simulatable. Gateway: simulator by default, real Razorpay test-mode on demand.</span>
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4 text-sm">
            <div className="rounded-xl border border-zinc-200 bg-white p-4"><b>8 agents</b><p className="text-xs text-zinc-500">sentinel investigator strategist optimizer policy_officer executor verifier learner</p></div>
            <div className="rounded-xl border border-zinc-200 bg-white p-4"><b>Hash-chained audit</b><p className="text-xs text-zinc-500">Every transition recomputable, /audit/verify</p></div>
            <div className="rounded-xl border border-zinc-200 bg-white p-4"><b>Policy as data</b><p className="text-xs text-zinc-500">All guardrails editable at /policies, versioned</p></div>
            <div className="rounded-xl border border-zinc-200 bg-white p-4"><b>Autonomous with human approval</b><p className="text-xs text-zinc-500">High-value &amp; voice require sign-off</p></div>
          </div>
        </div>
      </section>

      {/* CTA Docs */}
      <section className="bg-white px-6 py-14 sm:px-10 lg:px-14">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-2xl font-bold tracking-tight text-zinc-900">Docs & selling points</h2>
          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <div className="rounded-2xl border border-zinc-200 p-6">
              <h3 className="font-bold text-zinc-900">Real problem solved</h3>
              <p className="mt-2 text-sm text-zinc-600">Indian recurring revenue dies not from unwilling customers but from <b>exhausted regulatory retries</b> and <b>wrong remediation paths</b>. Revyn stops burning the budget and routes each regulatory state to its one correct action - in the customer&apos;s language - before the mandate is gone forever.</p>
            </div>
            <div className="rounded-2xl border border-zinc-200 p-6">
              <h3 className="font-bold text-zinc-900">Why it wins Track 03</h3>
              <ul className="mt-2 list-disc pl-5 text-sm text-zinc-600 space-y-1">
                <li><b>Problem taste:</b> India-specific, regulatory, verifiable against NPCI circulars</li>
                <li><b>Build quality:</b> Idempotency, audit chain, simulatable policy, 79 tests</li>
                <li><b>AI judgment:</b> LLM has exactly two jobs, both validated deterministically</li>
                <li><b>Failure recovery:</b> Ambiguous-gateway verification before any retry</li>
              </ul>
            </div>
          </div>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/" className="rounded-full bg-zinc-900 px-6 py-3 text-sm font-bold text-white hover:bg-zinc-800">Launch Dashboard →</Link>
            <Link href="/dashboard" className="rounded-full bg-zinc-900 px-6 py-3 text-sm font-bold text-white hover:bg-zinc-800">Launch Dashboard →</Link>
            <Link href="/decisions" className="rounded-full border border-zinc-200 bg-white px-6 py-3 text-sm font-semibold text-zinc-900 hover:bg-zinc-50">See Decision Evidence</Link>
            <Link href="/audit" className="rounded-full border border-zinc-200 bg-white px-6 py-3 text-sm font-semibold text-zinc-900 hover:bg-zinc-50">Audit Trail</Link>
          </div>
          <p className="mt-6 text-xs text-zinc-400">Security: mutating routes require X-API-Key (REVYN_API_KEY). Reads open for demo. Set NEXT_PUBLIC_API_KEY in frontend env to include the header automatically.</p>
        </div>
      </section>

      <footer className="border-t border-zinc-200 bg-zinc-50 px-6 py-8 text-center text-xs text-zinc-500 sm:px-10">
        © 2026 Revyn - The retry budget is a regulated resource. Built for Razorpay AI Buildathon Track 03. Synthetic data by default; real Razorpay test-mode on one-click path. <br />
        <span className="mt-2 inline-block rounded-full bg-zinc-900 px-3 py-1 text-[11px] font-semibold tracking-widest text-white">LIVE · COMPLIANT · INCREMENTAL</span>
      </footer>
    </div>
  );
}
