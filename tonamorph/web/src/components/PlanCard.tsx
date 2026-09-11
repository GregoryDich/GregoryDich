import type { ReactNode } from "react";
import { creditsLabel, planCopy } from "@/content/pricing";
import type { Plan } from "@/lib/api";
import { formatUsd } from "@/lib/format";
import { AttributedLink } from "./AttributedLink";
import { TrackedLink } from "./TrackedLink";

export function PlanCard({ plan, action }: { plan: Plan; action: ReactNode }) {
  const copy = planCopy[plan.id];
  return (
    <div className={`card flex flex-col ${copy?.highlight ? "border-accent/60" : ""}`}>
      <p className="eyebrow">{copy?.eyebrow ?? "Plan"}</p>
      <h2 className="mt-3 text-xl font-semibold">{copy?.title ?? plan.name}</h2>
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
      <AttributedLink href="/signup" className="btn btn-primary w-full" cta="start_free" location="pricing">
        Start free
      </AttributedLink>
    );
  }
  if (!signedIn) {
    return (
      <AttributedLink
        href={`/signup?next=${encodeURIComponent("/pricing")}`}
        className="btn btn-secondary w-full"
        cta={`signup_to_buy_${plan.id}`}
        location="pricing"
      >
        Sign up to buy
      </AttributedLink>
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
    <TrackedLink href={plan.checkout_url} className="btn btn-primary w-full" cta={`checkout_${plan.id}`} location="pricing" external>
      {plan.interval ? "Subscribe" : "Buy now"}
    </TrackedLink>
  );
}
