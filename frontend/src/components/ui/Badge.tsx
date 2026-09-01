import type { Tone } from "@/lib/labels";
import { titleCase } from "@/lib/format";

/* Status is never colour alone: every tone carries a glyph and a word. */
const TONE_STYLE: Record<Tone, string> = {
  neutral: "text-ink-2 bg-raised border-hairline",
  accent: "text-series-1 bg-series-1/12 border-series-1/35",
  good: "text-good bg-good/12 border-good/35",
  warning: "text-warning bg-warning/12 border-warning/35",
  serious: "text-serious bg-serious/12 border-serious/35",
  critical: "text-critical bg-critical/14 border-critical/40",
};

const TONE_GLYPH: Record<Tone, string> = {
  neutral: "○",
  accent: "◐",
  good: "✓",
  warning: "△",
  serious: "⚠",
  critical: "✕",
};

export function Badge({
  tone = "neutral",
  children,
  glyph = true,
  className = "",
}: {
  tone?: Tone;
  children: React.ReactNode;
  glyph?: boolean;
  className?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap ${TONE_STYLE[tone]} ${className}`}
    >
      {glyph ? <span aria-hidden>{TONE_GLYPH[tone]}</span> : null}
      {children}
    </span>
  );
}

export function StateBadge({ state, tone }: { state: string; tone: Tone }) {
  return <Badge tone={tone}>{titleCase(state)}</Badge>;
}

export function Delta({ value, format }: { value: number; format: (n: number) => string }) {
  if (value === 0) return <span className="text-muted">no change</span>;
  const up = value > 0;
  return (
    <span className={up ? "text-delta-up" : "text-critical"}>
      {up ? "↑" : "↓"} {format(Math.abs(value))}
    </span>
  );
}
