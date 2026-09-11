import type { Metadata } from "next";
import { cookies } from "next/headers";
import Link from "next/link";
import { PlanAction, PlanCard } from "@/components/PlanCard";
import { PricingViewTracker } from "@/components/PricingViewTracker";
import { MORPH_GUARANTEE, PRICING_HEADLINE, PRICING_SUBHEAD, planOrder, staticPlans } from "@/content/pricing";
import { api, attempt, type Plan } from "@/lib/api";
import { REF_COOKIE } from "@/lib/attribution";
import { brand } from "@/lib/brand";
import { normalizeReferralCode } from "@/lib/redirect";
import { getSessionUser } from "@/lib/supabase/server";

export const metadata: Metadata = {
  title: "Pricing",
  description: `${brand.productName} pricing: 3 free morphs at signup, 50 morphs for $9 that never expire, or 60 morphs a month for $7.99. One morph is one clip up to 60 s.`,
};

function sortPlans(plans: Plan[]): Plan[] {
  return [...plans].sort((a, b) => planOrder.indexOf(a.id) - planOrder.indexOf(b.id));
}

export default async function PricingPage() {
  const session = await getSessionUser();
  const cookieStore = await cookies();
  const ref = normalizeReferralCode(cookieStore.get(REF_COOKIE)?.value);

  let plans = staticPlans;
  let live = false;
  if (brand.apiUrl) {
    const result = await attempt(() => api.getPlans({ token: session?.accessToken, ref }));
    if (result.ok && result.data.length > 0) {
      plans = result.data;
      live = true;
    }
  }

  return (
    <div className="container-page py-16 sm:py-24">
      <PricingViewTracker />
      <div className="max-w-3xl">
        <p className="eyebrow">Pricing</p>
        <h1 className="mt-3 text-4xl font-semibold tracking-tight text-balance sm:text-5xl">{PRICING_HEADLINE}</h1>
        <p className="mt-4 text-lg text-ink-muted">{PRICING_SUBHEAD}</p>
      </div>

      <div className="mt-12 grid gap-4 md:grid-cols-3">
        {sortPlans(plans).map((plan) => (
          <PlanCard key={plan.id} plan={plan} action={<PlanAction plan={plan} signedIn={Boolean(session)} />} />
        ))}
      </div>

      <div className="card mt-10 border-accent/40">
        <p className="eyebrow">Guarantee</p>
        <p className="mt-2 text-xl font-medium">{MORPH_GUARANTEE}</p>
        <p className="mt-2 text-sm text-ink-muted">
          A failed morph is never charged; the credit comes back automatically. For a morph that finished but is unusable,
          write to{" "}
          <a href={`mailto:${brand.supportEmail}`} className="text-ink underline underline-offset-4">
            {brand.supportEmail}
          </a>{" "}
          and it goes back on your balance.
        </p>
      </div>

      <div className="mt-10 grid gap-6 text-sm text-ink-muted md:grid-cols-2">
        <p>
          Subscription morphs are spent before pack morphs and reset at the end of each billing period; pack morphs never
          expire. A cancelled subscription keeps its remaining morphs until the period ends. Both buttons open checkout; the
          plugin updates your balance itself.
        </p>
        <p>
          Purchases are processed by {brand.merchantOfRecord} as merchant of record. See the{" "}
          <Link href="/legal/refunds" className="text-ink underline underline-offset-4">
            refund policy
          </Link>{" "}
          and the{" "}
          <Link href="/legal/terms" className="text-ink underline underline-offset-4">
            terms
          </Link>
          .{!live && " Prices shown are list prices; checkout opens after you sign in."}
        </p>
      </div>
    </div>
  );
}
