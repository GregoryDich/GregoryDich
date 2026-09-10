"use client";

import { useId, useState } from "react";
import { describeAuthError } from "@/lib/auth-messages";
import { createClient } from "@/lib/supabase/client";

export function ResetRequestForm() {
  const emailId = useId();
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    const supabase = createClient();
    const { error: resetError } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/reset-password`,
    });
    // Unknown addresses are not revealed; only rate limiting is surfaced.
    if (resetError && (resetError.status === 429 || resetError.code?.startsWith("over_"))) {
      setError(describeAuthError(resetError));
      setSubmitting(false);
      return;
    }
    setSent(true);
  }

  if (sent) {
    return (
      <p className="text-sm text-ink-muted" aria-live="polite">
        If an account exists for <span className="text-ink">{email}</span>, a reset link is on its way. It is valid for a short
        time, so open it soon.
      </p>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-5" noValidate>
      {error && (
        <p role="alert" className="alert alert-error">
          {error}
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
      <button type="submit" className="btn btn-primary w-full" disabled={submitting}>
        {submitting ? "Sending…" : "Send reset link"}
      </button>
    </form>
  );
}
