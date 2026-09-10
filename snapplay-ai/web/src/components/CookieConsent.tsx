"use client";

import { Analytics } from "@vercel/analytics/next";
import Link from "next/link";
import Script from "next/script";
import { useEffect, useId, useState } from "react";
import { captureAttribution, clearAttribution } from "@/lib/attribution";
import { brand } from "@/lib/brand";
import {
  ALL_DENIED,
  ALL_GRANTED,
  OPEN_SETTINGS_EVENT,
  deleteCookie,
  gpcActive,
  readConsent,
  writeConsent,
  type Consent,
  type ConsentRecord,
} from "@/lib/consent";

type Mode = "hidden" | "banner" | "customise";

const CATEGORIES: { key: keyof Consent; title: string; body: string }[] = [
  {
    key: "functional",
    title: "Functional",
    body: "Remembers a referral code (`ref`, 30 days) so the person who sent you here gets credit when you sign up.",
  },
  {
    key: "analytics",
    title: "Analytics",
    body: "Cookieless page-view counting (Vercel Web Analytics). Nothing is stored on your device.",
  },
  {
    key: "marketing",
    title: "Marketing",
    body: "Loads Klaviyo, which sets `__kla_id` (up to 2 years) to connect your visits with the emails you asked for.",
  },
];

/**
 * Consent banner and the scripts it gates. Also mounts Vercel Web Analytics (cookieless)
 * unless the visitor has switched the analytics category off.
 */
export function CookieConsent() {
  const [record, setRecord] = useState<ConsentRecord | null>(null);
  const [mode, setMode] = useState<Mode>("hidden");
  const [draft, setDraft] = useState<Consent>(ALL_DENIED);
  const [gpc, setGpc] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const headingId = useId();

  useEffect(() => {
    const stored = readConsent();
    const signal = gpcActive();
    setRecord(stored);
    setGpc(signal);
    setLoaded(true);
    if (!stored) setMode("banner");
    const open = () => {
      setDraft(readConsent() ?? { ...ALL_DENIED, marketing: false });
      setMode("customise");
    };
    window.addEventListener(OPEN_SETTINGS_EVENT, open);
    return () => window.removeEventListener(OPEN_SETTINGS_EVENT, open);
  }, []);

  function save(consent: Consent) {
    const next = writeConsent(consent, brand.legalEffectiveDate);
    setRecord(next);
    setMode("hidden");
    if (consent.functional) {
      captureAttribution(window.location.search);
    } else {
      clearAttribution();
    }
    if (!consent.marketing) deleteCookie("__kla_id");
  }

  // Before any explicit choice a GPC signal means "no marketing cookies".
  const marketingAllowed = record ? record.marketing : false;
  const analyticsAllowed = record ? record.analytics : true;
  const klaviyoId = brand.klaviyoCompanyId;

  return (
    <>
      {loaded && analyticsAllowed && <Analytics />}
      {loaded && marketingAllowed && klaviyoId && (
        <Script src={`https://static.klaviyo.com/onsite/js/${encodeURIComponent(klaviyoId)}/klaviyo.js`} strategy="afterInteractive" />
      )}

      {mode !== "hidden" && (
        <section
          role="dialog"
          aria-modal="false"
          aria-labelledby={headingId}
          className="fixed inset-x-4 bottom-4 z-50 mx-auto max-w-xl rounded-xl border border-line bg-surface p-5 shadow-2xl shadow-black/60"
        >
          <h2 id={headingId} className="text-base font-semibold">
            Cookies
          </h2>
          <p className="mt-2 text-sm text-ink-muted">
            Strictly necessary cookies keep you signed in and remember this choice. Everything else is off until you say
            otherwise. Details in the{" "}
            <Link href="/legal/cookies" className="text-ink underline underline-offset-4">
              cookie policy
            </Link>
            .
          </p>
          {gpc && !record && (
            <p className="mt-2 text-xs text-ink-dim">Your browser sends a Global Privacy Control signal, so marketing cookies stay off unless you turn them on here.</p>
          )}

          {mode === "customise" && (
            <ul className="mt-4 space-y-3">
              {CATEGORIES.map((category) => (
                <li key={category.key} className="flex items-start gap-3 rounded-md border border-line p-3">
                  <input
                    id={`${headingId}-${category.key}`}
                    type="checkbox"
                    className="mt-1 h-4 w-4 accent-accent"
                    checked={draft[category.key]}
                    onChange={(event) => setDraft({ ...draft, [category.key]: event.target.checked })}
                  />
                  <label htmlFor={`${headingId}-${category.key}`} className="text-sm">
                    <span className="font-medium">{category.title}</span>
                    <span className="mt-0.5 block text-ink-muted">{category.body}</span>
                  </label>
                </li>
              ))}
            </ul>
          )}

          <div className="mt-4 flex flex-wrap gap-2">
            <button type="button" className="btn btn-primary" onClick={() => save(ALL_GRANTED)}>
              Accept all
            </button>
            <button type="button" className="btn btn-secondary" onClick={() => save(ALL_DENIED)}>
              Reject all
            </button>
            {mode === "banner" ? (
              <button type="button" className="btn btn-ghost" onClick={() => setMode("customise")}>
                Customise
              </button>
            ) : (
              <button type="button" className="btn btn-secondary" onClick={() => save(draft)}>
                Save choices
              </button>
            )}
          </div>
        </section>
      )}
    </>
  );
}
