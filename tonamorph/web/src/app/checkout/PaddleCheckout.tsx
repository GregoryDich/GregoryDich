"use client";

import Script from "next/script";
import { useCallback, useState } from "react";
import { brand } from "@/lib/brand";

interface PaddleGlobal {
  Initialize(options: { token: string; environment: "sandbox" | "production" }): void;
  Checkout: {
    open(options: {
      items: { priceId: string; quantity: number }[];
      customData?: Record<string, string>;
      customer?: { email: string };
      settings?: { successUrl?: string; displayMode?: "overlay" | "inline" };
    }): void;
  };
}

declare global {
  interface Window {
    Paddle?: PaddleGlobal;
  }
}

export interface CheckoutParams {
  priceId: string;
  userId: string;
  planId: string | null;
  ref: string | null;
  email: string | null;
}

/** Opens Paddle's overlay checkout once paddle.js has loaded. */
export function PaddleCheckout({ params, token }: { params: CheckoutParams; token: string }) {
  const [state, setState] = useState<"loading" | "open" | "error">("loading");

  const open = useCallback(() => {
    const paddle = window.Paddle;
    if (!paddle) {
      setState("error");
      return;
    }
    try {
      paddle.Initialize({ token, environment: brand.paddleEnvironment });
      const customData: Record<string, string> = { user_id: params.userId };
      if (params.planId) customData.plan_id = params.planId;
      if (params.ref) customData.ref = params.ref;
      paddle.Checkout.open({
        items: [{ priceId: params.priceId, quantity: 1 }],
        customData,
        ...(params.email ? { customer: { email: params.email } } : {}),
        settings: { displayMode: "overlay", successUrl: `${brand.siteUrl}/account?purchase=success` },
      });
      setState("open");
    } catch {
      setState("error");
    }
  }, [params, token]);

  return (
    <>
      <Script src="https://cdn.paddle.com/paddle/v2/paddle.js" strategy="afterInteractive" onLoad={open} onError={() => setState("error")} />
      {state === "loading" && (
        <p className="text-sm text-ink-muted" aria-live="polite">
          Opening secure checkout…
        </p>
      )}
      {state === "open" && (
        <div className="space-y-3 text-sm text-ink-muted" aria-live="polite">
          <p>The checkout is open in an overlay. If you closed it, you can reopen it below.</p>
          <button type="button" className="btn btn-primary" onClick={open}>
            Reopen checkout
          </button>
        </div>
      )}
      {state === "error" && (
        <p role="alert" className="alert alert-error">
          The checkout could not be loaded. Check that your browser allows scripts from {brand.merchantOfRecord}, then reload.
        </p>
      )}
    </>
  );
}
