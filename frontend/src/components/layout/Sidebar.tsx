"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

import { IconButton } from "@/components/ui/Button";
import { NAV } from "@/lib/routes";

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <span
        aria-hidden
        className="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-[16px] font-bold text-white shadow-soft"
        style={{ background: "linear-gradient(135deg, #276DFF 0%, #3AA07A 55%, #8E7BFF 100%)" }}
      >
        R
      </span>
      <span className="min-w-0">
        <span className="block text-[15px] font-semibold tracking-tight text-ink leading-none">Revyn</span>
        {compact ? null : <span className="block truncate text-[11px] tracking-wide text-muted">Revenue recovery</span>}
      </span>
      <span className="ml-auto hidden h-6 items-center rounded-full bg-series-1/10 px-2 text-[10px] font-semibold tracking-widest text-series-1 sm:inline-flex">LIVE</span>
    </div>
  );
}

function NavIcon({ name, active }: { name: string; active: boolean }) {
  const cls = `h-[15px] w-[15px] shrink-0 ${active ? "text-series-1" : "text-muted"}`;
  switch (name) {
    case "grid":
      return (
        <svg viewBox="0 0 16 16" className={cls} fill="none" aria-hidden>
          <rect x="1.5" y="1.5" width="5.5" height="5.5" rx="1.2" stroke="currentColor" strokeWidth="1.3" />
          <rect x="8.5" y="1.5" width="5.5" height="5.5" rx="1.2" stroke="currentColor" strokeWidth="1.3" />
          <rect x="1.5" y="8.5" width="5.5" height="5.5" rx="1.2" stroke="currentColor" strokeWidth="1.3" />
          <rect x="8.5" y="8.5" width="5.5" height="5.5" rx="1.2" stroke="currentColor" strokeWidth="1.3" />
        </svg>
      );
    case "radar":
      return (
        <svg viewBox="0 0 16 16" className={cls} fill="none" aria-hidden>
          <circle cx="8" cy="8" r="5.6" stroke="currentColor" strokeWidth="1.3" />
          <circle cx="8" cy="8" r="2.2" stroke="currentColor" strokeWidth="1.2" />
          <path d="M8 2.2 L8 5 M8 11 L8 13.8 M2.2 8 L5 8 M11 8 L13.8 8" stroke="currentColor" strokeWidth="1.15" strokeLinecap="round" />
        </svg>
      );
    case "route":
      return (
        <svg viewBox="0 0 16 16" className={cls} fill="none" aria-hidden>
          <circle cx="3.6" cy="3.8" r="1.6" stroke="currentColor" strokeWidth="1.3" />
          <circle cx="12.4" cy="12.2" r="1.6" stroke="currentColor" strokeWidth="1.3" />
          <path d="M4.8 5 Q8 7.5 11.2 10.8" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" fill="none" />
          <circle cx="8" cy="8" r="1.15" fill="currentColor" opacity="0.85" />
        </svg>
      );
    case "shield":
      return (
        <svg viewBox="0 0 16 16" className={cls} fill="none" aria-hidden>
          <path d="M8 1.6 L12.6 4.2 V8.1 C12.6 10.8 10.7 13 8 14.1 C5.3 13 3.4 10.8 3.4 8.1 V4.2Z" stroke="currentColor" strokeWidth="1.3" strokeLinejoin="round" />
          <path d="M6 8.1 L7.5 9.6 L10.4 6.4" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      );
    case "layers":
      return (
        <svg viewBox="0 0 16 16" className={cls} fill="none" aria-hidden>
          <path d="M2.2 6.2 L8 2.8 L13.8 6.2 L8 9.6Z" stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round" />
          <path d="M2.2 9 L8 12.4 L13.8 9" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round" opacity="0.75" />
        </svg>
      );
    case "chart":
      return (
        <svg viewBox="0 0 16 16" className={cls} fill="none" aria-hidden>
          <rect x="2" y="9.5" width="2.6" height="4" rx="0.7" stroke="currentColor" strokeWidth="1.2" />
          <rect x="6.2" y="6.2" width="2.6" height="7.3" rx="0.7" stroke="currentColor" strokeWidth="1.2" />
          <rect x="10.8" y="3" width="2.6" height="10.5" rx="0.7" stroke="currentColor" strokeWidth="1.2" />
        </svg>
      );
    case "flask":
      return (
        <svg viewBox="0 0 16 16" className={cls} fill="none" aria-hidden>
          <path d="M6.2 2.2 H9.8 L9.8 6.2 L12.4 10.6 C13 11.7 12.2 13.4 10.9 13.4 H5.1 C3.8 13.4 3 11.7 3.6 10.6Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
          <path d="M5.6 9 H10.4" stroke="currentColor" strokeWidth="1.1" strokeLinecap="round" opacity="0.6" />
        </svg>
      );
    case "coins":
      return (
        <svg viewBox="0 0 16 16" className={cls} fill="none" aria-hidden>
          <ellipse cx="8" cy="4.8" rx="4.4" ry="2.1" stroke="currentColor" strokeWidth="1.25" />
          <path d="M3.6 4.8 V9.6 C3.6 10.75 5.57 11.7 8 11.7 C10.43 11.7 12.4 10.75 12.4 9.6 V4.8" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
          <ellipse cx="8" cy="9.6" rx="4.4" ry="2.1" stroke="currentColor" strokeWidth="1.15" opacity="0.85" />
        </svg>
      );
    case "book":
      return (
        <svg viewBox="0 0 16 16" className={cls} fill="none" aria-hidden>
          <path d="M3 2.6 C3 2.6 5 1.9 8 2.6 V13.2 C5 12.5 3 13.2 3 13.2Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
          <path d="M13 2.6 C13 2.6 11 1.9 8 2.6 V13.2 C11 12.5 13 13.2 13 13.2Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
          <path d="M8 2.6 V13.2" stroke="currentColor" strokeWidth="1.15" />
        </svg>
      );
    case "sliders":
      return (
        <svg viewBox="0 0 16 16" className={cls} fill="none" aria-hidden>
          <path d="M2 4.2 H6.2" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
          <path d="M9.8 4.2 H14" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
          <circle cx="8" cy="4.2" r="1.6" stroke="currentColor" strokeWidth="1.2" fill="var(--surface)" />
          <path d="M2 11.8 H9.2" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
          <path d="M12.8 11.8 H14" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" />
          <circle cx="11" cy="11.8" r="1.6" stroke="currentColor" strokeWidth="1.2" fill="var(--surface)" />
        </svg>
      );
    case "scroll":
      return (
        <svg viewBox="0 0 16 16" className={cls} fill="none" aria-hidden>
          <path d="M5 2.4 H11 C11 2.4 11.8 2.4 11.8 3.2 V12.8 C11.8 13.6 11 13.6 11 13.6 H5 C4.2 13.6 4.2 12.8 4.2 12.8 V3.2 C4.2 2.4 5 2.4 5 2.4Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" />
          <path d="M6.2 6 H9.8 M6.2 8.2 H9.8 M6.2 10.4 H9" stroke="currentColor" strokeWidth="1.15" strokeLinecap="round" />
        </svg>
      );
    default:
      return <span className={cls} aria-hidden>•</span>;
  }
}

