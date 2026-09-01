"use client";

import { useSyncExternalStore } from "react";

import { applyTheme, readTheme, serverTheme, subscribeTheme } from "@/lib/theme";

export function ThemeToggle() {
  const theme = useSyncExternalStore(subscribeTheme, readTheme, serverTheme);
  const next = theme === "dark" ? "light" : "dark";

  return (
    <button
      type="button"
      onClick={() => applyTheme(next)}
      title={`Switch to ${next} theme`}
      aria-label={`Switch to ${next} theme`}
      className="hairline rounded-md bg-raised px-2 py-1 text-xs text-ink-2 hover:text-ink"
    >
      {theme === "dark" ? "◐ Dark" : "◑ Light"}
    </button>
  );
}
