/**
 * Client-side attribution capture (GROWTH.md §7): `ref` and `utm_*` from the landing URL
 * are kept for 30 days and attached to the signup as user metadata. `ref` is also mirrored
 * into a cookie so server-rendered pages can pass it to `GET /v1/plans?ref=`.
 */
import { normalizeReferralCode } from "./redirect";

export const UTM_KEYS = ["utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term"] as const;
export type UtmKey = (typeof UTM_KEYS)[number];

export interface Attribution {
  referral_code?: string;
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_content?: string;
  utm_term?: string;
}

interface StoredAttribution extends Attribution {
  captured_at: number;
}

export const ATTRIBUTION_STORAGE_KEY = "attribution";
export const REF_COOKIE = "ref";
const MAX_AGE_SECONDS = 30 * 24 * 60 * 60;

export function attributionFromSearch(search: string): Attribution {
  const params = new URLSearchParams(search);
  const out: Attribution = {};
  const ref = normalizeReferralCode(params.get("ref"));
  if (ref) out.referral_code = ref;
  for (const key of UTM_KEYS) {
    const value = params.get(key)?.trim().slice(0, 200);
    if (value) out[key] = value;
  }
  return out;
}

export function captureAttribution(search: string): void {
  const fresh = attributionFromSearch(search);
  if (Object.keys(fresh).length === 0) return;
  const merged: StoredAttribution = { ...readAttribution(), ...fresh, captured_at: Date.now() };
  try {
    window.localStorage.setItem(ATTRIBUTION_STORAGE_KEY, JSON.stringify(merged));
  } catch {
    // Storage unavailable (private mode); the signup form still reads the URL directly.
  }
  if (fresh.referral_code) {
    const secure = window.location.protocol === "https:" ? "; Secure" : "";
    document.cookie = `${REF_COOKIE}=${fresh.referral_code}; Max-Age=${MAX_AGE_SECONDS}; Path=/; SameSite=Lax${secure}`;
  }
}

export function readAttribution(): Attribution {
  try {
    const raw = window.localStorage.getItem(ATTRIBUTION_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Partial<StoredAttribution>;
    if (typeof parsed.captured_at !== "number" || Date.now() - parsed.captured_at > MAX_AGE_SECONDS * 1000) {
      return {};
    }
    const { captured_at: _ignored, ...rest } = parsed;
    return rest;
  } catch {
    return {};
  }
}
