import type { Tone } from "@/lib/labels";
import { titleCase } from "@/lib/format";

const TONE_STYLE: Record<Tone, string> = {
  neutral: "text-ink-2 bg-raised border-hairline",
  accent: "text-series-1 bg-series-1/10 border-series-1/20",
  good: "text-good bg-good/10 border-good/20",
  warning: "text-warning bg-warning/10 border-warning/25",
  serious: "text-serious bg-serious/10 border-serious/20",
  critical: "text-critical bg-critical/10 border-critical/25",
};

const TONE_GLYPH: Record<Tone, string> = {
  neutral: "○",
  accent: "◐",
  good: "✓",
  warning: "△",
  serious: "⚠",
  critical: "✕",
};

export function Badge({ tone = "neutral", children, glyph = true, className = "" }: { tone?: Tone; children: React.ReactNode; glyph?: boolean; className?: string }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium whitespace-nowrap leading-none tracking-wide ${TONE_STYLE[tone]} ${className}`}>
      {glyph ? <span aria-hidden className="text-[10px] leading-none opacity-90">{TONE_GLYPH[tone]}</span> : null}
      {children}
    </span>
  );
}

export function StateBadge({ state, tone }: { state: string; tone: Tone }) {
  return <Badge tone={tone}>{titleCase(state)}</Badge>;
}

export function Delta({ value, format }: { value: number; format: (n: number) => string }) {
  if (value === 0) return <span className="text-muted text-xs">no change</span>;
  const up = value > 0;
  return <span className={`num inline-flex items-center gap-1 text-xs font-semibold ${up ? "text-delta-up" : "text-critical"}`}>{up ? "↑" : "↓"} {format(Math.abs(value))}</span>;
}
