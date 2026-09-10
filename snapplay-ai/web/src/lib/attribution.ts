/**
 * Attribution (GROWTH.md §7): `ref` and `utm_*` from the landing URL. They travel through
 * the funnel in the URL itself (see AttributedLink) so that no storage is needed before a
 * cookie choice is made; once the visitor grants functional cookies they are also kept for
 * 30 days — `ref` in the `ref` cookie (readable by server-rendered pages) and everything in
 * local storage — and attached to the signup as user metadata.
 */
import { deleteCookie, functionalConsentGranted } from "./consent";
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

/** Query string (without `?`) carrying the attribution parameters present in `search`. */
export function attributionQuery(search: string): string {
  const source = new URLSearchParams(search);
  const out = new URLSearchParams();
  for (const key of ["ref", ...UTM_KEYS]) {
    const value = source.get(key);
    if (value) out.set(key, value);
  }
  return out.toString();
}

/** Persists attribution from the current URL — only once functional cookies are granted. */
export function captureAttribution(search: string): void {
  if (!functionalConsentGranted()) return;
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

export function clearAttribution(): void {
  try {
    window.localStorage.removeItem(ATTRIBUTION_STORAGE_KEY);
  } catch {
    // Nothing stored.
  }
  deleteCookie(REF_COOKIE);
}

export function readAttribution(): Attribution {
  if (!functionalConsentGranted()) return {};
  try {
    const raw = window.localStorage.getItem(ATTRIBUTION_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Partial<StoredAttribution>;
    if (typeof parsed.captured_at !== "number" || Date.now() - parsed.captured_at > MAX_AGE_SECONDS * 1000) {
      return {};
    }
    const attribution: Attribution = {};
    if (typeof parsed.referral_code === "string") attribution.referral_code = parsed.referral_code;
    for (const key of UTM_KEYS) {
      const value = parsed[key];
      if (typeof value === "string") attribution[key] = value;
    }
    return attribution;
  } catch {
    return {};
  }
}
