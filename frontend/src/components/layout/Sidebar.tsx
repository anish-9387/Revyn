"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { IconButton } from "@/components/ui/Button";
import {
  BarChart3, BookOpen, Coins, FlaskConical, Layers, LayoutGrid,
  PanelLeftClose, PanelLeftOpen, Radar, Route, ScrollText,
  ShieldCheck, SlidersHorizontal, Sparkles, X,
} from "@/lib/icons";
import { NAV } from "@/lib/routes";

const STORAGE_KEY = "revyn_sidebar_collapsed";

function Brand({ collapsed = false }: { collapsed?: boolean }) {
  return (
    <div className={`flex items-center gap-2.5 min-w-0 ${collapsed ? "justify-center" : ""}`}>
      <span
        aria-hidden
        className="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-[16px] font-bold text-white shadow-soft"
        style={{ background: "linear-gradient(135deg, #2563EB 0%, #06B6D4 55%, #7C3AED 100%)" }}
      >
        R
      </span>
      {!collapsed && (
        <span className="min-w-0">
          <span className="block text-[15px] font-semibold tracking-tight text-ink leading-none">Revyn</span>
          <span className="block truncate text-[11px] tracking-wide text-muted">Revenue recovery</span>
        </span>
      )}
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

function NavList({
  approvals,
  collapsed,
  onNavigate,
}: {
  approvals: number;
  collapsed?: boolean;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  return (
    <ul className="flex-1 space-y-0.5 overflow-y-auto py-1 pr-1">
      {NAV.map((item) => {
        const active = pathname === item.path || (item.path !== "/" && pathname.startsWith(item.path));
        return (
          <li key={item.path}>
            <Link
              href={item.path}
              title={collapsed ? item.label : item.hint}
              onClick={onNavigate}
              aria-current={active ? "page" : undefined}
              className={`group relative flex items-center gap-2.5 rounded-xl px-2.5 py-[8px] text-[13px] leading-none transition-all ${collapsed ? "justify-center" : ""} ${
                active
                  ? "bg-[color-mix(in_oklab,var(--series-1)_10%,var(--raised))] font-medium text-ink shadow-soft"
                  : "text-ink-2 hover:bg-raised hover:text-ink"
              }`}
            >
              <span
                aria-hidden
                className={`absolute top-1/2 left-0 h-6 w-[3px] -translate-y-1/2 rounded-full bg-series-1 transition-all ${active ? "opacity-100" : "opacity-0 group-hover:opacity-30"}`}
              />
              <NavIcon name={(item as { icon: string }).icon} active={active} />
              {!collapsed && <span className="min-w-0 truncate">{item.label}</span>}
              {!collapsed && item.path === "/approvals" && approvals > 0 ? (
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

export function Sidebar({
  approvals,
  open,
  onClose,
}: {
  approvals: number;
  open: boolean;
  onClose: () => void;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const initialized = useRef(false);

  // Load persisted state once on mount
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === "true") setCollapsed(true);
    } catch {}
  }, []);

  const toggle = useCallback(() => {
    setCollapsed((prev) => {
      const next = !prev;
      try { localStorage.setItem(STORAGE_KEY, String(next)); } catch {}
      return next;
    });
  }, []);

  // Close mobile drawer on Escape
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = ""; };
  }, [open, onClose]);

  return (
    <>
      {/* ── Desktop sidebar ─────────────────────────────── */}
      <nav
        aria-label="Sections"
        className={`hidden lg:flex lg:h-dvh lg:shrink-0 lg:flex-col lg:border-r lg:border-hairline lg:bg-surface/70 lg:backdrop-blur-xl lg:px-3 lg:py-4 sidebar-transition overflow-hidden ${
          collapsed ? "lg:w-[3.75rem]" : "lg:w-[16rem]"
        }`}
      >
        {/* Brand + collapse toggle */}
        <div className={`flex items-center pb-3.5 ${collapsed ? "justify-center px-1" : "px-2 justify-between"}`}>
          <Brand collapsed={collapsed} />
          <button
            type="button"
            onClick={toggle}
            title={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
            className="hidden lg:grid h-7 w-7 place-items-center rounded-lg text-muted hover:bg-raised hover:text-ink transition-all ml-1 shrink-0"
          >
            {collapsed ? <PanelLeftOpen size={14} /> : <PanelLeftClose size={14} />}
          </button>
        </div>
        <div className="mb-2 h-px bg-hairline/60" />
        <NavList approvals={approvals} collapsed={collapsed} />
        {!collapsed && (
          <div className="mt-auto border-t border-hairline/60 pt-3">
            <div className="rounded-xl bg-raised px-3 py-2.5">
              <p className="text-[11px] font-semibold tracking-wide text-ink">Need help?</p>
              <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-muted">
                Guardrails keep every recovery inside your limits. Adjust them in Guardrails.
              </p>
            </div>
          </div>
        )}
      </nav>

      {/* ── Mobile drawer ───────────────────────────────── */}
      {open ? (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            type="button"
            aria-label="Close navigation"
            onClick={onClose}
            className="animate-fade absolute inset-0 bg-black/55 backdrop-blur-[3px]"
          />
          <nav
            aria-label="Sections"
            className="animate-drawer relative flex h-full w-[17.5rem] max-w-[84vw] flex-col border-r border-hairline bg-surface px-3 py-3.5 shadow-float"
          >
            <div className="flex items-center justify-between gap-2 pb-3">
              <Brand />
              <IconButton label="Close navigation" onClick={onClose}>
                <X size={14} aria-hidden />
              </IconButton>
            </div>
            <div className="mb-2 h-px bg-hairline/60" />
            <NavList approvals={approvals} onNavigate={onClose} />
          </nav>
        </div>
      ) : null}
    </>
  );
}
