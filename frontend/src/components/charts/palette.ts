/**
 * Colour is bound to the entity, never to rank, so a loss class keeps its hue on every
 * chart and across theme swaps. CSS variables are read by the SVG directly.
 */
import type { EventKind } from "@/lib/types";

export const SERIES = [
  "var(--series-1)",
  "var(--series-2)",
  "var(--series-3)",
  "var(--series-4)",
  "var(--series-5)",
  "var(--series-6)",
  "var(--series-7)",
  "var(--series-8)",
] as const;

export const LOSS_CLASS_COLOUR: Record<EventKind, string> = {
  payment_failure: "var(--series-1)",
  cart_abandonment: "var(--series-2)",
  subscription_failure: "var(--series-3)",
  overdue_invoice: "var(--series-4)",
};

export const COHORT_COLOUR = {
  control: "var(--axis)",
  treatment: "var(--series-1)",
} as const;

export const AXIS = {
  stroke: "var(--axis)",
  tick: { fill: "var(--muted)", fontSize: 11 },
  grid: "var(--grid)",
};

export const GAP = 2;

export const seriesColour = (index: number) => SERIES[index % SERIES.length];
