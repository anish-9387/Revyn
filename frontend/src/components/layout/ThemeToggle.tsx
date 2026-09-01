"use client";

import { useEffect, useState } from "react";

import { applyTheme, readTheme, type Theme } from "@/lib/theme";

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("dark");

  useEffect(() => setTheme(readTheme()), []);

  const flip = () => {
    const next: Theme = theme === "dark" ? "light" : "dark";
    applyTheme(next);
    setTheme(next);
  };

  return (
    <button
      type="button"
      onClick={flip}
      title={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
      aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} theme`}
      className="hairline rounded-md bg-raised px-2 py-1 text-xs text-ink-2 hover:text-ink"
    >
      {theme === "dark" ? "◐ Dark" : "◑ Light"}
    </button>
  );
}
