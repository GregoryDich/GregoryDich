"use client";

import { useEffect } from "react";
import { track } from "@/lib/track";

/** Reports `pricing_view` once per visit to /pricing; renders nothing. */
export function PricingViewTracker() {
  useEffect(() => {
    track("pricing_view");
  }, []);
  return null;
}
