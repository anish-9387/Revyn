"use client";

import { useEffect, useState, useSyncExternalStore } from "react";

import { IconButton } from "@/components/ui/Button";
import { applyTheme, readTheme, serverTheme, subscribeTheme } from "@/lib/theme";

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribeTheme, readTheme, serverTheme);
  const [mounted, setMounted] = useState(false);
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => setMounted(true), []);

  const next = theme === "dark" ? "light" : "dark";
  if (!mounted) {
    return (
      <IconButton label="Toggle theme" className="rounded-full opacity-0" aria-hidden>
        <span className="h-5 w-5" />
      </IconButton>
    );
  }
  return (
    <IconButton label={`Switch to ${next} theme`} onClick={() => applyTheme(next)} className="rounded-full">
      <span aria-hidden className="grid h-5 w-5 place-items-center">
        {theme === "dark" ? (
          <svg viewBox="0 0 16 16" width="15" height="15" fill="none" aria-hidden>
            <path d="M8 2.6 A5.4 5.4 0 1 0 13.4 8.2 A5.2 5.2 0 0 1 8 2.6Z" stroke="currentColor" strokeWidth="1.25" strokeLinejoin="round" />
            <circle cx="8" cy="8" r="1" fill="currentColor" opacity="0.9" />
          </svg>
        ) : (
          <svg viewBox="0 0 16 16" width="15" height="15" fill="none" aria-hidden>
            <circle cx="8" cy="8" r="3.2" stroke="currentColor" strokeWidth="1.25" />
            <path d="M8 1.6 V3 M8 13 V14.4 M1.6 8 H3 M13 8 H14.4 M3.6 3.6 L4.6 4.6 M11.4 11.4 L12.4 12.4 M12.4 3.6 L11.4 4.6 M4.6 11.4 L3.6 12.4" stroke="currentColor" strokeWidth="1.15" strokeLinecap="round" />
          </svg>
        )}
      </span>
    </IconButton>
  );
}
