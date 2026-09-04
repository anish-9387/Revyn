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
        <span className="num text-ink">
          {used}
          <span className="text-muted"> / {limit}</span>
        </span>
      </div>
      <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-grid">
        <div
          className="h-full origin-left rounded-full animate-grow"
          style={{ width: `${ratio * 100}%`, background: colour }}
        />
      </div>
    </div>
  );
}

/**
 * Horizontal share bar for ranked slices. Below `sm` the label and amount take a row of their own
 * and the bar spans beneath them, because a fixed label column truncates written cause names.
 */
export function ShareBar({
  label,
  value,
  share,
  colour,
  showShare = true,
}: {
  label: string;
  value: string;
  share: number;
  colour: string;
  /** Off when `value` already *is* the share, so the same number is not printed twice. */
  showShare?: boolean;
}) {
  return (
    <div className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1.5 text-xs sm:grid-cols-[minmax(6rem,10rem)_1fr_auto]">
      <span className="min-w-0 truncate text-ink-2 sm:order-1" title={label}>
        {label}
      </span>
      <span className="num whitespace-nowrap text-ink sm:order-3">
        {value}
        {showShare ? <span className="text-muted"> {pct(share)}</span> : null}
      </span>
      <span className="col-span-2 h-2 overflow-hidden rounded-sm bg-grid sm:order-2 sm:col-span-1">
        <span
          className="block h-full origin-left rounded-sm animate-grow"
          style={{ width: `${Math.max(share * 100, 1)}%`, background: colour }}
        />
      </span>
    </div>
  );
}
