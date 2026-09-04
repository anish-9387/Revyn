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
  const page = Math.floor(offset / limit) + 1;
  const pages = Math.ceil(total / limit);
  return (
    <nav
      aria-label="Pagination"
      className="mt-4 flex flex-col-reverse items-stretch gap-3 border-t border-hairline pt-3 text-xs text-muted sm:flex-row sm:items-center sm:justify-between"
    >
      <p className="num text-center sm:text-left">
        {compact(from)}–{compact(to)} of {compact(total)}
        <span className="hidden sm:inline"> · page {page} of {pages}</span>
      </p>
      <div className="flex gap-2 [&>*]:flex-1 sm:[&>*]:flex-none">
        <Button size="sm" disabled={offset === 0} onClick={() => onChange(Math.max(offset - limit, 0))}>
          ← Previous
        </Button>
        <Button size="sm" disabled={to >= total} onClick={() => onChange(offset + limit)}>
          Next →
        </Button>
      </div>
    </nav>
  );
}
