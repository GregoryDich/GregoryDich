/**
 * Turns whatever `GET /v1/status` returns into what the status page renders. The parser is
 * deliberately forgiving: a component may arrive as a plain state string or as an object
 * with a `status`/`state` field, unknown states are shown verbatim, and a missing number
 * renders as a dash rather than breaking the page.
 */

export const COMPONENT_KEYS = ["api", "engine", "payments", "website"] as const;
export type ComponentKey = (typeof COMPONENT_KEYS)[number];

export const COMPONENT_LABELS: Record<ComponentKey, string> = {
  api: "API",
  engine: "Morph engine",
  payments: "Payments",
  website: "Website & account",
};

export type ComponentState = "operational" | "degraded" | "down" | "maintenance" | "unknown";

export interface ComponentView {
  key: ComponentKey;
  label: string;
  state: ComponentState;
  /** The API's own wording when it is not one of the known states. */
  raw: string | null;
}

export interface Last24hView {
  morphs: number | null;
  /** 0–100, one decimal. */
  successRatePercent: number | null;
  p50Ms: number | null;
  p95Ms: number | null;
}

export interface StatusView {
  components: ComponentView[];
  last24h: Last24hView;
  overall: ComponentState;
}

const KNOWN_STATES: Record<string, ComponentState> = {
  operational: "operational",
  ok: "operational",
  up: "operational",
  healthy: "operational",
  degraded: "degraded",
  slow: "degraded",
  partial_outage: "degraded",
  down: "down",
  outage: "down",
  major_outage: "down",
  maintenance: "maintenance",
};

/** Worst state wins for the page headline. */
const SEVERITY: ComponentState[] = ["down", "degraded", "maintenance", "unknown", "operational"];

function componentState(value: unknown): { state: ComponentState; raw: string | null } {
  let text: string | null = null;
  if (typeof value === "string") {
    text = value;
  } else if (value && typeof value === "object") {
    const field = (value as Record<string, unknown>).status ?? (value as Record<string, unknown>).state;
    if (typeof field === "string") text = field;
  }
  if (!text) return { state: "unknown", raw: null };
  const known = KNOWN_STATES[text.trim().toLowerCase()];
  return known ? { state: known, raw: null } : { state: "unknown", raw: text.trim().slice(0, 40) };
}

function finiteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function successRatePercent(value: unknown): number | null {
  const rate = finiteNumber(value);
  if (rate === null || rate < 0) return null;
  const percent = rate <= 1 ? rate * 100 : rate;
  return percent > 100 ? null : Math.round(percent * 10) / 10;
}

export function parseStatus(input: unknown): StatusView {
  const root = input && typeof input === "object" ? (input as Record<string, unknown>) : {};
  const rawComponents = root.components && typeof root.components === "object" ? (root.components as Record<string, unknown>) : {};
  const components = COMPONENT_KEYS.map((key) => ({ key, label: COMPONENT_LABELS[key], ...componentState(rawComponents[key]) }));

  const window24h = root.last_24h && typeof root.last_24h === "object" ? (root.last_24h as Record<string, unknown>) : {};
  const last24h: Last24hView = {
    morphs: finiteNumber(window24h.morphs),
    successRatePercent: successRatePercent(window24h.success_rate),
    p50Ms: finiteNumber(window24h.p50_ms),
    p95Ms: finiteNumber(window24h.p95_ms),
  };

  const overall = SEVERITY.find((state) => components.some((component) => component.state === state)) ?? "unknown";
  return { components, last24h, overall };
}

export const STATE_LABELS: Record<ComponentState, string> = {
  operational: "Operational",
  degraded: "Degraded",
  down: "Down",
  maintenance: "Maintenance",
  unknown: "Unknown",
};

export const OVERALL_LABELS: Record<ComponentState, string> = {
  operational: "All systems operational",
  degraded: "Degraded performance",
  down: "Some systems are down",
  maintenance: "Maintenance in progress",
  unknown: "Status unknown",
};

export function formatMs(value: number | null): string {
  if (value === null) return "—";
  return value >= 1000 ? `${(value / 1000).toFixed(1)} s` : `${Math.round(value)} ms`;
}
