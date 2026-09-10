/** Human-readable messages for auth outcomes, keyed by the `error` query parameter. */
export const AUTH_ERROR_MESSAGES: Record<string, string> = {
  confirm_failed: "That confirmation link is invalid or has already been used. Log in, or sign up again to get a new one.",
  link_expired: "That password reset link is invalid or has expired. Request a new one below.",
  session_expired: "Your session has expired. Log in again.",
};

export function authErrorMessage(code: string | undefined): string | null {
  if (!code) return null;
  return AUTH_ERROR_MESSAGES[code] ?? null;
}

/**
 * Maps a Supabase Auth error to the same wording the API's `/v1/auth/*` routes produce
 * (409 conflict, 422 validation_error, 429 rate_limited), so both entry points feel alike.
 */
export function describeAuthError(error: { code?: string; status?: number; message: string }): string {
  switch (error.code) {
    case "user_already_exists":
    case "email_exists":
      return "An account with this email already exists. Log in, or reset your password.";
    case "weak_password":
      return error.message || "That password is too weak.";
    case "validation_failed":
    case "email_address_invalid":
      return error.message || "Check the email address and try again.";
    case "invalid_credentials":
      return "Incorrect email or password.";
    case "email_not_confirmed":
      return "Confirm your email address first — check your inbox for the confirmation link.";
    case "same_password":
      return "Choose a password you have not used before.";
    case "over_request_rate_limit":
    case "over_email_send_rate_limit":
      return "Too many attempts. Wait a few minutes and try again.";
    default:
      if (error.status === 429) return "Too many attempts. Wait a few minutes and try again.";
      if (error.status === 422) return error.message;
      return error.message || "Something went wrong. Try again.";
  }
}
