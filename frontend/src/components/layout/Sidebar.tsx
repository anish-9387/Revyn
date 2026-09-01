"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { NAV } from "@/lib/routes";

export function Sidebar({ approvals }: { approvals: number }) {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Sections"
      className="flex gap-1 overflow-x-auto border-b border-hairline px-3 py-2 lg:h-dvh lg:w-60 lg:shrink-0 lg:flex-col lg:overflow-y-auto lg:border-r lg:border-b-0 lg:px-3 lg:py-4"
    >
      <div className="hidden px-2 pb-4 lg:block">
        <p className="text-sm font-semibold tracking-tight text-ink">Revyn</p>
        <p className="text-[11px] leading-relaxed text-muted">Revenue recovery, supervised</p>
      </div>
      {NAV.map((item) => {
        const active = pathname === item.path || (item.path !== "/" && pathname.startsWith(item.path));
        return (
          <Link
            key={item.path}
            href={item.path}
            aria-current={active ? "page" : undefined}
            className={`flex items-center justify-between gap-2 rounded-md px-2.5 py-1.5 text-xs whitespace-nowrap transition ${
              active ? "bg-series-1/14 font-medium text-series-1" : "text-ink-2 hover:bg-raised hover:text-ink"
            }`}
          >
            <span>{item.label}</span>
            {item.path === "/approvals" && approvals > 0 ? (
              <span className="rounded-full bg-warning/20 px-1.5 text-[10px] font-semibold tabular-nums text-warning">
                {approvals}
              </span>
            ) : null}
          </Link>
        );
      })}
    </nav>
  );
}
