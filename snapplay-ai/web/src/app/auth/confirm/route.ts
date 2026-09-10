import type { EmailOtpType } from "@supabase/supabase-js";
import { redirect } from "next/navigation";
import type { NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";

const OTP_TYPES: readonly EmailOtpType[] = ["signup", "invite", "magiclink", "recovery", "email_change", "email"];

function isOtpType(value: string | null): value is EmailOtpType {
  return value !== null && (OTP_TYPES as readonly string[]).includes(value);
}

// Each Supabase email template hard-codes its `type`: signup | email | magiclink → welcome,
// recovery → new password, email_change → account notice.
function destination(type: string | null): string {
  if (type === "recovery") return "/auth/reset-password";
  if (type === "email_change") return "/account?email=changed";
  return "/account?welcome=1";
}

function failure(type: string | null): string {
  return type === "recovery" ? "/reset-password?error=link_expired" : "/login?error=confirm_failed";
}

/**
 * Email link landing. Handles the custom template form (`?token_hash=…&type=…`) and the
 * default PKCE form (`?code=…`), establishes the cookie session and redirects by purpose.
 */
export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const tokenHash = params.get("token_hash");
  const type = params.get("type");
  const code = params.get("code");

  if (tokenHash && isOtpType(type)) {
    const supabase = await createClient();
    const { error } = await supabase.auth.verifyOtp({ type, token_hash: tokenHash });
    redirect(error ? failure(type) : destination(type));
  }

  if (code) {
    const supabase = await createClient();
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    redirect(error ? failure(type) : destination(type));
  }

  // Implicit-flow links carry the session in the URL fragment, which the browser keeps
  // across this redirect; the login page consumes it and continues to the account.
  redirect(`/login?next=${encodeURIComponent("/account?welcome=1")}`);
}
