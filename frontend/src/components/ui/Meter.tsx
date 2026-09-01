import { pct } from "@/lib/format";

/** Budget bar: used against a hard limit, so the remainder must stay visible. */
export function Meter({
  label,
  used,
  limit,
  tone,
}: {
  label: string;
  used: number;
  limit: number;
  tone?: string;
}) {
  const ratio = limit > 0 ? Math.min(used / limit, 1) : 0;
  const colour = tone ?? (ratio >= 1 ? "var(--critical)" : ratio >= 0.67 ? "var(--warning)" : "var(--series-3)");
  return (
    <div>
      <div className="flex items-baseline justify-between text-xs">
        <span className="text-ink-2">{label}</span>
        <span className="tabular-nums text-ink">
          {used}
          <span className="text-muted"> / {limit}</span>
        </span>
      </div>
      <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-grid">
        <div
          className="h-full rounded-full transition-[width]"
          style={{ width: `${ratio * 100}%`, background: colour }}
        />
      </div>
    </div>
  );
}

/** Horizontal share bar used for ranked slices; label and value stay outside the fill. */
export function ShareBar({
  label,
  value,
  share,
  colour,
}: {
  label: string;
  value: string;
  share: number;
  colour: string;
}) {
  return (
    <div className="grid grid-cols-[minmax(6rem,10rem)_1fr_auto] items-center gap-3 text-xs">
      <span className="truncate text-ink-2" title={label}>
        {label}
      </span>
      <span className="h-2 rounded-sm bg-grid">
        <span
          className="block h-full rounded-sm"
          style={{ width: `${Math.max(share * 100, 1)}%`, background: colour }}
        />
      </span>
      <span className="tabular-nums text-ink">
        {value} <span className="text-muted">{pct(share)}</span>
      </span>
    </div>
  );
}
