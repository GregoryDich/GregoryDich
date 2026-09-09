/**
 * Validates a `next` redirect target. Only same-origin, absolute-path relative URLs are
 * accepted: they must start with a single `/`, may not start with `//` or `/\` (protocol-
 * relative), and may not contain control characters or a scheme.
 */
export function safeNext(value: string | null | undefined, fallback = "/account"): string {
  if (!value) return fallback;
  if (value.length > 512) return fallback;
  if (!value.startsWith("/")) return fallback;
  if (value.startsWith("//") || value.startsWith("/\\")) return fallback;
  if (/[\u0000-\u001f\u007f]/.test(value)) return fallback;
  if (/^\/[^/?#]*:/.test(value)) return fallback;
  return value;
}

/** Affiliate/referral code as accepted by `GET /v1/plans?ref=` (contract §3). */
export const REFERRAL_CODE_PATTERN = /^[A-Za-z0-9_-]{1,64}$/;

export function normalizeReferralCode(value: string | null | undefined): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  return REFERRAL_CODE_PATTERN.test(trimmed) ? trimmed : null;
}
