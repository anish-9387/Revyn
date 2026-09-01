"use client";

import { Button } from "@/components/ui/Button";
import { compact } from "@/lib/format";

export function Pager({
  total,
  limit,
  offset,
  onChange,
}: {
  total: number;
  limit: number;
  offset: number;
  onChange: (next: number) => void;
}) {
  if (total <= limit) return null;
  const from = offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <div className="mt-3 flex items-center justify-between gap-3 text-xs text-muted">
      <span className="tabular-nums">
        {compact(from)}–{compact(to)} of {compact(total)}
      </span>
      <span className="flex gap-2">
        <Button size="sm" disabled={offset === 0} onClick={() => onChange(Math.max(offset - limit, 0))}>
          Previous
        </Button>
        <Button size="sm" disabled={to >= total} onClick={() => onChange(offset + limit)}>
          Next
        </Button>
      </span>
    </div>
  );
}
