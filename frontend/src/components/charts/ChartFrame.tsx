"use client";

import { useId, useState, type ReactNode } from "react";

export interface LegendItem {
  label: string;
  colour: string;
}

/**
 * Every chart ships with the numbers behind it: a table view satisfies screen readers and
 * the contrast relief rule for the lighter fills, and settles arguments about exact values.
 */
export function ChartFrame({
  title,
  hint,
  legend,
  height = 260,
  table,
  actions,
  children,
}: {
  title: string;
  hint?: string;
  legend?: LegendItem[];
  height?: number | "auto";
  table?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
}) {
  const [showTable, setShowTable] = useState(false);
  const id = useId();

  return (
    <figure className="hairline rounded-xl bg-surface p-4 sm:p-5">
      <figcaption className="mb-3 flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold tracking-tight text-ink">{title}</h3>
          {hint ? <p className="mt-0.5 text-xs leading-relaxed text-muted">{hint}</p> : null}
        </div>
        <div className="flex items-center gap-2">
          {actions}
          {table ? (
            <button
              type="button"
              onClick={() => setShowTable((open) => !open)}
              aria-expanded={showTable}
              aria-controls={id}
              className="hairline rounded-md bg-raised px-2 py-1 text-[11px] text-ink-2 hover:text-ink"
            >
              {showTable ? "Hide values" : "Values"}
            </button>
          ) : null}
        </div>
      </figcaption>

      {legend && legend.length > 1 ? (
        <ul className="mb-3 flex flex-wrap gap-x-4 gap-y-1.5">
          {legend.map((item) => (
            <li key={item.label} className="flex items-center gap-1.5 text-[11px] text-ink-2">
              <span
                aria-hidden
                className="inline-block h-2.5 w-2.5 rounded-[2px]"
                style={{ background: item.colour }}
              />
              {item.label}
            </li>
          ))}
        </ul>
      ) : null}

      <div style={height === "auto" ? undefined : { height }} className="w-full">
        {children}
      </div>

      {table && showTable ? (
        <div id={id} className="mt-4 border-t border-hairline pt-3">
          {table}
        </div>
      ) : null}
    </figure>
  );
}
