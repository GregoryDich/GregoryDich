import type { Plan } from "@/lib/api";

/**
 * Contract §3 facts, used when the API is unreachable at request time. In copy a credit
 * is a "morph" (one clip up to 60 s → stems, MIDI, key and BPM); the API and the ledger
 * keep calling them credits.
 */
export const staticPlans: Plan[] = [
  { id: "free", name: "Free", credits: 3, price_usd: 0, interval: null, checkout_url: null },
  { id: "pack_50", name: "50 Credits", credits: 50, price_usd: 9, interval: null, checkout_url: null },
  { id: "sub_monthly", name: "Pro Monthly", credits: 60, price_usd: 7.99, interval: "month", checkout_url: null },
];

export interface PlanCopy {
  eyebrow: string;
  /** Card title in customer wording; the API's plan name is kept for receipts. */
  title: string;
  summary: string;
  bullets: string[];
  highlight?: boolean;
}

export const planCopy: Record<string, PlanCopy> = {
  free: {
    eyebrow: "To start",
    title: "3 free morphs",
    summary: "Three morphs on the house. No card, no trial clock.",
    bullets: ["3 morphs at signup", "Every feature of the plugin", "Failed morphs are not charged"],
  },
  pack_50: {
    eyebrow: "Pay once",
    title: "50 morphs",
    summary: "Fifty morphs whenever you need them.",
    bullets: ["50 morphs for $9, once", "Pack morphs never expire", "Stack as many packs as you like"],
    highlight: true,
  },
  sub_monthly: {
    eyebrow: "For daily use",
    title: "60 morphs a month",
    summary: "Sixty morphs every month, cheapest per morph.",
    bullets: ["60 morphs for $7.99 a month", "Subscription morphs reset monthly", "Cancel any time; keep morphs until the period ends"],
  },
};

export const planOrder = ["free", "pack_50", "sub_monthly"];

/** The refund rule, verbatim from the brand platform. */
export const MORPH_GUARANTEE = "If a morph is unusable, that morph is refunded.";

export const PRICING_HEADLINE = "50 morphs for $9, once. 60 morphs a month for $7.99.";

export const PRICING_SUBHEAD =
  "One morph = one clip up to 60 s → stems, MIDI, key and BPM. Failed morphs are not charged. Pack morphs never expire; subscription morphs reset monthly.";

/** One morph = one processed clip. */
export function creditsLabel(plan: Plan): string {
  if (plan.id === "free") return `${plan.credits} free morphs`;
  return plan.interval ? `${plan.credits} morphs / ${plan.interval}` : `${plan.credits} morphs`;
}
