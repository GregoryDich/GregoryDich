"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";
import { MIN_PASSWORD_LENGTH, PasswordField } from "@/components/PasswordField";
import { attributionFromSearch, readAttribution, type Attribution } from "@/lib/attribution";
import { describeAuthError } from "@/lib/auth-messages";
import { createClient } from "@/lib/supabase/client";

type Status = "idle" | "submitting" | "sent";

export function SignupForm({ loginHref }: { loginHref: string }) {
  const router = useRouter();
  const ids = { email: useId(), agree: useId(), marketing: useId() };
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [agree, setAgree] = useState(false);
  const [marketing, setMarketing] = useState(false);
  const [attribution, setAttribution] = useState<Attribution>({});
  const [status, setStatus] = useState<Status>("idle");
  const [error, setError] = useState<string | null>(null);
  const [resent, setResent] = useState<string | null>(null);

  useEffect(() => {
    // URL parameters win over what an earlier visit stored.
    setAttribution({ ...readAttribution(), ...attributionFromSearch(window.location.search) });
  }, []);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    if (!agree) {
      setError("You need to agree to the Terms and the Privacy Policy to create an account.");
      return;
    }
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Use at least ${MIN_PASSWORD_LENGTH} characters for your password.`);
      return;
    }
    setStatus("submitting");
    const supabase = createClient();
    const { data, error: signUpError } = await supabase.auth.signUp({
      email,
      password,
      options: {
        emailRedirectTo: `${window.location.origin}/auth/confirm`,
        data: {
          referral_code: attribution.referral_code ?? null,
          marketing_opt_in: marketing,
          terms_accepted_at: new Date().toISOString(),
          utm_source: attribution.utm_source ?? null,
          utm_medium: attribution.utm_medium ?? null,
          utm_campaign: attribution.utm_campaign ?? null,
          utm_content: attribution.utm_content ?? null,
          utm_term: attribution.utm_term ?? null,
        },
      },
    });
    if (signUpError) {
      setError(describeAuthError(signUpError));
      setStatus("idle");
      return;
    }
    if (data.session) {
      // Email confirmation is disabled on this project: the account is live immediately.
      router.push("/account?welcome=1");
      router.refresh();
      return;
    }
    // With confirmation enabled, an existing address also lands here (identities is empty)
    // so that the form does not reveal which emails are registered.
    setStatus("sent");
  }

  async function resend() {
    setResent(null);
    const supabase = createClient();
    const { error: resendError } = await supabase.auth.resend({
      type: "signup",
      email,
      options: { emailRedirectTo: `${window.location.origin}/auth/confirm` },
    });
    setResent(resendError ? describeAuthError(resendError) : "Sent. Give it a minute and check your spam folder too.");
  }

  if (status === "sent") {
    return (
      <div className="space-y-4" aria-live="polite">
        <h2 className="text-xl font-semibold">Check your email</h2>
        <p className="text-sm text-ink-muted">
          We sent a confirmation link to <span className="text-ink">{email}</span>. Open it to activate your account and your
          3 free credits.
        </p>
        <p className="text-sm text-ink-muted">
          Already had an account with this address? The email will say so — just{" "}
          <Link href={loginHref} className="text-ink underline underline-offset-4">
            log in
          </Link>{" "}
          instead.
        </p>
        <div className="flex flex-wrap items-center gap-3 pt-2">
          <button type="button" className="btn btn-secondary" onClick={resend}>
            Resend the email
          </button>
          {resent && <span className="text-sm text-ink-muted">{resent}</span>}
        </div>
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
      <div>
        <label htmlFor={ids.email} className="label">
          Email
        </label>
        <input
          id={ids.email}
          name="email"
          type="email"
          className="input"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
      </div>
      <PasswordField name="password" label="Password" value={password} onChange={setPassword} autoComplete="new-password" showStrength />
      <input type="hidden" name="referral_code" value={attribution.referral_code ?? ""} />
      <div className="space-y-3 text-sm">
        <label htmlFor={ids.agree} className="flex items-start gap-3">
          <input
            id={ids.agree}
            name="agree"
            type="checkbox"
            className="mt-1 h-4 w-4 accent-accent"
            checked={agree}
            onChange={(event) => setAgree(event.target.checked)}
            required
          />
          <span className="text-ink-muted">
            I agree to the{" "}
            <Link href="/legal/terms" className="text-ink underline underline-offset-4" target="_blank">
              Terms of Service
            </Link>{" "}
            and the{" "}
            <Link href="/legal/privacy" className="text-ink underline underline-offset-4" target="_blank">
              Privacy Policy
            </Link>
            .
          </span>
        </label>
        <label htmlFor={ids.marketing} className="flex items-start gap-3">
          <input
            id={ids.marketing}
            name="marketing_opt_in"
            type="checkbox"
            className="mt-1 h-4 w-4 accent-accent"
            checked={marketing}
            onChange={(event) => setMarketing(event.target.checked)}
          />
          <span className="text-ink-muted">Email me product updates and tips. Optional; unsubscribe any time.</span>
        </label>
      </div>
      <button type="submit" className="btn btn-primary w-full" disabled={status === "submitting"}>
        {status === "submitting" ? "Creating account…" : "Create account"}
      </button>
      <p className="text-center text-sm text-ink-muted">
        Already have an account?{" "}
        <Link href={loginHref} className="text-ink underline underline-offset-4">
          Log in
        </Link>
      </p>
    </form>
  );
}
