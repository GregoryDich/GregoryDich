"use client";

import Link from "next/link";
import Script from "next/script";
import { useEffect, useState } from "react";
import { brand } from "@/lib/brand";

const STORAGE_KEY = "cookie-consent";
type Consent = "granted" | "denied" | null;

/**
 * Consent banner for the only optional third-party script (Klaviyo). Vercel Web Analytics
 * is cookieless and always on. With no Klaviyo id there is nothing to gate, so nothing renders.
 */
export function CookieConsent() {
  const [consent, setConsent] = useState<Consent | "unknown">("unknown");

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem(STORAGE_KEY);
      setConsent(stored === "granted" || stored === "denied" ? stored : null);
    } catch {
      setConsent(null);
    }
  }, []);

  const klaviyoId = brand.klaviyoCompanyId;
  if (!klaviyoId || consent === "unknown") return null;

  function decide(value: Exclude<Consent, null>) {
    try {
      window.localStorage.setItem(STORAGE_KEY, value);
    } catch {
      // Without storage the choice lasts for this page view only.
    }
    setConsent(value);
  }

  if (consent === "granted") {
    return (
      <Script
        src={`https://static.klaviyo.com/onsite/js/${encodeURIComponent(klaviyoId)}/klaviyo.js`}
        strategy="afterInteractive"
      />
    );
  }
  if (consent === "denied") return null;

  return (
    <div
      role="region"
      aria-label="Cookie consent"
      className="fixed inset-x-4 bottom-4 z-50 mx-auto max-w-xl rounded-xl border border-line bg-surface p-5 shadow-2xl shadow-black/50"
    >
      <p className="text-sm text-ink-muted">
        We use one optional marketing cookie (Klaviyo) to send you product updates you asked for. Everything else on this site
        runs without tracking cookies. See the{" "}
        <Link href="/legal/cookies" className="text-ink underline underline-offset-4">
          cookie policy
        </Link>
        .
      </p>
      <div className="mt-4 flex flex-wrap gap-2">
        <button type="button" className="btn btn-primary" onClick={() => decide("granted")}>
          Allow
        </button>
        <button type="button" className="btn btn-secondary" onClick={() => decide("denied")}>
          Decline
        </button>
      </div>
    </div>
  );
}
