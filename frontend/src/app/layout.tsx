import type { Metadata, Viewport } from "next";

import { AppShell } from "@/components/layout/AppShell";

import "./globals.css";

export const metadata: Metadata = {
  title: "Revyn — Autonomous Revenue Recovery",
  description:
    "Agentic revenue recovery: detects failed payments, abandoned checkouts, failed subscriptions and overdue invoices, then recovers them under merchant guardrails.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#0d0d0d" },
    { media: "(prefers-color-scheme: light)", color: "#f9f9f7" },
  ],
};

// Runs before paint so a light-theme reader never sees a dark flash.
const THEME_BOOTSTRAP = `try{var t=localStorage.getItem("revyn-theme");if(t==="light")document.documentElement.dataset.theme="light"}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOTSTRAP }} />
      </head>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
