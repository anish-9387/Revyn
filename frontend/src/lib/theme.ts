"use client";

/**
 * Theme preference persisted per browser, with the document's `data-theme` as the source of
 * truth so a pre-paint inline script can set it before React exists.
 */

export type Theme = "dark" | "light";

const STORAGE_KEY = "revyn-theme";
const listeners = new Set<() => void>();

export function readTheme(): Theme {
  if (typeof document === "undefined") return "dark";
  return document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

export function applyTheme(theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  try {
    window.localStorage.setItem(STORAGE_KEY, theme);
  } catch {
    // Private-mode storage denial must not break the toggle.
  }
  for (const listener of listeners) listener();
}

/** `useSyncExternalStore` contract: the DOM attribute is the store. */
export function subscribeTheme(onChange: () => void): () => void {
  listeners.add(onChange);
  window.addEventListener("storage", onChange);
  return () => {
    listeners.delete(onChange);
    window.removeEventListener("storage", onChange);
  };
}

export const serverTheme = (): Theme => "dark";
