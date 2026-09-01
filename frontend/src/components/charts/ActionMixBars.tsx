"use client";

import { ChartFrame } from "@/components/charts/ChartFrame";
import { compact } from "@/lib/format";
import { actionLabel } from "@/lib/labels";

export interface MixArm {
  label: string;
  colour: string;
  mix: Record<string, number>;
}

/**
 * Ranked magnitudes for one measure, so a single hue per arm is correct: colour separates the
 * arms being compared, never the rank of a bar.
 */
export function ActionMixBars({
  arms,
  title = "Action mix",
  hint,
}: {
  arms: MixArm[];
  title?: string;
  hint?: string;
}) {
  const actions = Array.from(new Set(arms.flatMap((arm) => Object.keys(arm.mix))));
  const total = (action: string) => arms.reduce((sum, arm) => sum + (arm.mix[action] ?? 0), 0);
  const ranked = actions.sort((left, right) => total(right) - total(left));
  const max = Math.max(1, ...ranked.flatMap((action) => arms.map((arm) => arm.mix[action] ?? 0)));

  return (
    <ChartFrame
      title={title}
      hint={hint}
      height="auto"
      legend={arms.length > 1 ? arms.map((arm) => ({ label: arm.label, colour: arm.colour })) : undefined}
    >
      <ul className="space-y-2.5">
        {ranked.map((action) => (
          <li key={action} className="grid grid-cols-[8.5rem_1fr] items-center gap-3">
            <span className="truncate text-xs text-ink-2" title={actionLabel(action)}>
              {actionLabel(action)}
            </span>
            <span className="space-y-[2px]">
              {arms.map((arm) => {
                const value = arm.mix[action] ?? 0;
                return (
                  <span key={arm.label} className="flex items-center gap-2">
                    <span className="h-2.5 flex-1 rounded-sm bg-grid">
                      <span
                        className="block h-full rounded-sm"
                        style={{ width: `${(value / max) * 100}%`, background: arm.colour }}
                      />
                    </span>
                    <span className="w-10 text-right text-[11px] tabular-nums text-ink">
                      {compact(value)}
                    </span>
                  </span>
                );
              })}
            </span>
          </li>
        ))}
      </ul>
    </ChartFrame>
  );
}
