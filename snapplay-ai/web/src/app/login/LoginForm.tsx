"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";
import { PasswordField } from "@/components/PasswordField";
import { describeAuthError } from "@/lib/auth-messages";
import { createClient } from "@/lib/supabase/client";

export function LoginForm({ next, initialError }: { next: string; initialError: string | null }) {
  const router = useRouter();
  const emailId = useId();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(initialError);
  const [unconfirmed, setUnconfirmed] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    // Confirmation links sent without PKCE (e.g. accounts created from inside the plugin)
    // arrive with the session in the URL fragment; the browser client consumes it here.
    if (!window.location.hash.includes("access_token=")) return;
    const supabase = createClient();
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_IN") {
        router.replace(next);
        router.refresh();
      }
    });
    return () => subscription.unsubscribe();
  }, [next, router]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    setUnconfirmed(false);
    setSubmitting(true);
    const supabase = createClient();
    const { error: signInError } = await supabase.auth.signInWithPassword({ email, password });
    if (signInError) {
      setError(describeAuthError(signInError));
      setUnconfirmed(signInError.code === "email_not_confirmed");
      setSubmitting(false);
      return;
    }
    router.push(next);
    router.refresh();
  }

  async function resendConfirmation() {
    const supabase = createClient();
    const { error: resendError } = await supabase.auth.resend({
      type: "signup",
      email,
      options: { emailRedirectTo: `${window.location.origin}/auth/confirm` },
    });
    setNotice(resendError ? describeAuthError(resendError) : "Confirmation email sent.");
  }

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      {error && (
        <div role="alert" className="alert alert-error space-y-2">
          <p>{error}</p>
          {unconfirmed && (
            <button type="button" className="text-ink underline underline-offset-4" onClick={resendConfirmation}>
              Resend the confirmation email
            </button>
          )}
        </div>
      )}
      {notice && (
        <p role="status" className="alert alert-success">
          {notice}
        </p>
      )}
      <div>
        <label htmlFor={emailId} className="label">
          Email
        </label>
        <input
          id={emailId}
          name="email"
          type="email"
          className="input"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </div>
      <PasswordField name="password" label="Password" value={password} onChange={setPassword} autoComplete="current-password" />
      <div className="flex items-center justify-between text-sm">
        <Link href="/reset-password" className="text-ink-muted underline underline-offset-4 hover:text-ink">
          Forgot password?
        </Link>
      </div>
      <button type="submit" className="btn btn-primary w-full" disabled={submitting}>
        {submitting ? "Logging in…" : "Log in"}
      </button>
      <p className="text-center text-sm text-ink-muted">
        New here?{" "}
        <Link href={next === "/account" ? "/signup" : `/signup?next=${encodeURIComponent(next)}`} className="text-ink underline underline-offset-4">
          Create an account
        </Link>
      </p>
    </form>
  );
}
