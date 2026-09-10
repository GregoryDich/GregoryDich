import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";
import { redirect } from "next/navigation";
import { planOrder } from "@/content/pricing";
import { api, attempt, type ApiError, type Attempt, type JobSummary, type Plan } from "@/lib/api";
import { REF_COOKIE } from "@/lib/attribution";
import { brand } from "@/lib/brand";
import { formatDateTime, formatSeconds, formatUsd } from "@/lib/format";
import { normalizeReferralCode } from "@/lib/redirect";
import { getSessionUser } from "@/lib/supabase/server";
import { ApiKeysPanel } from "./ApiKeysPanel";

export const metadata: Metadata = {
  title: "Account",
  robots: { index: false, follow: false },
};

const PLAN_LABELS: Record<string, string> = { free: "Free", credits: "Credit pack", subscription: "Pro Monthly" };

const STATUS_STYLES: Record<JobSummary["status"], string> = {
  queued: "text-ink-muted",
  running: "text-accent",
  succeeded: "text-success",
  failed: "text-danger",
  cancelled: "text-ink-dim",
};

function errorText(error: ApiError, subject: string): string {
  if (error.code === "api_not_configured") return `${subject} is unavailable: the API URL is not configured.`;
  if (error.code === "network_error") return `${subject} could not be loaded: the API is unreachable.`;
  if (error.status === 401) return `${subject} could not be loaded: your session was rejected by the API. Log out and in again.`;
  return `${subject} could not be loaded (${error.code}).`;
}

function notConfigured<T>(): Attempt<T> {
  return { ok: false, error: { name: "ApiError", status: 0, code: "api_not_configured", message: "", details: null, isNotFound: false } as ApiError };
}

