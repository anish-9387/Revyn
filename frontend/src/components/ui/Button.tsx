"use client";

import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "ghost" | "danger" | "quiet";

const VARIANT: Record<Variant, string> = {
  primary: "bg-series-1 text-white border-series-1 hover:brightness-110",
  ghost: "bg-raised text-ink border-hairline hover:bg-surface",
  danger: "bg-critical/14 text-critical border-critical/40 hover:bg-critical/22",
  quiet: "bg-transparent text-ink-2 border-transparent hover:text-ink hover:bg-raised",
};

export function Button({
  variant = "ghost",
  size = "md",
  loading = false,
  className = "",
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: "sm" | "md";
  loading?: boolean;
}) {
  const dims = size === "sm" ? "px-2.5 py-1 text-[11px]" : "px-3 py-1.5 text-xs";
  return (
    <button
      {...rest}
      disabled={rest.disabled || loading}
      className={`inline-flex items-center gap-1.5 rounded-md border font-medium transition disabled:cursor-not-allowed disabled:opacity-45 ${dims} ${VARIANT[variant]} ${className}`}
    >
      {loading ? <span className="animate-pulse" aria-hidden>&bull;&bull;&bull;</span> : children}
    </button>
  );
}
