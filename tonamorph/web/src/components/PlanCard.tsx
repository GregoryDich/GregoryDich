import Link from "next/link";
import type { ReactNode } from "react";
import { creditsLabel, planCopy } from "@/content/pricing";
import type { Plan } from "@/lib/api";
import { formatUsd } from "@/lib/format";

export function PlanCard({ plan, action }: { plan: Plan; action: ReactNode }) {
  const copy = planCopy[plan.id];
  return (
    <div className={`card flex flex-col ${copy?.highlight ? "border-accent/60" : ""}`}>
      <p className="eyebrow">{copy?.eyebrow ?? "Plan"}</p>
      <h2 className="mt-3 text-xl font-semibold">{plan.name}</h2>
      <p className="mt-4 text-4xl font-semibold tracking-tight">
        {formatUsd(plan.price_usd)}
        {plan.interval && <span className="text-base font-normal text-ink-dim"> / {plan.interval}</span>}
      </p>
      <p className="mt-1 text-sm text-ink-muted">{creditsLabel(plan)}</p>
      {copy && <p className="mt-4 text-sm text-ink-muted">{copy.summary}</p>}
      {copy && (
        <ul className="mt-5 space-y-2 text-sm">
          {copy.bullets.map((bullet) => (
            <li key={bullet} className="flex gap-2.5">
              <span aria-hidden="true" className="text-accent">
                ✓
              </span>
              <span>{bullet}</span>
            </li>
          ))}
        </ul>
      )}
      <div className="mt-8 flex-1" />
      <div>{action}</div>
    </div>
  );
}

export function PlanAction({ plan, signedIn }: { plan: Plan; signedIn: boolean }) {
  if (plan.id === "free") {
    return signedIn ? (
      <span className="btn btn-secondary w-full cursor-default">Included with your account</span>
    ) : (
      <Link href="/signup" className="btn btn-primary w-full">
        Start free
      </Link>
    );
  }
  if (!signedIn) {
    return (
      <Link href={`/signup?next=${encodeURIComponent("/pricing")}`} className="btn btn-secondary w-full">
        Sign up to buy
      </Link>
    );
  }
  if (!plan.checkout_url) {
    return (
      <span className="btn btn-secondary w-full cursor-not-allowed opacity-60" aria-disabled="true">
        Checkout not available yet
      </span>
    );
  }
  return (
    <a href={plan.checkout_url} className="btn btn-primary w-full" rel="noopener">
      {plan.interval ? "Subscribe" : "Buy now"}
    </a>
  );
}
