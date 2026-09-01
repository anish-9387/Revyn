import type { ReactNode } from "react";

export interface TooltipRow {
  label: string;
  value: ReactNode;
  colour?: string;
}

export function VizTooltip({ title, rows, note }: { title: string; rows: TooltipRow[]; note?: string }) {
  return (
    <div className="viz-tooltip">
      <p className="mb-1.5 font-medium text-ink">{title}</p>
      <ul className="space-y-1">
        {rows.map((row) => (
          <li key={row.label} className="flex items-center justify-between gap-4">
            <span className="flex items-center gap-1.5 text-ink-2">
              {row.colour ? (
                <span
                  aria-hidden
                  className="inline-block h-2 w-2 rounded-[2px]"
                  style={{ background: row.colour }}
                />
              ) : null}
              {row.label}
            </span>
            <span className="tabular-nums text-ink">{row.value}</span>
          </li>
        ))}
      </ul>
      {note ? <p className="mt-1.5 text-[11px] text-muted">{note}</p> : null}
    </div>
  );
}
