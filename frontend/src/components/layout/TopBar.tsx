"use client";

import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { inr, relativeTime } from "@/lib/format";
import type { Overview } from "@/lib/types";

export function TopBar({
  overview,
  automationEnabled,
  updatedAt,
  busy,
  onCycle,
  onKillSwitch,
}: {
  overview: Overview | null;
  automationEnabled: boolean;
  updatedAt: number | null;
  busy: string | null;
  onCycle: () => void;
  onKillSwitch: (enable: boolean) => void;
}) {
  const runtime = overview?.runtime;
  const scheduler = runtime?.scheduler;

  return (
    <header className="sticky top-0 z-20 flex flex-wrap items-center gap-x-4 gap-y-2 border-b border-hairline bg-plane/92 px-4 py-2.5 backdrop-blur">
      <div className="flex items-baseline gap-2">
        <span className="text-xs text-muted">At risk now</span>
        <span className="text-sm font-semibold tabular-nums text-ink">
          {overview ? inr(overview.revenue_at_risk_paise) : "—"}
        </span>
      </div>
      <div className="flex items-baseline gap-2">
        <span className="text-xs text-muted">Incremental net</span>
        <span className="text-sm font-semibold tabular-nums text-delta-up">
          {overview ? inr(overview.incremental_net_paise) : "—"}
        </span>
      </div>

      <div className="ml-auto flex flex-wrap items-center gap-2">
        {runtime ? (
          <>
            <Badge tone="neutral" glyph={false}>
              gateway: {runtime.gateway}
            </Badge>
            <Badge tone={runtime.llm_model ? "accent" : "neutral"} glyph={false}>
              reasoning: {runtime.reasoning_provider}
            </Badge>
            <Badge tone={runtime.model.trained ? "good" : "warning"}>
              {runtime.model.trained ? `model ${runtime.model.version ?? "ready"}` : "heuristic model"}
            </Badge>
            <Badge tone={scheduler?.running ? "good" : "warning"}>
              {scheduler?.running ? `loop live · ${scheduler.cycles} cycles` : "loop paused"}
            </Badge>
          </>
        ) : null}
        <span className="text-[11px] text-muted">
          {updatedAt ? `synced ${relativeTime(new Date(updatedAt).toISOString())}` : "syncing"}
        </span>
        <Button variant="ghost" size="sm" loading={busy === "cycle"} onClick={onCycle}>
          Run one cycle
        </Button>
        <Button
          variant={automationEnabled ? "danger" : "primary"}
          size="sm"
          loading={busy === "kill"}
          onClick={() => onKillSwitch(!automationEnabled)}
          title="Stops every automated action immediately"
        >
          {automationEnabled ? "Kill switch" : "Re-enable"}
        </Button>
        <ThemeToggle />
      </div>
    </header>
  );
}
