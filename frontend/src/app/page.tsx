"use client";
import Link from "next/link";
import { Activity, AlertTriangle, ArrowRight, BarChart3, Check, Coins, Globe, Layers, ScrollText, ShieldCheck, Sparkles, Timer, TrendingUp, Wallet, X, Zap } from "@/lib/icons";
import { MotionDiv, MotionFade } from "@/lib/motion";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-plane">
      <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5 sm:px-8">
          <div className="flex items-center gap-2.5">
            <span className="grid h-8 w-8 place-items-center rounded-xl bg-gradient-to-br from-blue-600 to-cyan-500 text-sm font-bold text-white shadow">R</span>
            <span className="text-[15px] font-bold tracking-tight text-slate-900">Revyn</span>
            <span className="hidden rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-bold tracking-widest text-blue-600 ring-1 ring-blue-200 sm:inline-flex">TRACK 03</span>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/dashboard" className="hidden rounded-full border border-slate-200 bg-white px-4 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 sm:inline-flex">Dashboard</Link>
            <Link href="/dashboard" className="inline-flex items-center gap-1.5 rounded-full bg-slate-900 px-5 py-2.5 text-xs font-bold text-white shadow hover:bg-slate-800">Launch app <ArrowRight size={14} /></Link>
          </div>
        </div>
      </header>

      <section className="relative overflow-hidden border-b border-slate-200/60 bg-gradient-to-b from-white via-blue-50/40 to-slate-50/80 px-6 py-14 sm:px-8 lg:py-20">
        <div className="absolute -top-28 -right-28 h-[560px] w-[560px] rounded-full bg-gradient-to-br from-blue-100 to-cyan-100 opacity-60 blur-3xl" />
        <div className="absolute -bottom-24 -left-24 h-[420px] w-[420px] rounded-full bg-gradient-to-br from-violet-100 to-blue-100 opacity-50 blur-3xl" />
        <div className="relative mx-auto max-w-6xl">
          <MotionFade>
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-white px-3 py-1.5 text-xs font-semibold tracking-wide text-blue-700 shadow-sm">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" /> RAZORPAY AI BUILDATHON · REVENUE RECOVERY
            </div>
          </MotionFade>
          <MotionDiv delay={80} className="mt-6 max-w-3xl">
            <h1 className="text-4xl font-extrabold leading-[0.96] tracking-tight text-slate-900 sm:text-5xl lg:text-[54px]">The retry budget is a <span className="bg-gradient-to-r from-blue-600 via-cyan-600 to-emerald-600 bg-clip-text text-transparent">regulated resource.</span></h1>
            <p className="mt-5 text-base leading-relaxed text-slate-600 sm:text-lg">UPI AutoPay fails <b className="text-slate-900">8–15%</b> vs 2–3% for cards. NPCI gives you <b className="text-slate-900">4 attempts, ever</b>. Four failure modes are <b className="text-slate-900">regulatory states</b>, not balance problems - retrying them is guaranteed to fail.</p>
            <p className="mt-3 inline-flex items-center gap-2 rounded-xl bg-white px-3 py-2 text-sm font-medium text-slate-700 shadow-sm ring-1 ring-slate-200"><Sparkles size={14} className="text-blue-600" /> Revyn spends <b>zero</b> attempts on them and routes each to its one correct action - in the customer&apos;s language.</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/dashboard" className="inline-flex items-center gap-2 rounded-full bg-blue-600 px-6 py-3 text-sm font-bold text-white shadow hover:bg-blue-700">Open Command Centre <ArrowRight size={16} /></Link>
              <Link href="/simulator" className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-700 shadow-sm hover:bg-slate-50"><FlaskIcon /> Test Futility Engine</Link>
              <Link href="/ledger" className="inline-flex items-center gap-2 rounded-full bg-white px-6 py-3 text-sm font-semibold text-slate-700 shadow-sm ring-1 ring-slate-200 hover:bg-slate-50"><Coins size={16} /> Ledger</Link>
            </div>
          </MotionDiv>
          <MotionDiv delay={160} className="mt-10 grid max-w-2xl grid-cols-3 gap-3">
            {[
              { k: "NPCI max", v: "4", s: "attempts / mandate", icon: Timer },
              { k: "Wasted", v: "0.4", s: "vs 3.1 generic", icon: AlertTriangle, good: true },
              { k: "Lift", v: "+28.4pp", s: "at 0.73 contacts", icon: TrendingUp },
            ].map((c) => (
              <div key={c.k} className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="flex items-center gap-1.5 text-[11px] font-bold tracking-widest text-slate-500"><c.icon size={12} /> {c.k}</div>
                <div className={`mt-1 text-2xl font-extrabold ${c.good ? "text-emerald-600" : "text-slate-900"}`}>{c.v}</div>
                <div className="text-xs text-slate-500">{c.s}</div>
              </div>
            ))}
          </MotionDiv>
        </div>
      </section>

      <section className="bg-white px-6 py-14 sm:px-8">
        <div className="mx-auto max-w-6xl grid gap-10 lg:grid-cols-2">
          <MotionDiv>
            <p className="text-xs font-bold tracking-widest text-blue-600">THE REAL PROBLEM</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight text-slate-900">Card-rail dunning is wrong for UPI.</h2>
            <p className="mt-4 text-sm leading-relaxed text-slate-600">Since 1 Aug 2025, NPCI caps mandate execution at <b>1 initial + 3 retries</b>. Execution is pushed out of 10:00–13:00 IST. RBI requires a <b>pre-debit notification ≥24h</b>. First failure can auto-revoke the mandate. AFA ceiling ₹15,000 - above it needs fresh auth.</p>
            <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
              <p className="text-xs font-bold text-slate-700">Four failure modes retry can never fix</p>
              <div className="mt-3 grid gap-2">
                {[
                  ["No mandate on file", "REREGISTER_MANDATE · AFA / UPI-PIN link"],
                  ["Mandate revoked", "REREGISTER_MANDATE + acknowledgement copy"],
                  ["Charge exceeds cap", "AMEND_MANDATE_CAP at new amount"],
                  ["PDN not delivered", "SEND_PDN → wait 24h → present"],
                ].map(([t, d]) => (
                  <div key={t} className="flex items-center justify-between rounded-xl bg-white px-3 py-2.5 text-sm shadow-sm ring-1 ring-slate-200/60">
                    <span className="font-semibold text-slate-900">{t}</span><span className="text-xs text-slate-500">{d}</span>
                  </div>
                ))}
              </div>
              <p className="mt-3 flex items-center gap-1.5 text-xs text-slate-500"><AlertTriangle size={12} /> Generic &quot;update payment method&quot; routes all four to the wrong place.</p>
            </div>
          </MotionDiv>
          <MotionDiv delay={100}>
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900"><BarChart3 size={16} className="text-slate-400" /> What happens without Revyn</h3>
              <div className="mt-4 space-y-3">
                <div className="flex gap-3 rounded-xl border border-red-200 bg-red-50 p-4">
                  <span className="grid h-8 w-8 place-items-center rounded-full bg-red-600 text-white"><X size={14} /></span>
                  <div><p className="text-sm font-bold text-slate-900">Generic: 3.1 wasted / mandate</p><p className="text-xs text-slate-600">Burns budget on revoked mandate → auto-revoked → customer lost forever.</p></div>
                </div>
                <div className="flex gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                  <span className="grid h-8 w-8 place-items-center rounded-full bg-emerald-600 text-white"><Check size={14} /></span>
                  <div><p className="text-sm font-bold text-slate-900">Revyn: 0.4 wasted, 0 revoked</p><p className="text-xs text-slate-600">REGULATORY → RETRY_FUTILE blocked → Hinglish re-register link.</p></div>
                </div>
                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div className="rounded-xl bg-slate-900 p-4 text-center text-white"><div className="text-sm font-bold">3.1 wasted</div><div className="text-xs opacity-60">Baseline</div></div>
                  <div className="rounded-xl bg-blue-600 p-4 text-center text-white"><div className="text-sm font-bold">0.4 wasted</div><div className="text-xs opacity-80">Revyn</div></div>
                </div>
              </div>
            </div>
          </MotionDiv>
        </div>
      </section>

      <section className="bg-slate-50 px-6 py-14 sm:px-8">
        <div className="mx-auto max-w-6xl">
          <p className="text-center text-xs font-bold tracking-widest text-blue-600">THREE PILLARS</p>
          <h2 className="mt-2 text-center text-3xl font-bold text-slate-900">Mandate-aware. Budget-aware. Language-aware.</h2>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {[
              { title: "Mandate Retry Sequencer", icon: Timer, desc: "Hard 4-attempt ledger, window guard (never 10–13 IST), PDN 24h gate, first-presentation protection, salary-cycle timing.", bullets: ["Attempts remaining in UI", "Defer, don't spend", "PDN as balance nudge"] },
              { title: "Futility Engine", icon: ShieldCheck, desc: "CauseLayer.REGULATORY · RETRY_FUTILE hard-blocks RETRY as BLOCK, not down-weight.", bullets: ["MANDATE_ABSENT → REREGISTER", "CAP_EXCEEDED → AMEND_CAP", "PDN_MISSING → SEND_PDN"] },
              { title: "Hinglish + Validator", icon: Globe, desc: "LLM in code-mixed register, deterministic validator gates every message before send.", bullets: ["DLT shape enforced", "Amount hallucination blocked", "Hinglish promise: kal, parso, salary"] },
            ].map((p, i) => (
              <MotionDiv key={p.title} delay={i * 80} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-blue-600 text-white"><p.icon size={18} /></div>
                <h3 className="mt-4 text-base font-bold text-slate-900">{p.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{p.desc}</p>
                <ul className="mt-4 space-y-1.5 text-xs text-slate-500">{p.bullets.map(b => <li key={b} className="flex gap-1.5"><span className="text-blue-400">•</span> {b}</li>)}</ul>
              </MotionDiv>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-white px-6 py-14 sm:px-8">
        <div className="mx-auto max-w-6xl grid gap-10 lg:grid-cols-2">
          <div>
            <p className="text-xs font-bold tracking-widest text-blue-600">WHY TRUST REVYN</p>
            <h2 className="mt-2 text-3xl font-bold text-slate-900">Incrementality as headline KPI.</h2>
            <p className="mt-4 text-sm leading-relaxed text-slate-600">Others report gross. Revyn reports <b>gross − organic − cost</b> with a real control holdout. Method per row: cohort / model / blended.</p>
            <div className="mt-6 rounded-2xl bg-slate-900 p-6 text-white shadow-lg">
              <p className="text-xs tracking-widest text-white/60">INCREMENTAL LEDGER</p>
              <p className="mt-2 text-lg">Gross <b>₹3.15L</b> <span className="text-white/50">→ Organic ₹0.59L → Cost ₹185</span></p>
              <p className="text-2xl font-extrabold text-emerald-400">= Net ₹2.43L</p>
              <p className="mt-2 text-xs text-white/50">23% smaller than the claimable number - that&apos;s why it&apos;s honest.</p>
            </div>
          </div>
          <div className="space-y-4">
            {[
              ["Uplift-based decision", "uplift × amount − cost − discount − friction − penalty · DO_NOTHING can win · +28.4pp at 0.73 contacts"],
              ["Friction priced in rupees", "FRICTION_FLOOR + RATE × ltv · more careful with better customers"],
              ["Calibration as safety", "Isotonic + Brier · gate on min_confidence · miscalibration = unauthorised spend"],
            ].map(([h, d]) => (
              <div key={h} className="rounded-2xl border border-slate-200 bg-slate-50/60 p-5">
                <h4 className="flex items-center gap-2 text-sm font-bold text-slate-900"><Layers size={14} className="text-slate-400" /> {h}</h4>
                <p className="mt-1 text-sm text-slate-600">{d}</p>
              </div>
            ))}
            <div className="rounded-2xl border border-blue-200 bg-blue-50 p-5">
              <h4 className="flex items-center gap-2 text-sm font-bold text-blue-900"><Zap size={14} /> The LLM&apos;s two real jobs</h4>
              <p className="mt-1 text-sm text-blue-800">&quot;Never controls a financial API. Generates Hinglish and understands unstructured speech - both validated deterministically.&quot;</p>
            </div>
          </div>
        </div>
      </section>

      <section className="bg-slate-900 px-6 py-14 text-white sm:px-8">
        <div className="mx-auto max-w-6xl">
          <h2 className="flex items-center gap-2 text-2xl font-bold"><BarChart3 size={20} className="text-blue-400" /> The chart no other entrant can produce</h2>
          <p className="mt-2 text-sm text-white/60">/simulator - generic dunning vs mandate-aware on same book, with NPCI wasted as first-class metric.</p>
          <div className="mt-8 grid gap-6 md:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur"><p className="text-xs tracking-widest text-white/50">WASTED / MANDATE</p><p className="mt-2 text-3xl font-extrabold"><span className="text-red-400">3.1</span> <span className="text-white/30">→</span> <span className="text-emerald-400">0.4</span></p><p className="text-xs text-white/50">Generic vs Revyn</p></div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur"><p className="text-xs tracking-widest text-white/50">REVOKED</p><p className="mt-2 text-3xl font-extrabold"><span className="text-red-400">8</span> <span className="text-white/30">→</span> <span className="text-emerald-400">0</span></p><p className="text-xs text-white/50">Prevented by RETRY_FUTILE</p></div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur"><p className="text-xs tracking-widest text-white/50">COST / RECOVERY</p><p className="mt-2 text-3xl font-extrabold">₹3.76</p><p className="text-xs text-white/50">Incremental basis</p></div>
          </div>
        </div>
      </section>

      <section className="bg-slate-50 px-6 py-14 sm:px-8">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-2xl font-bold text-slate-900">Architecture at a glance</h2>
          <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-6 font-mono text-xs leading-relaxed text-slate-700 shadow-sm">OBSERVE → DETECT → DIAGNOSE (<span className="font-bold text-blue-600">REGULATORY</span>) → PREDICT → DECIDE (uplift) → GATE (<span className="font-bold text-red-600">RETRY_FUTILE</span> / NPCI budget / window / PDN) → ACT → VERIFY → LEARN</div>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              ["8 agents", "sentinel investigator strategist optimizer policy_officer executor verifier learner"],
              ["Hash-chained audit", "Every transition verifiable via /audit/verify"],
              ["Policy as data", "Versioned, editable at /policies, simulatable"],
              ["Human approval", "High-value & voice require sign-off"],
            ].map(([t, d]) => (
              <div key={t} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"><div className="text-sm font-bold text-slate-900">{t}</div><div className="mt-1 text-xs text-slate-500">{d}</div></div>
            ))}
          </div>
        </div>
      </section>

      <section className="bg-white px-6 py-14 sm:px-8">
        <div className="mx-auto max-w-6xl">
          <h2 className="text-2xl font-bold text-slate-900">Docs & selling points</h2>
          <div className="mt-6 grid gap-6 md:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 p-6"><h3 className="flex items-center gap-2 font-bold text-slate-900"><Wallet size={16} className="text-slate-400" /> Real problem solved</h3><p className="mt-2 text-sm text-slate-600">Revenue dies from <b>exhausted retries</b> and <b>wrong remediation</b>, not unwilling customers. Revyn stops the burn and routes each state to its one correct action.</p></div>
            <div className="rounded-2xl border border-slate-200 p-6"><h3 className="flex items-center gap-2 font-bold text-slate-900"><Activity size={16} className="text-slate-400" /> Why it wins Track 03</h3><ul className="mt-2 list-disc pl-5 text-sm text-slate-600 space-y-1"><li>Problem taste: India-specific, regulatory, verifiable</li><li>Build quality: idempotency, audit chain, 79 tests</li><li>AI judgment: LLM has exactly two jobs</li><li>Failure recovery: verify before retry</li></ul></div>
          </div>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link href="/dashboard" className="inline-flex items-center gap-2 rounded-full bg-slate-900 px-6 py-3 text-sm font-bold text-white hover:bg-slate-800">Launch Dashboard <ArrowRight size={16} /></Link>
            <Link href="/decisions" className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"><Layers size={16} /> Decisions</Link>
            <Link href="/audit" className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-slate-50"><ScrollText size={16} /> Audit</Link>
          </div>
          <p className="mt-6 text-xs text-slate-400">Security: mutating routes require <code className="rounded bg-slate-100 px-1">X-API-Key</code> (REVYN_API_KEY). Reads open for demo. Set <code className="rounded bg-slate-100 px-1">NEXT_PUBLIC_API_KEY</code> in frontend.</p>
        </div>
      </section>

      <footer className="border-t border-slate-200 bg-slate-50 px-6 py-8 text-center text-xs text-slate-500 sm:px-8">&copy; 2026 Revyn - The retry budget is a regulated resource. <span className="ml-2 inline-flex rounded-full bg-slate-900 px-3 py-1 text-[11px] font-bold tracking-widest text-white">LIVE · COMPLIANT · INCREMENTAL</span></footer>
    </div>
  );
}

function FlaskIcon() {
  return <svg width={16} height={16} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.75}><path d="M10 2h4v6l4 6c1 1.5 0 3.5-2 3.5H8c-2 0-3-2-2-3.5l4-6z" /></svg>;
}
