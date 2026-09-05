"use client";
import Image from "next/image";
import Link from "next/link";
import {
  AlertTriangle, ArrowRight, ArrowUpRight, BarChart3,
  Check, Globe, Layers, ScrollText, ShieldCheck, Sparkles,
  Timer, TrendingUp, X, Zap,
} from "@/lib/icons";
import { MotionDiv, MotionFade } from "@/lib/motion";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">

      {/* ── Nav ──────────────────────────────────────────────── */}
      <header className="sticky top-0 z-40 border-b border-black/8 bg-white/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3.5 sm:px-8">
          <div className="flex items-center gap-2.5">
            <div className="relative h-8 w-8 shrink-0">
              <Image src="/logo.png" alt="Revyn logo" fill className="object-contain rounded-lg" priority />
            </div>
            <span className="text-[15px] font-bold tracking-tight text-black">Revyn</span>
          </div>
          <nav className="hidden md:flex items-center gap-8 text-xs font-bold tracking-[0.12em] uppercase text-black/60">
            <a href="#problem" className="hover:text-black transition-colors">Problem</a>
            <a href="#how-it-works" className="hover:text-black transition-colors">How it works</a>
            <a href="#metrics" className="hover:text-black transition-colors">Metrics</a>
          </nav>
          <div className="flex items-center gap-2">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-1.5 rounded-full bg-black px-5 py-2.5 text-xs font-bold text-white hover:bg-slate-800 transition-colors"
            >
              Open app <ArrowRight size={13} />
            </Link>
          </div>
        </div>
      </header>

      {/* ── Hero ─────────────────────────────────────────────── */}
      <section className="relative overflow-hidden border-b border-black/8 bg-[#050a14] px-6 py-20 sm:px-8 lg:py-28">
        {/* ambient glows */}
        <div className="pointer-events-none absolute -top-40 -right-40 h-[600px] w-[600px] rounded-full bg-blue-600/20 blur-[120px]" />
        <div className="pointer-events-none absolute -bottom-32 -left-32 h-[500px] w-[500px] rounded-full bg-violet-700/15 blur-[120px]" />

        <div className="relative mx-auto max-w-6xl">
          <MotionFade>
            <p className="inline-flex items-center gap-2 text-[10px] font-bold tracking-[0.2em] uppercase text-blue-400 mb-6">
              <Sparkles size={12} /> AI Revenue Recovery · India-First
            </p>
          </MotionFade>
          <MotionDiv delay={60} className="max-w-4xl">
            <h1 className="text-5xl font-extrabold leading-[0.95] tracking-tight text-white sm:text-6xl lg:text-[68px]">
              The retry budget is a{" "}
              <span className="bg-gradient-to-r from-blue-400 via-cyan-400 to-emerald-400 bg-clip-text text-transparent">
                regulated resource.
              </span>
            </h1>
            <p className="mt-6 max-w-2xl text-base leading-relaxed text-white/60 sm:text-lg">
              UPI AutoPay fails <strong className="text-white">8–15%</strong> of the time.
              NPCI gives you <strong className="text-white">4 attempts, ever</strong>. Four of the most
              common failure modes are regulatory states - retrying them is guaranteed to fail.
              Revyn spends <strong className="text-white">zero attempts</strong> on them.
            </p>
          </MotionDiv>
          <MotionDiv delay={140} className="mt-10 flex flex-wrap gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-full bg-blue-600 px-7 py-3.5 text-sm font-bold text-white shadow-lg hover:bg-blue-500 transition-colors"
            >
              Open Command Centre <ArrowRight size={16} />
            </Link>
            <Link
              href="/simulator"
              className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/8 px-7 py-3.5 text-sm font-semibold text-white hover:bg-white/15 transition-colors backdrop-blur"
            >
              Run a simulation <ArrowUpRight size={14} />
            </Link>
          </MotionDiv>

          {/* Stats bar */}
          <MotionDiv delay={220} className="mt-14 grid max-w-2xl grid-cols-3 gap-3">
            {[
              { k: "NPCI limit", v: "4", s: "attempts per mandate", icon: Timer },
              { k: "Wasted (Revyn)", v: "0.4", s: "vs 3.1 generic", icon: TrendingUp, good: true },
              { k: "Recovery lift", v: "+28pp", s: "at 0.73 contacts", icon: BarChart3 },
            ].map((c) => (
              <div key={c.k} className="rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur">
                <div className="flex items-center gap-1.5 text-[10px] font-bold tracking-widest text-white/40 uppercase">
                  <c.icon size={11} /> {c.k}
                </div>
                <div className={`mt-1.5 text-2xl font-extrabold ${c.good ? "text-emerald-400" : "text-white"}`}>{c.v}</div>
                <div className="text-[11px] text-white/40">{c.s}</div>
              </div>
            ))}
          </MotionDiv>
        </div>
      </section>

      {/* ── Problem ──────────────────────────────────────────── */}
      <section id="problem" className="bg-white px-6 py-16 sm:px-8 lg:py-20">
        <div className="mx-auto max-w-6xl">
          <p className="text-[10px] font-bold tracking-[0.2em] uppercase text-blue-600">The Problem</p>
          <div className="mt-3 grid gap-12 lg:grid-cols-2 lg:mt-8">
            <div>
              <h2 className="text-3xl font-extrabold tracking-tight text-black sm:text-4xl">
                Card-rail dunning is the wrong tool for UPI.
              </h2>
              <p className="mt-4 text-sm leading-relaxed text-slate-600">
                Since August 2025, NPCI caps mandate execution at <strong className="text-black">1 initial + 3 retries</strong>.
                Execution windows are restricted. RBI requires a <strong className="text-black">pre-debit notification at least 24h</strong> in advance.
                A first failure can auto-revoke the mandate entirely. AFA ceiling is ₹15,000 - above it needs fresh authentication.
              </p>
              <div className="mt-6 rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <p className="text-xs font-bold text-slate-700 mb-3">Four failure modes retry can never fix</p>
                <div className="space-y-2">
                  {[
                    ["No mandate on file", "Re-register · AFA / UPI-PIN link"],
                    ["Mandate revoked", "Re-register + acknowledgement copy"],
                    ["Charge exceeds cap", "Amend mandate cap at new amount"],
                    ["PDN not delivered", "Send PDN → wait 24h → retry present"],
                  ].map(([t, d]) => (
                    <div key={t} className="flex items-center justify-between rounded-xl bg-white px-3 py-2.5 text-sm shadow-sm ring-1 ring-slate-200/60">
                      <span className="font-semibold text-slate-900">{t}</span>
                      <span className="text-xs text-slate-500 text-right ml-3">{d}</span>
                    </div>
                  ))}
                </div>
                <p className="mt-3 flex items-center gap-1.5 text-xs text-slate-500">
                  <AlertTriangle size={12} /> Generic "update payment method" routes all four to the same wrong place.
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <h3 className="flex items-center gap-2 text-sm font-bold text-slate-900"><BarChart3 size={16} className="text-slate-400" /> Without mandate-aware recovery</h3>
                <div className="mt-4 space-y-3">
                  <div className="flex gap-3 rounded-xl border border-red-200 bg-red-50 p-4">
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-red-600 text-white"><X size={14} /></span>
                    <div>
                      <p className="text-sm font-bold text-slate-900">3.1 wasted attempts per mandate</p>
                      <p className="text-xs text-slate-600 mt-0.5">Burns budget on revoked mandates → auto-revoke → customer lost permanently.</p>
                    </div>
                  </div>
                  <div className="flex gap-3 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                    <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-emerald-600 text-white"><Check size={14} /></span>
                    <div>
                      <p className="text-sm font-bold text-slate-900">Revyn: 0.4 wasted, zero revocations</p>
                      <p className="text-xs text-slate-600 mt-0.5">Regulatory states hard-blocked → correct remediation sent in customer's language.</p>
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-3 pt-1">
                    <div className="rounded-xl bg-slate-900 p-4 text-center text-white">
                      <div className="text-sm font-bold">3.1 wasted</div>
                      <div className="text-xs opacity-50 mt-0.5">Baseline</div>
                    </div>
                    <div className="rounded-xl bg-blue-600 p-4 text-center text-white">
                      <div className="text-sm font-bold">0.4 wasted</div>
                      <div className="text-xs opacity-80 mt-0.5">Revyn</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── How it works ─────────────────────────────────────── */}
      <section id="how-it-works" className="bg-slate-50 px-6 py-16 sm:px-8 border-y border-slate-200">
        <div className="mx-auto max-w-6xl">
          <p className="text-center text-[10px] font-bold tracking-[0.2em] uppercase text-blue-600">How It Works</p>
          <h2 className="mt-3 text-center text-3xl font-extrabold tracking-tight text-black sm:text-4xl">
            Mandate-aware. Budget-aware. Language-aware.
          </h2>
          <div className="mt-10 grid gap-6 md:grid-cols-3">
            {[
              {
                title: "Mandate Retry Sequencer",
                icon: Timer,
                desc: "Hard 4-attempt ledger, window guard (avoids restricted hours), PDN 24h gate, first-presentation protection, and salary-cycle timing.",
                bullets: ["Attempts remaining tracked in UI", "Defer decisions - don't spend budget", "PDN doubles as a balance nudge"],
              },
              {
                title: "Futility Engine",
                icon: ShieldCheck,
                desc: "Regulatory failure modes are classified and hard-blocked from retry - not just down-weighted. RETRY_FUTILE is a real gate.",
                bullets: ["Mandate absent → re-register flow", "Cap exceeded → amend cap action", "PDN missing → send PDN first"],
              },
              {
                title: "Hinglish Messenger",
                icon: Globe,
                desc: "LLM drafts messages in code-mixed Hinglish. A deterministic validator gates every message before it is sent - no hallucinated amounts reach customers.",
                bullets: ["DLT template shape enforced", "Amount & date hallucination blocked", "Natural Hinglish register (kal, salary)"],
              },
            ].map((p, i) => (
              <MotionDiv key={p.title} delay={i * 80} className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
                <div className="grid h-10 w-10 place-items-center rounded-xl bg-black text-white">
                  <p.icon size={18} />
                </div>
                <h3 className="mt-4 text-base font-bold text-slate-900">{p.title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600">{p.desc}</p>
                <ul className="mt-4 space-y-1.5 text-xs text-slate-500">
                  {p.bullets.map(b => (
                    <li key={b} className="flex gap-1.5">
                      <span className="text-blue-400 shrink-0">▸</span> {b}
                    </li>
                  ))}
                </ul>
              </MotionDiv>
            ))}
          </div>
        </div>
      </section>

      {/* ── Incrementality ───────────────────────────────────── */}
      <section className="bg-white px-6 py-16 sm:px-8 lg:py-20">
        <div className="mx-auto max-w-6xl grid gap-12 lg:grid-cols-2 items-center">
          <div>
            <p className="text-[10px] font-bold tracking-[0.2em] uppercase text-blue-600">Why Trust The Numbers</p>
            <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-black sm:text-4xl">
              Incremental revenue, not gross.
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-slate-600">
              Most recovery systems report gross recovered and self-attribute it all. Revyn reports{" "}
              <strong className="text-black">gross − organic − cost</strong>, backed by a real control holdout.
              The number is 23% smaller than the claimable figure - that's the point.
            </p>
            <div className="mt-6 rounded-2xl bg-black p-6 text-white shadow-lg">
              <p className="text-[10px] tracking-widest text-white/40 uppercase">Incremental Ledger</p>
              <p className="mt-3 text-lg">Gross <strong>₹3.15L</strong> <span className="text-white/40">→ Organic ₹0.59L → Cost ₹185</span></p>
              <p className="text-2xl font-extrabold text-emerald-400 mt-1">= Net ₹2.43L</p>
              <p className="mt-2 text-xs text-white/40">23% smaller than the claimable number - defensible by design.</p>
            </div>
          </div>
          <div className="space-y-4">
            {[
              ["Uplift-based decision engine", "Scores uplift × amount − cost − discount − friction − penalty. DO_NOTHING can win - and often should."],
              ["Friction priced in rupees", "More careful with high-LTV customers. Friction floor + rate × LTV, not a uniform policy."],
              ["Calibrated confidence gates", "Isotonic calibration + Brier score. Miscalibration = unauthorised spend - so it's blocked before action."],
            ].map(([h, d]) => (
              <div key={h as string} className="rounded-2xl border border-slate-200 bg-slate-50 p-5">
                <h4 className="flex items-center gap-2 text-sm font-bold text-slate-900">
                  <Layers size={14} className="text-slate-400 shrink-0" /> {h}
                </h4>
                <p className="mt-1.5 text-sm text-slate-600">{d}</p>
              </div>
            ))}
            <div className="rounded-2xl border border-blue-200 bg-blue-50 p-5">
              <h4 className="flex items-center gap-2 text-sm font-bold text-blue-900">
                <Zap size={14} className="shrink-0" /> The LLM has exactly two jobs
              </h4>
              <p className="mt-1.5 text-sm text-blue-800">
                Generate Hinglish messages and interpret unstructured speech. It never controls a financial API.
                Every output is validated deterministically before it reaches a customer.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Dark metrics section ──────────────────────────────── */}
      <section id="metrics" className="relative overflow-hidden bg-[#050a14] px-6 py-16 sm:px-8">
        <div className="pointer-events-none absolute top-0 right-0 h-[400px] w-[400px] rounded-full bg-blue-700/15 blur-[100px] translate-x-1/3 -translate-y-1/3" />
        <div className="mx-auto max-w-6xl relative">
          <p className="text-[10px] font-bold tracking-[0.2em] uppercase text-blue-400">Live Metrics</p>
          <h2 className="mt-3 text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            Numbers the dashboard surfaces in real time.
          </h2>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur">
              <p className="text-[10px] tracking-widest text-white/40 uppercase">Wasted / Mandate</p>
              <p className="mt-3 text-3xl font-extrabold">
                <span className="text-red-400">3.1</span>
                <span className="text-white/25 mx-2">→</span>
                <span className="text-emerald-400">0.4</span>
              </p>
              <p className="mt-1.5 text-xs text-white/40">Generic dunning vs Revyn</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur">
              <p className="text-[10px] tracking-widest text-white/40 uppercase">Mandate Revocations</p>
              <p className="mt-3 text-3xl font-extrabold">
                <span className="text-red-400">8</span>
                <span className="text-white/25 mx-2">→</span>
                <span className="text-emerald-400">0</span>
              </p>
              <p className="mt-1.5 text-xs text-white/40">Prevented by the Futility Engine</p>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-6 backdrop-blur">
              <p className="text-[10px] tracking-widest text-white/40 uppercase">Cost / Incremental Recovery</p>
              <p className="mt-3 text-3xl font-extrabold text-white">₹3.76</p>
              <p className="mt-1.5 text-xs text-white/40">Measured on an incremental basis</p>
            </div>
          </div>
        </div>
      </section>

      {/* ── Architecture ─────────────────────────────────────── */}
      <section className="bg-slate-50 px-6 py-16 sm:px-8 border-t border-slate-200">
        <div className="mx-auto max-w-6xl">
          <p className="text-[10px] font-bold tracking-[0.2em] uppercase text-blue-600">Architecture</p>
          <h2 className="mt-3 text-2xl font-extrabold tracking-tight text-black">Eight agents. One closed loop.</h2>
          <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 font-mono text-xs leading-relaxed text-slate-700 shadow-sm overflow-x-auto whitespace-nowrap">
            OBSERVE → DETECT → DIAGNOSE (<span className="font-bold text-blue-600">REGULATORY</span>) → PREDICT → DECIDE (uplift) → GATE (<span className="font-bold text-red-600">RETRY_FUTILE</span> / NPCI budget / window / PDN) → ACT → VERIFY → LEARN
          </div>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {[
              { t: "8 agents", d: "Sentinel, investigator, strategist, optimizer, policy officer, executor, verifier, learner." },
              { t: "Hash-chained audit", d: "Every transition verifiable through the Audit page - tamper-evident by construction." },
              { t: "Policy as data", d: "Versioned policies, editable in the Policies page, testable in the Simulator." },
              { t: "Human approval", d: "High-value and voice-initiated actions require sign-off before execution." },
            ].map(({ t, d }) => (
              <div key={t} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <div className="text-sm font-bold text-slate-900">{t}</div>
                <div className="mt-1.5 text-xs text-slate-500 leading-relaxed">{d}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── Final CTA ────────────────────────────────────────── */}
      <section className="relative overflow-hidden bg-[#050a14] px-6 py-20 sm:px-8 text-center">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-b from-blue-900/10 to-transparent" />
        <div className="relative mx-auto max-w-2xl">
          <h2 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
            See Revyn working on real data.
          </h2>
          <p className="mt-4 text-sm text-white/50">
            The Command Centre shows live recovery positions, agent decisions, and an incrementality ledger - no configuration needed to explore.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <Link
              href="/dashboard"
              className="inline-flex items-center gap-2 rounded-full bg-blue-600 px-8 py-4 text-sm font-bold text-white shadow-lg hover:bg-blue-500 transition-colors"
            >
              Open Command Centre <ArrowRight size={16} />
            </Link>
            <Link
              href="/audit"
              className="inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/8 px-8 py-4 text-sm font-semibold text-white hover:bg-white/15 transition-colors"
            >
              <ScrollText size={14} /> View audit trail
            </Link>
          </div>
        </div>
      </section>

      {/* ── Footer ───────────────────────────────────────────── */}
      <footer className="border-t border-slate-200 bg-white px-6 py-8 text-center sm:px-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center gap-2 sm:flex-row sm:justify-between">
          <div className="flex items-center gap-2">
            <div className="relative h-6 w-6 shrink-0">
              <Image src="/logo.png" alt="Revyn" fill className="object-contain rounded-md" />
            </div>
            <span className="text-xs font-semibold text-slate-700">Revyn</span>
          </div>
          <p className="text-xs text-slate-400">© 2026 Revyn · Revenue recovery, supervised.</p>
          <div className="flex items-center gap-4 text-xs text-slate-500">
            <Link href="/ledger" className="hover:text-slate-800 transition-colors">Ledger</Link>
            <Link href="/audit" className="hover:text-slate-800 transition-colors">Audit</Link>
            <Link href="/simulator" className="hover:text-slate-800 transition-colors">Simulator</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
