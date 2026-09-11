/**
 * "Send a morph to a friend" (contract §1 `referral`, §3 earned morphs): every account owns
 * an 8-character code drawn from an alphabet without 0/O and 1/I/L, shared as `/m/<code>`.
 * Input is case-insensitive; the canonical spelling is upper case. Distinct from the
 * affiliate codes accepted by `normalizeReferralCode` (`GET /v1/plans?ref=`).
 */
export const USER_REFERRAL_CODE_PATTERN = /^[ABCDEFGHJKMNPQRSTUVWXYZ23456789]{8}$/;

/** The canonical code, or null when the value is not shaped like one (no lookup is made). */
export function parseUserReferralCode(value: string | null | undefined): string | null {
  if (!value) return null;
  const code = value.trim().toUpperCase();
  return USER_REFERRAL_CODE_PATTERN.test(code) ? code : null;
}

/**
 * Sign-up link for a validated code. The code travels in the URL because the `ref` cookie
 * is written only after functional consent; the sign-up form reads `?ref=` and stores it
 * as the `referral_code` metadata (see SignupForm and lib/attribution).
 */
export function referralSignupHref(code: string): string {
  return `/signup?ref=${code}`;
}
