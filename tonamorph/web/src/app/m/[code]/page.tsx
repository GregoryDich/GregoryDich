import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { AttributedLink } from "@/components/AttributedLink";
import { DemoVideo } from "@/components/DemoVideo";
import { HowItWorksSteps } from "@/components/HowItWorksSteps";
import { PRODUCT_PROMISE } from "@/content/landing";
import { REFERRAL_COPY } from "@/content/referral";
import { brand } from "@/lib/brand";
import { parseUserReferralCode, referralSignupHref } from "@/lib/referral";

type Params = Promise<{ code: string }>;

/**
 * Referral landing, `/m/<code>` — the link the share button hands out (contract §1
 * `referral.url`). The code is checked for shape only; whether it is live is decided by the
 * database at sign-up, where an unknown code never fails the sign-up. Personal links: never
 * indexed, never in the sitemap.
 */
async function codeFrom(params: Params): Promise<string> {
  const code = parseUserReferralCode((await params).code);
  if (!code) notFound();
  return code;
}

export async function generateMetadata({ params }: { params: Params }): Promise<Metadata> {
  await codeFrom(params);
  const title = `${REFERRAL_COPY.title} · ${brand.productName}`;
  const description = `${PRODUCT_PROMISE} ${REFERRAL_COPY.terms}`;
  return {
    title: REFERRAL_COPY.title,
    description,
    robots: { index: false, follow: false },
    openGraph: { type: "website", siteName: brand.productName, title, description },
    twitter: { card: "summary_large_image", title, description },
  };
}

export default async function ReferralPage({ params }: { params: Params }) {
  const code = await codeFrom(params);
  return (
    <div className="container-page py-16 sm:py-24">
      <div className="max-w-3xl">
        <p className="eyebrow">{REFERRAL_COPY.eyebrow}</p>
        <h1 className="mt-4 text-4xl font-semibold tracking-tight text-balance sm:text-6xl">{REFERRAL_COPY.headline}</h1>
        <p className="mt-6 max-w-2xl text-lg text-ink-muted">{PRODUCT_PROMISE}</p>
        <div className="mt-8 flex flex-wrap items-center gap-3">
          <AttributedLink href={referralSignupHref(code)} className="btn btn-primary btn-lg" cta="claim_referral" location="referral">
            {REFERRAL_COPY.cta}
          </AttributedLink>
        </div>
        <p className="mt-3 text-sm text-ink-dim">{REFERRAL_COPY.terms}</p>
      </div>
      <div className="mt-14">
        <DemoVideo />
      </div>
      <section className="mt-16 sm:mt-24" aria-labelledby="how">
        <p className="eyebrow">How it works</p>
        <h2 id="how" className="mt-3 text-3xl font-semibold tracking-tight sm:text-4xl">
          Drop. Play. Drag.
        </h2>
        <HowItWorksSteps />
      </section>
    </div>
  );
}
