import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { brand } from "@/lib/brand";
import { normalizeReferralCode } from "@/lib/redirect";
import { getSessionUser } from "@/lib/supabase/server";
import { PaddleCheckout, type CheckoutParams } from "./PaddleCheckout";

export const metadata: Metadata = {
  title: "Checkout",
  robots: { index: false, follow: false },
};

const PRICE_ID = /^pri_[A-Za-z0-9]+$/;
const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const PLAN_ID = /^[a-z0-9_]{1,32}$/;

interface Query {
  price?: string;
  user_id?: string;
  plan_id?: string;
  ref?: string;
}

/**
 * Paddle's default payment link. `GET /v1/plans` builds `checkout_url` as
 * `/checkout?price=<pri_…>&user_id=<uuid>&ref=<code>&plan_id=<plan>`; the plugin opens it
 * in the system browser, where the user is not necessarily signed in to the site.
 */
export default async function CheckoutPage({ searchParams }: { searchParams: Promise<Query> }) {
  const query = await searchParams;
  const session = await getSessionUser();

  if (!brand.paddleClientToken) {
    return (
      <Shell title="Checkout is not configured">
        <p className="text-ink-muted">
          Payments are not switched on for this deployment yet. If you reached this page from the plugin, please try again
          later or contact{" "}
          <a href={`mailto:${brand.supportEmail}`} className="text-ink underline underline-offset-4">
            {brand.supportEmail}
          </a>
          .
        </p>
      </Shell>
    );
  }

  const priceId = query.price && PRICE_ID.test(query.price) ? query.price : null;
  const userId = session?.user.id ?? (query.user_id && UUID.test(query.user_id) ? query.user_id.toLowerCase() : null);
  const planId = query.plan_id && PLAN_ID.test(query.plan_id) ? query.plan_id : null;
  const ref = normalizeReferralCode(query.ref);

  if (!priceId) {
    return (
      <Shell title="This checkout link is incomplete">
        <p className="text-ink-muted">The link is missing a valid price. Pick a plan on the pricing page instead.</p>
        <Link href="/pricing" className="btn btn-primary mt-6">
          See plans
        </Link>
      </Shell>
    );
  }

  if (!userId) {
    const back = new URLSearchParams();
    back.set("price", priceId);
    if (planId) back.set("plan_id", planId);
    if (ref) back.set("ref", ref);
    redirect(`/login?next=${encodeURIComponent(`/checkout?${back.toString()}`)}`);
  }

  const params: CheckoutParams = { priceId, userId, planId, ref, email: session?.user.email ?? null };

  return (
    <Shell title="Secure checkout">
      <p className="mb-6 text-ink-muted">
        Payment is handled by {brand.merchantOfRecord}, the merchant of record. Credits land on your account within a minute
        of a successful payment.
      </p>
      <PaddleCheckout params={params} token={brand.paddleClientToken} />
    </Shell>
  );
}

function Shell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="container-narrow py-16 sm:py-24">
      <p className="eyebrow">Checkout</p>
      <h1 className="mt-3 text-3xl font-semibold tracking-tight">{title}</h1>
      <div className="card mt-8">{children}</div>
    </div>
  );
}
