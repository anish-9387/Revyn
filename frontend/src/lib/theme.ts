"use client";

/** Theme preference persisted per browser; the document carries `data-theme`. */

export type Theme = "dark" | "light";
const STORAGE_KEY = "revyn-theme";

export function readTheme(): Theme {
  if (typeof document === "undefined") return "dark";
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored === "light" ? "light" : "dark";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  window.localStorage.setItem(STORAGE_KEY, theme);
}
