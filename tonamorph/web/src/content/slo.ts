/**
 * Service-level objectives published on /status. These are commitments the status page
 * reports against, not contractual terms: the Terms of Service promise only what the
 * code already guarantees (a failed morph is never charged).
 */
export interface SloTarget {
  id: string;
  name: string;
  target: string;
  detail: string;
}

export const sloTargets: readonly SloTarget[] = [
  {
    id: "availability",
    name: "Availability",
    target: "99.5 % per month",
    detail:
      "The API health check and new morph submissions answer within the month for at least 99.5 % of minutes (about 3.6 hours of allowance). Announced maintenance, posted at least 24 hours ahead and capped at 2 hours a month, is excluded.",
  },
  {
    id: "success",
    name: "Morph success",
    target: "≥ 99 %",
    detail: "At least 99 % of morphs that start finish with stems, MIDI, key and BPM. The rest are not charged.",
  },
  {
    id: "latency",
    name: "Time to result",
    target: "p95 ≤ 10 s warm",
    detail:
      "From upload complete to playable, queue included: p50 at or under 4 s and p95 at or under 10 s while the engine is warm. The first morph after a long idle can take up to 45 s.",
  },
];

/** Announced maintenance is excluded from availability only under these conditions. */
export const maintenancePolicy = {
  noticeHours: 24,
  maxHoursPerMonth: 2,
} as const;
