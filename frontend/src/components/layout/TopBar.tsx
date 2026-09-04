"use client";

import { Button, IconButton } from "@/components/ui/Button";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { inr } from "@/lib/format";
import type { Overview } from "@/lib/types";

function Kpi({ label, short, value, tone }: { label: string; short: string; value: string; tone?: string }) {
  return (
    <div className="min-w-0">
      <p className="text-[10px] font-semibold tracking-[0.08em] whitespace-nowrap text-muted uppercase">
        <span className="sm:hidden">{short}</span>
        <span className="hidden sm:inline">{label}</span>
      </p>
      <p className={`num truncate text-[15px] leading-none font-semibold tracking-tight ${tone ?? "text-ink"}`}>{value}</p>
    </div>
  );
}

export function TopBar({
  overview,
  automationEnabled,
  busy,
  onCycle,
  onKillSwitch,
  onOpenNav,
}: {
  overview: Overview | null;
  automationEnabled: boolean;
  busy: string | null;
  onCycle: () => void;
  onKillSwitch: (enable: boolean) => void;
  onOpenNav: () => void;
}) {
  return (
    <header className="sticky top-0 z-30 border-b border-hairline bg-plane/75 backdrop-blur-xl supports-[backdrop-filter]:bg-plane/60">
      <div className="mx-auto flex max-w-[1560px] items-center gap-3 px-4 py-2.5 sm:gap-5 sm:px-5 lg:px-7">
        <IconButton label="Open navigation" onClick={onOpenNav} className="lg:hidden rounded-xl">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
            <path d="M2.8 5 H13.2 M2.8 8 H13.2 M2.8 11 H13.2" stroke="currentColor" strokeWidth="1.35" strokeLinecap="round" />
          </svg>
        </IconButton>
        <div className="flex min-w-0 items-center gap-4 sm:gap-7">
          <Kpi label="At risk now" short="At risk" value={overview ? inr(overview.revenue_at_risk_paise) : "—"} />
          <span aria-hidden className="hidden h-8 w-px bg-hairline sm:block" />
          <Kpi label="Incremental net" short="Net back" value={overview ? inr(overview.incremental_net_paise) : "—"} tone="text-delta-up" />
          <span className="hidden items-center gap-1.5 rounded-full bg-delta-up/10 px-2 py-1 text-[10px] font-semibold tracking-wide text-delta-up sm:inline-flex">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-delta-up" aria-hidden /> LIVE
          </span>
        </div>
        <div className="ml-auto flex shrink-0 items-center gap-2">
          <Button variant="ghost" size="sm" loading={busy === "cycle"} onClick={onCycle} className="hidden sm:inline-flex">
            Run cycle
          </Button>
          <Button variant="ghost" size="sm" loading={busy === "cycle"} onClick={onCycle} className="sm:hidden rounded-xl">
            Cycle
          </Button>
          <Button
            variant={automationEnabled ? "danger" : "primary"}
            size="sm"
            loading={busy === "kill"}
            onClick={() => onKillSwitch(!automationEnabled)}
            title={automationEnabled ? "Pause every automated action immediately" : "Resume automated recovery"}
            className="rounded-full"
          >
            <span className="hidden sm:inline">{automationEnabled ? "Pause automation" : "Resume"}</span>
            <span className="sm:hidden">{automationEnabled ? "Pause" : "Resume"}</span>
          </Button>
          <span aria-hidden className="h-6 w-px bg-hairline" />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