function NavList({ approvals, onNavigate }: { approvals: number; onNavigate?: () => void }) {
  const pathname = usePathname();
  return (
    <ul className="flex-1 space-y-0.5 overflow-y-auto py-1 pr-1">
      {NAV.map((item) => {
        const active = pathname === item.path || (item.path !== "/" && pathname.startsWith(item.path));
        return (
          <li key={item.path}>
            <Link
              href={item.path}
              title={item.hint}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={`group relative flex items-center gap-2.5 rounded-xl px-2.5 py-[8px] text-[13px] leading-none transition-all ${
                active ? "bg-[color-mix(in_oklab,var(--series-1)_10%,var(--raised))] font-medium text-ink shadow-soft" : "text-ink-2 hover:bg-raised hover:text-ink"
              }`}
            >
              <span
                aria-hidden
                className={`absolute top-1/2 left-0 h-6 w-[3px] -translate-y-1/2 rounded-full bg-series-1 transition-all ${active ? "opacity-100" : "opacity-0 group-hover:opacity-30"}`}
              />
              <NavIcon name={(item as { icon: string }).icon} active={active} />
              <span className="min-w-0 truncate">{item.label}</span>
              {item.path === "/approvals" && approvals > 0 ? (
                <span className="ml-auto grid h-5 min-w-5 place-items-center rounded-full bg-warning px-1.5 text-[11px] font-bold leading-none text-white shadow-soft">
                  {approvals > 99 ? "99+" : approvals}
                </span>
              ) : null}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

export function Sidebar({ approvals, open, onClose }: { approvals: number; open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = ""; };
  }, [open, onClose]);

  return (
    <>
      <nav aria-label="Sections" className="hidden lg:flex lg:h-dvh lg:w-[16rem] lg:shrink-0 lg:flex-col lg:border-r lg:border-hairline lg:bg-surface/70 lg:backdrop-blur-xl lg:px-3 lg:py-4">
        <div className="px-2 pb-3.5"><Brand /></div>
        <div className="mb-2 h-px bg-hairline/60" />
        <NavList approvals={approvals} />
        <div className="mt-auto border-t border-hairline/60 pt-3">
          <div className="rounded-xl bg-raised px-3 py-2.5">
            <p className="text-[11px] font-semibold tracking-wide text-ink">Need help?</p>
            <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-muted">Guardrails keep every recovery inside your limits. Adjust them in Guardrails.</p>
          </div>
        </div>
      </nav>
      {open ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button type="button" aria-label="Close navigation" onClick={onClose} className="animate-fade absolute inset-0 bg-black/55 backdrop-blur-[3px]" />
          <nav aria-label="Sections" className="animate-drawer relative flex h-full w-[17.5rem] max-w-[84vw] flex-col border-r border-hairline bg-surface px-3 py-3.5 shadow-float">
            <div className="flex items-center justify-between gap-2 pb-3">
              <Brand />
              <IconButton label="Close navigation" onClick={onClose}><span aria-hidden className="text-[11px]">✕</span></IconButton>
            </div>
            <div className="mb-2 h-px bg-hairline/60" />
            <NavList approvals={approvals} onNavigate={onClose} />
          </nav>
        </div>
      ) : null}
    </>
  );
}
