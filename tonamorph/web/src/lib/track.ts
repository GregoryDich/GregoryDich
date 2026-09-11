import { track as vercelTrack } from "@vercel/analytics";
import { readConsent } from "./consent";

/**
 * Web events from the growth taxonomy (docs/GTM_PLAN.md, appendix C §3), sent to Vercel
 * Web Analytics. Custom events are a Vercel Pro feature; on Hobby the calls are accepted
 * and dropped. Properties are deliberately limited to product facts — never an email,
 * user id, IP or anything else that identifies a person — and the union below is the
 * only way to emit one, so a new event has to be added here first.
 */
export type CtaLocation = "header" | "hero" | "free" | "pricing" | "download" | "samplab" | "footer" | "referral";

export type TrackEvent =
  | { name: "cta_clicked"; properties: { cta: string; location: CtaLocation } }
  | { name: "signup_started"; properties?: undefined }
  | { name: "signup_completed"; properties: { source: "web" } }
  | { name: "plugin_downloaded"; properties: { os: "macos" | "windows" } }
  | { name: "demo_play"; properties?: undefined }
  | { name: "pricing_view"; properties?: undefined }
  | { name: "checkout_started"; properties: { plan_id: string; ref?: string } }
  | { name: "nps_submitted"; properties: { score: number } };

export type TrackEventName = TrackEvent["name"];

/** Property keys that must never appear on an event (guarded by the type and by tests). */
export const FORBIDDEN_PROPERTY_KEYS = ["email", "user_id", "userId", "name", "ip", "phone", "address", "comment", "token"] as const;

/** Analytics runs before an explicit choice (cookieless) and stops once the visitor rejects it. */
export function analyticsAllowed(): boolean {
  const record = readConsent();
  return record ? record.analytics : true;
}

/** Emits one typed event; a no-op on the server, when analytics is rejected, or without the Analytics component. */
export function track<E extends TrackEvent>(name: E["name"], ...rest: E extends { properties: infer P } ? (undefined extends P ? [] : [P]) : []): void {
  if (typeof window === "undefined") return;
  if (!analyticsAllowed()) return;
  const properties = rest[0];
  if (properties === undefined) {
    vercelTrack(name);
    return;
  }
  const clean: Record<string, string | number | boolean> = {};
  for (const [key, value] of Object.entries(properties)) {
    if (value === undefined || value === null) continue;
    clean[key] = value as string | number | boolean;
  }
  vercelTrack(name, clean);
}
