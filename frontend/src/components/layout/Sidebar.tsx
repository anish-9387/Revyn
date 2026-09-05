"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";

import { IconButton } from "@/components/ui/Button";
import { BarChart3, BookOpen, Coins, FlaskConical, Layers, LayoutGrid, Radar, Route, ScrollText, ShieldCheck, SlidersHorizontal, Sparkles } from "@/lib/icons";
import { NAV } from "@/lib/routes";

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <span
        aria-hidden
        className="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-[16px] font-bold text-white shadow-soft"
        style={{ background: "linear-gradient(135deg, #2563EB 0%, #06B6D4 55%, #7C3AED 100%)" }}
      >
        R
      </span>
      <span className="min-w-0">
        <span className="block text-[15px] font-semibold tracking-tight text-ink leading-none">Revyn</span>
        {compact ? null : <span className="block truncate text-[11px] tracking-wide text-muted">Revenue recovery</span>}
      </span>
      <span className="ml-auto hidden h-6 items-center rounded-full bg-blue-50 px-2 text-[10px] font-semibold tracking-widest text-blue-600 ring-1 ring-blue-200 sm:inline-flex">LIVE</span>
    </div>
  );
}

function NavIcon({ name, active }: { name: string; active: boolean }) {
  const cls = `h-[15px] w-[15px] shrink-0 ${active ? "text-blue-600" : "text-slate-400"}`;
  const props = { className: cls, size: 15 } as const;
  switch (name) {
    case "grid": return <LayoutGrid {...props} />;
    case "radar": return <Radar {...props} />;
    case "route": return <Route {...props} />;
    case "shield": return <ShieldCheck {...props} />;
    case "layers": return <Layers {...props} />;
    case "chart": return <BarChart3 {...props} />;
    case "flask": return <FlaskConical {...props} />;
    case "coins": return <Coins {...props} />;
    case "book": return <BookOpen {...props} />;
    case "sliders": return <SlidersHorizontal {...props} />;
    case "scroll": return <ScrollText {...props} />;
    case "sparkles": return <Sparkles {...props} />;
    default: return <span className={cls} aria-hidden>•</span>;
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