export default async function AccountPage({ searchParams }: { searchParams: Promise<{ welcome?: string; email?: string; purchase?: string }> }) {
  const { welcome, email: emailParam, purchase } = await searchParams;
  const session = await getSessionUser();
  if (!session) redirect("/login?next=%2Faccount");
  const { user, accessToken } = session;

  const cookieStore = await cookies();
  const ref = normalizeReferralCode(cookieStore.get(REF_COOKIE)?.value);

  const [me, plans, jobs, keys] = brand.apiUrl
    ? await Promise.all([
        attempt(() => api.getMe(accessToken)),
        attempt(() => api.getPlans({ token: accessToken, ref })),
        attempt(() => api.listJobs(accessToken, 20)),
        attempt(() => api.listApiKeys(accessToken)),
      ])
    : [notConfigured<Awaited<ReturnType<typeof api.getMe>>>(), notConfigured<Plan[]>(), notConfigured<Awaited<ReturnType<typeof api.listJobs>>>(), notConfigured<Awaited<ReturnType<typeof api.listApiKeys>>>()];

  const paidPlans = plans.ok ? plans.data.filter((plan) => plan.id !== "free").sort((a, b) => planOrder.indexOf(a.id) - planOrder.indexOf(b.id)) : [];
  const jobList = jobs.ok ? jobs.data.jobs : [];
  const keyList = keys.ok ? keys.data.keys : [];
  const keysError = keys.ok || keys.error.isNotFound ? null : errorText(keys.error, "API keys");
  const email = me.ok ? me.data.user.email : (user.email ?? "");
  const deleteHref = `mailto:${brand.supportEmail}?subject=${encodeURIComponent("Delete my account")}&body=${encodeURIComponent(
    `Please delete the ${brand.productName} account for ${email} (user id ${user.id}) and all data associated with it.`,
  )}`;

  return (
    <div className="container-page py-12 sm:py-16">
      {welcome === "1" && (
        <p role="status" className="alert alert-success mb-8">
          Your account is confirmed and your 3 free credits are ready. Install the plugin and sign in inside it to start.
        </p>
      )}
      {emailParam === "changed" && (
        <p role="status" className="alert alert-success mb-8">
          Your email address has been updated.
        </p>
      )}
      {purchase === "success" && (
        <p role="status" className="alert alert-success mb-8">
          Payment received. Your credits arrive as soon as {brand.merchantOfRecord} confirms the transaction — usually within a
          minute. Reload this page to see the new balance.
        </p>
      )}

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="eyebrow">Account</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight">{email}</h1>
          {me.ok && <p className="mt-1 text-sm text-ink-muted">Plan: {PLAN_LABELS[me.data.user.plan] ?? me.data.user.plan}</p>}
        </div>
        <form action="/auth/signout" method="post">
          <button type="submit" className="btn btn-secondary">
            Sign out
          </button>
        </form>
      </div>

      <div className="mt-10 grid gap-6 lg:grid-cols-[1.2fr_1fr]">
        <section className="card" aria-labelledby="balance">
          <h2 id="balance" className="text-lg font-semibold">
            Credits
          </h2>
          {me.ok ? (
            <>
              <p className="mt-4 text-5xl font-semibold tracking-tight">
                {me.data.balance.available}
                <span className="ml-2 text-base font-normal text-ink-muted">available</span>
              </p>
              <dl className="mt-4 grid grid-cols-2 gap-4 text-sm">
                <div>
                  <dt className="text-ink-dim">Total</dt>
                  <dd>{me.data.balance.credits}</dd>
                </div>
                <div>
                  <dt className="text-ink-dim">Reserved by running jobs</dt>
                  <dd>{me.data.balance.reserved}</dd>
                </div>
                {me.data.balance.subscription_renews_at && (
                  <div className="col-span-2">
                    <dt className="text-ink-dim">Subscription renews</dt>
                    <dd>{formatDateTime(me.data.balance.subscription_renews_at)}</dd>
                  </div>
                )}
              </dl>
              <p className="mt-4 text-xs text-ink-dim">
                Monthly credits are spent first and expire at the end of the billing period; pack credits never expire.
              </p>
            </>
          ) : (
            <p className="alert alert-info mt-4">{errorText(me.error, "Your balance")}</p>
          )}
        </section>

        <section className="card" aria-labelledby="buy">
          <h2 id="buy" className="text-lg font-semibold">
            Add credits
          </h2>
          {plans.ok ? (
            <ul className="mt-4 space-y-3">
              {paidPlans.map((plan) => (
                <li key={plan.id} className="flex items-center justify-between gap-4 rounded-md border border-line p-3">
                  <div>
                    <p className="font-medium">{plan.name}</p>
                    <p className="text-sm text-ink-muted">
                      {plan.credits} credits{plan.interval ? ` / ${plan.interval}` : ""} · {formatUsd(plan.price_usd)}
                    </p>
                  </div>
                  {plan.checkout_url ? (
                    <a href={plan.checkout_url} className="btn btn-primary" rel="noopener">
                      {plan.interval ? "Subscribe" : "Buy"}
                    </a>
                  ) : (
                    <span className="text-xs text-ink-dim">Not available yet</span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <p className="alert alert-info mt-4">{errorText(plans.error, "Plans")}</p>
          )}
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            {brand.billingPortalUrl && (
              <a href={brand.billingPortalUrl} className="text-ink underline underline-offset-4" rel="noopener">
                Manage subscription
              </a>
            )}
            <Link href="/pricing" className="text-ink-muted underline underline-offset-4 hover:text-ink">
              Compare plans
            </Link>
          </div>
        </section>
      </div>

      <section className="card mt-6" aria-labelledby="jobs">
        <h2 id="jobs" className="text-lg font-semibold">
          Recent jobs
        </h2>
        {jobs.ok || jobs.error.isNotFound ? (
          jobList.length === 0 ? (
            <p className="mt-4 text-sm text-ink-muted">
              No jobs yet. Drop a clip on the plugin and it will show up here.{" "}
              <Link href="/download" className="text-ink underline underline-offset-4">
                Get the plugin
              </Link>
              .
            </p>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-ink-dim uppercase">
                  <tr>
                    <th className="py-2 pr-4 font-medium">Created</th>
                    <th className="py-2 pr-4 font-medium">Status</th>
                    <th className="py-2 pr-4 font-medium">Duration</th>
                    <th className="py-2 font-medium">Credits</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line">
                  {jobList.map((job) => (
                    <tr key={job.job_id}>
                      <td className="py-3 pr-4 text-ink-muted">{formatDateTime(job.created_at)}</td>
                      <td className={`py-3 pr-4 capitalize ${STATUS_STYLES[job.status]}`}>
                        {job.status}
                        {job.status === "failed" && job.error && <span className="ml-2 text-xs text-ink-dim">{job.error.message}</span>}
                      </td>
                      <td className="py-3 pr-4 text-ink-muted">{formatSeconds(job.result?.input?.duration_seconds)}</td>
                      <td className="py-3">{job.result ? job.result.credits_charged : job.status === "failed" || job.status === "cancelled" ? 0 : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : (
          <p className="alert alert-info mt-4">{errorText(jobs.error, "Job history")}</p>
        )}
      </section>

      <section className="card mt-6" aria-labelledby="keys">
        <h2 id="keys" className="text-lg font-semibold">
          API keys
        </h2>
        <p className="mt-1 text-sm text-ink-muted">
          For scripts and CI. Keys use your credits and the same rate limits as the plugin; they cannot manage other keys.
        </p>
        <div className="mt-5">
          <ApiKeysPanel keys={keyList} listError={keysError} />
        </div>
      </section>

      <section className="card mt-6 border-danger/30" aria-labelledby="danger">
        <h2 id="danger" className="text-lg font-semibold">
          Delete account
        </h2>
        <p className="mt-1 text-sm text-ink-muted">
          There is no self-service deletion yet. Email support from the address on this account and we will remove the
          account, its credits and any remaining data. Unused purchased credits are handled under the refund policy.
        </p>
        <a href={deleteHref} className="btn btn-danger mt-4">
          Request deletion by email
        </a>
      </section>
    </div>
  );
}
