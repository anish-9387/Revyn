"use client";

import type { KeyboardEvent, ReactNode } from "react";

export interface Column<T> {
  key: string;
  head: ReactNode;
  cell: (row: T) => ReactNode;
  align?: "left" | "right";
  width?: string;
}

const activate = (handler?: () => void) => (event: KeyboardEvent) => {
  if (!handler || (event.key !== "Enter" && event.key !== " ")) return;
  event.preventDefault();
  handler();
};

export function DataTable<T>({ columns, rows, rowKey, empty = "No rows", onRowClick, dense = false }: { columns: Column<T>[]; rows: T[]; rowKey: (row: T) => string; empty?: string; onRowClick?: (row: T) => void; dense?: boolean }) {
  if (rows.length === 0) return <p className="px-1 py-10 text-center text-xs text-muted">{empty}</p>;
  const pad = dense ? "px-3 py-2.5" : "px-3.5 py-3";
  const [lead, ...rest] = columns;
  return (
    <>
      <ul className="space-y-2.5 md:hidden">
        {rows.map((row) => (
          <li
            key={rowKey(row)}
            role={onRowClick ? "button" : undefined}
            tabIndex={onRowClick ? 0 : undefined}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
            onKeyDown={activate(onRowClick ? () => onRowClick(row) : undefined)}
            className={`rounded-2xl border border-hairline bg-raised/70 p-3.5 backdrop-blur-sm transition-all ${onRowClick ? "press cursor-pointer hover:border-hairline-strong hover:shadow-soft active:scale-[0.99]" : ""}`}
          >
            <div className="flex items-start justify-between gap-3">
              <p className="min-w-0 text-[13px] font-medium leading-tight text-ink">{lead.cell(row)}</p>
              {onRowClick ? <span aria-hidden className="grid h-7 w-7 place-items-center rounded-full border border-hairline bg-surface text-muted shrink-0">›</span> : null}
            </div>
            <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-2">
              {rest.map((column) => (
                <div key={column.key} className="min-w-0">
                  {column.head ? <dt className="truncate text-[10px] font-semibold uppercase tracking-[0.08em] text-muted">{column.head}</dt> : null}
                  <dd className="num mt-0.5 text-xs break-words font-medium text-ink-2">{column.cell(row)}</dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
      <div className="scroll-fade -mx-1 hidden overflow-x-auto px-1 md:block">
        <table className="w-full border-collapse text-[13px]">
          <thead>
            <tr className="border-b border-hairline">
              {columns.map((column) => (
                <th key={column.key} scope="col" style={column.width ? { width: column.width } : undefined} className={`${pad} text-[10px] font-semibold uppercase tracking-[0.08em] whitespace-nowrap text-muted ${column.align === "right" ? "text-right" : "text-left"}`}>
                  {column.head}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={rowKey(row)}
                tabIndex={onRowClick ? 0 : undefined}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                onKeyDown={activate(onRowClick ? () => onRowClick(row) : undefined)}
                className={`border-b border-hairline/50 transition-colors last:border-0 ${onRowClick ? "cursor-pointer hover:bg-raised" : "hover:bg-raised/40"}`}
              >
                {columns.map((column) => (
                  <td key={column.key} className={`${pad} align-middle ${column.align === "right" ? "num text-right" : "text-left"}`}>
                    {column.cell(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
