import { authErrorMessage } from "@/lib/auth-messages";

/** Shown by the auth forms while the Supabase settings are absent (pre-launch previews). */
export function AuthUnavailable() {
  return (
    <p role="status" className="rounded-md border border-neutral-700 bg-neutral-900/60 p-4 text-sm text-neutral-300">
      {authErrorMessage("auth_unavailable")}
    </p>
  );
}
