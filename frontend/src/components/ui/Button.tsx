"use client";

import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "ghost" | "danger" | "quiet";

const VARIANT: Record<Variant, string> = {
  primary: "border-transparent bg-series-1 text-white shadow-soft hover:brightness-[1.07] hover:shadow-lift active:brightness-[0.98]",
  ghost: "border-hairline bg-raised text-ink hover:border-hairline-strong hover:bg-elevated hover:shadow-soft",
  danger: "border-critical/25 bg-critical/10 text-critical hover:bg-critical/15 hover:border-critical/30",
  quiet: "border-transparent bg-transparent text-ink-2 hover:bg-raised hover:text-ink",
};

const SIZE = {
  sm: "h-8 gap-1.5 px-3 text-[12px] rounded-full",
  md: "h-9 gap-2 px-4 text-[13px] rounded-xl",
};

export function Button({
  variant = "ghost",
  size = "md",
  loading = false,
  className = "",
  children,
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: "sm" | "md"; loading?: boolean }) {
  return (
    <button
      {...rest}
      disabled={rest.disabled || loading}
      aria-busy={loading || undefined}
      className={`press inline-flex shrink-0 items-center justify-center border font-medium transition-all disabled:cursor-not-allowed disabled:opacity-45 focus-ring ${SIZE[size]} ${VARIANT[variant]} ${className}`}
    >
      {loading ? <span aria-hidden className="h-3.5 w-3.5 animate-spin rounded-full border-[1.7px] border-current/30 border-t-current" /> : null}
      {children}
    </button>
  );
}

export function IconButton({
  label,
  children,
  className = "",
  ...rest
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string; children: React.ReactNode }) {
  return (
    <button
      {...rest}
      title={label}
      aria-label={label}
      className={`press inline-flex h-9 w-9 items-center justify-center rounded-xl border border-hairline bg-raised text-ink-2 transition-all hover:border-hairline-strong hover:bg-elevated hover:text-ink hover:shadow-soft focus-ring ${className}`}
    >
      {children}
    </button>
  );
}
