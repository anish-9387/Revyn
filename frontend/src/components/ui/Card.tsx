import type { Route } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

export function Card({ children, className = "", pad = true, hover = false }: { children: ReactNode; className?: string; pad?: boolean; hover?: boolean }) {
  return (
    <section className={`panel panel-sheen rounded-card min-w-0 overflow-hidden ${pad ? "p-4 sm:p-5" : ""} ${hover ? "lift" : ""} ${className}`}>{children}</section>
  );
}

export function CardHead({ title, hint, actions }: { title: ReactNode; hint?: ReactNode; actions?: ReactNode }) {
  return (
    <header className="mb-4 flex flex-col gap-2.5 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
      <div className="min-w-0">
        <h2 className="text-[14.5px] font-semibold tracking-tight text-ink leading-tight">{title}</h2>
        {hint ? <p className="mt-1.5 text-xs leading-relaxed text-muted sm:text-[12.5px] max-w-prose">{hint}</p> : null}
      </div>
      {actions ? <div className="flex min-w-0 flex-wrap items-center gap-2 sm:justify-end shrink-0">{actions}</div> : null}
    </header>
  );
}

export function PageHead({ title, hint, actions }: { title: string; hint?: string; actions?: ReactNode }) {
  return (
    <header className="animate-rise flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
      <div className="min-w-0">
        <h1 className="text-[22px] font-bold tracking-tight text-ink sm:text-[28px] leading-[1.05]">{title}</h1>
        {hint ? <p className="mt-1.5 max-w-2xl text-[13px] leading-relaxed text-ink-2 sm:text-sm">{hint}</p> : null}
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div> : null}
    </header>
  );
}

export function CardLink({ href, children }: { href: Route; children: ReactNode }) {
  return (
    <Link href={href} className="press group inline-flex items-center gap-1.5 rounded-full border border-hairline bg-raised px-3 py-1.5 text-[11.5px] font-medium text-ink-2 transition-all hover:border-hairline-strong hover:bg-elevated hover:text-ink hover:shadow-soft">
      {children}
      <span aria-hidden className="text-[11px] transition-transform duration-200 group-hover:translate-x-0.5">→</span>
    </Link>
  );
}
