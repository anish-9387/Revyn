import type { ReactNode } from "react";

export function StatTile({
  label,
  value,
  sub,
  accent,
  emphasis = false,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  accent?: string;
  emphasis?: boolean;
}) {
  return (
    <div className="hairline rounded-xl bg-surface p-4">
      <p className="text-[11px] font-medium uppercase tracking-wider text-muted">{label}</p>
      <p
        className={`mt-2 tabular-nums tracking-tight ${emphasis ? "text-3xl" : "text-2xl"} font-semibold`}
        style={accent ? { color: accent } : undefined}
      >
        {value}
      </p>
      {sub ? <p className="mt-1.5 text-xs leading-relaxed text-ink-2">{sub}</p> : null}
    </div>
  );
}

export function StatRow({ children }: { children: ReactNode }) {
  return <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{children}</div>;
}

export function KeyValue({ items }: { items: [string, ReactNode][] }) {
  return (
    <dl className="grid gap-x-6 gap-y-2 sm:grid-cols-2">
      {items.map(([key, value]) => (
        <div key={key} className="flex items-baseline justify-between gap-3 text-xs">
          <dt className="text-muted">{key}</dt>
          <dd className="text-right tabular-nums text-ink">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
