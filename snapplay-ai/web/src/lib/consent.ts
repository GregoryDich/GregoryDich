/**
 * Cookie consent, matching the cookie policy: the choice lives in the first-party cookie
 * `cookie-consent` (12 months) so both the browser and the server can read it. Categories:
 * functional (the 30-day `ref` cookie), analytics (Vercel Web Analytics — cookieless, but
 * the toggle exists) and marketing (Klaviyo's `__kla_id`, loaded only after opt-in).
 * A Global Privacy Control signal counts as a rejection of marketing cookies until the
 * visitor makes an explicit choice.
 */

export const CONSENT_COOKIE = "cookie-consent";
export const CONSENT_MAX_AGE_SECONDS = 365 * 24 * 60 * 60;
export const OPEN_SETTINGS_EVENT = "cookie-settings:open";

export interface Consent {
  functional: boolean;
  analytics: boolean;
  marketing: boolean;
}

export interface ConsentRecord extends Consent {
  v: 1;
  /** Effective date of the cookie policy the choice was made under. */
  policy: string;
  ts: string;
}

export const ALL_GRANTED: Consent = { functional: true, analytics: true, marketing: true };
export const ALL_DENIED: Consent = { functional: false, analytics: false, marketing: false };

export function parseConsent(raw: string | undefined | null): ConsentRecord | null {
  if (!raw) return null;
  try {
    const parsed = JSON.parse(decodeURIComponent(raw)) as Partial<ConsentRecord>;
    if (parsed.v !== 1) return null;
    return {
      v: 1,
      functional: parsed.functional === true,
      analytics: parsed.analytics === true,
      marketing: parsed.marketing === true,
      policy: typeof parsed.policy === "string" ? parsed.policy : "",
      ts: typeof parsed.ts === "string" ? parsed.ts : "",
    };
  } catch {
    return null;
  }
}

export function readCookie(name: string): string | undefined {
  if (typeof document === "undefined") return undefined;
  const prefix = `${name}=`;
  const found = document.cookie.split("; ").find((part) => part.startsWith(prefix));
  return found ? found.slice(prefix.length) : undefined;
}

export function readConsent(): ConsentRecord | null {
  return parseConsent(readCookie(CONSENT_COOKIE));
}

function secureFlag(): string {
  return window.location.protocol === "https:" ? "; Secure" : "";
}

export function writeConsent(consent: Consent, policyVersion: string): ConsentRecord {
  const record: ConsentRecord = { v: 1, ...consent, policy: policyVersion, ts: new Date().toISOString() };
  document.cookie = `${CONSENT_COOKIE}=${encodeURIComponent(JSON.stringify(record))}; Max-Age=${CONSENT_MAX_AGE_SECONDS}; Path=/; SameSite=Lax${secureFlag()}`;
  return record;
}

export function deleteCookie(name: string): void {
  document.cookie = `${name}=; Max-Age=0; Path=/; SameSite=Lax${secureFlag()}`;
}

/** Global Privacy Control as exposed by the browser (the `Sec-GPC` header is its request-side twin). */
export function gpcActive(): boolean {
  return typeof navigator !== "undefined" && (navigator as Navigator & { globalPrivacyControl?: boolean }).globalPrivacyControl === true;
}

/** Whether the `functional` category is currently granted (the only category the attribution code needs). */
export function functionalConsentGranted(): boolean {
  return readConsent()?.functional === true;
}

export function openCookieSettings(): void {
  window.dispatchEvent(new Event(OPEN_SETTINGS_EVENT));
}
