/**
 * Status-page incident log and scheduled maintenance. Newest first. An incident stays
 * listed for 90 days after it is resolved; maintenance windows are announced at least
 * 24 hours ahead and are limited to two hours a month (see slo.ts).
 */
export type IncidentState = "investigating" | "identified" | "monitoring" | "resolved";

export interface IncidentUpdate {
  /** ISO 8601 timestamp with offset, e.g. "2026-09-14T18:05:00-04:00". */
  at: string;
  state: IncidentState;
  body: string;
}

export interface Incident {
  id: string;
  title: string;
  /** Component keys from the status API: api, engine, payments, website. */
  components: readonly string[];
  /** Oldest first. */
  updates: readonly IncidentUpdate[];
}

export interface MaintenanceWindow {
  id: string;
  title: string;
  /** ISO 8601 timestamps with offset. */
  starts_at: string;
  ends_at: string;
  body: string;
}

export const incidents: readonly Incident[] = [];

export const scheduledMaintenance: readonly MaintenanceWindow[] = [];
