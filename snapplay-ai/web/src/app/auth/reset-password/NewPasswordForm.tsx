"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { MIN_PASSWORD_LENGTH, PasswordField } from "@/components/PasswordField";
import { describeAuthError } from "@/lib/auth-messages";
import { createClient } from "@/lib/supabase/client";

type SessionState = "checking" | "ready" | "missing";

export function NewPasswordForm() {
  const router = useRouter();
  const [session, setSession] = useState<SessionState>("checking");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const supabase = createClient();
    let settled = false;
    const settle = (state: SessionState) => {
      if (!settled) {
        settled = true;
        setSession(state);
      }
    };
    // A session may already be in the cookie (server-side exchange) or still be arriving
    // from the URL fragment (implicit-flow link), which the client processes asynchronously.
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, current) => {
      if (current && (event === "SIGNED_IN" || event === "PASSWORD_RECOVERY" || event === "INITIAL_SESSION")) settle("ready");
    });
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) settle("ready");
    });
    const timer = window.setTimeout(() => settle("missing"), 2500);
    return () => {
      subscription.unsubscribe();
      window.clearTimeout(timer);
    };
  }, []);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Use at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    if (password !== confirm) {
      setError("The two passwords do not match.");
      return;
    }
    setSubmitting(true);
    const supabase = createClient();
    const { error: updateError } = await supabase.auth.updateUser({ password });
    if (updateError) {
      setError(describeAuthError(updateError));
      setSubmitting(false);
      return;
    }
    router.push("/account");
    router.refresh();
  }

  if (session === "checking") {
    return (
      <p className="text-sm text-ink-muted" aria-live="polite">
        Checking your reset link…
      </p>
    );
  }

  if (session === "missing") {
    return (
      <div className="space-y-4" aria-live="polite">
        <p className="alert alert-error">This reset link is invalid or has expired.</p>
        <Link href="/reset-password" className="btn btn-secondary">
          Request a new link
        </Link>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      {error && (
        <p role="alert" className="alert alert-error">
          {error}
        </p>
      )}
      <PasswordField name="password" label="New password" value={password} onChange={setPassword} autoComplete="new-password" showStrength />
      <PasswordField name="confirm" label="Repeat new password" value={confirm} onChange={setConfirm} autoComplete="new-password" />
      <button type="submit" className="btn btn-primary w-full" disabled={submitting}>
        {submitting ? "Saving…" : "Save new password"}
      </button>
    </form>
  );
}
