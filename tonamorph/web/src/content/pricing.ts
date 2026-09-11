import type { Plan } from "@/lib/api";

/** Contract §3 facts, used when the API is unreachable at request time. */
export const staticPlans: Plan[] = [
  { id: "free", name: "Free", credits: 3, price_usd: 0, interval: null, checkout_url: null },
  { id: "pack_50", name: "50 Credits", credits: 50, price_usd: 9, interval: null, checkout_url: null },
  { id: "sub_monthly", name: "Pro Monthly", credits: 60, price_usd: 7.99, interval: "month", checkout_url: null },
];

export interface PlanCopy {
  eyebrow: string;
  summary: string;
  bullets: string[];
  highlight?: boolean;
}

export const planCopy: Record<string, PlanCopy> = {
  free: {
    eyebrow: "To start",
    summary: "Three clips on the house. No card, no trial clock.",
    bullets: ["3 credits at signup", "Every feature of the plugin", "Credits never expire"],
  },
  pack_50: {
    eyebrow: "Pay once",
    summary: "Fifty clips whenever you need them.",
    bullets: ["50 credits for $9", "Never expire", "Stack as many packs as you like"],
    highlight: true,
  },
  sub_monthly: {
    eyebrow: "For daily use",
    summary: "Sixty clips every month, cheapest per clip.",
    bullets: ["60 credits every month", "Unused monthly credits expire at period end", "Cancel any time; keep credits until the period ends"],
  },
};

export const planOrder = ["free", "pack_50", "sub_monthly"];

/** One credit = one processed clip. */
export function creditsLabel(plan: Plan): string {
  if (plan.id === "free") return `${plan.credits} free credits`;
  return plan.interval ? `${plan.credits} credits / ${plan.interval}` : `${plan.credits} credits`;
}
