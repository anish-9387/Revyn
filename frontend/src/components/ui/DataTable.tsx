import type { ReactNode } from "react";

export interface Column<T> {
  key: string;
  head: ReactNode;
  cell: (row: T) => ReactNode;
  align?: "left" | "right";
  width?: string;
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  empty = "No rows",
  onRowClick,
  dense = false,
}: {
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  empty?: string;
  onRowClick?: (row: T) => void;
  dense?: boolean;
}) {
  if (rows.length === 0) {
    return <p className="px-1 py-8 text-center text-xs text-muted">{empty}</p>;
  }
  const cellPad = dense ? "px-2.5 py-1.5" : "px-3 py-2.5";
  return (
    <div className="-mx-1 overflow-x-auto px-1">
      <table className="w-full border-collapse text-xs">
        <thead>
          <tr className="border-b border-hairline">
            {columns.map((column) => (
              <th
                key={column.key}
                scope="col"
                style={column.width ? { width: column.width } : undefined}
                className={`${cellPad} font-medium uppercase tracking-wider text-muted text-[10px] ${
                  column.align === "right" ? "text-right" : "text-left"
                }`}
              >
                {column.head}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={`border-b border-hairline/60 last:border-0 ${
                onRowClick ? "cursor-pointer hover:bg-raised" : ""
              }`}
            >
              {columns.map((column) => (
                <td
                  key={column.key}
                  className={`${cellPad} align-middle ${
                    column.align === "right" ? "text-right tabular-nums" : "text-left"
                  }`}
                >
                  {column.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
