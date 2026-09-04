import type { ReactNode } from "react";

export function StatTile({ label, value, sub, accent, emphasis = false }: { label: string; value: ReactNode; sub?: ReactNode; accent?: string; emphasis?: boolean }) {
  return (
    <div className="panel panel-sheen lift group relative overflow-hidden rounded-tile p-4 sm:p-5">
      <span aria-hidden className="absolute inset-x-0 top-0 h-[2px] opacity-70" style={{ background: `linear-gradient(90deg, transparent, ${accent ?? "var(--series-1)"}, transparent)` }} />
      <p className="text-[10.5px] font-semibold uppercase tracking-[0.09em] text-muted">{label}</p>
      <p className={`num mt-2 font-bold tracking-tight leading-none ${emphasis ? "text-[28px] sm:text-[32px]" : "text-[22px] sm:text-[26px]"}`} style={accent ? { color: accent } : undefined}>
        {value}
      </p>
      {sub ? <p className="mt-2 text-[12px] leading-relaxed text-ink-2">{sub}</p> : null}
    </div>
  );
}

export function StatRow({ children }: { children: ReactNode }) {
  return <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4 sm:gap-4">{children}</div>;
}

export function KeyValue({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid gap-x-6 sm:grid-cols-2">
      {items.map(([key, value]) => (
        <div key={key} className="flex items-baseline justify-between gap-3 border-b border-hairline/60 py-2.5 text-[13px] last:border-0 sm:[&:nth-last-child(2)]:border-0">
          <dt className="text-muted">{key}</dt>
          <dd className="num text-right font-medium text-ink">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
