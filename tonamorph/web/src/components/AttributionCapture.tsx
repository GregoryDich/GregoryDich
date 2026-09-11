"use client";

import { useEffect } from "react";
import { captureAttribution } from "@/lib/attribution";

/** Records `ref` / `utm_*` from the current URL; renders nothing. */
export function AttributionCapture() {
  useEffect(() => {
    captureAttribution(window.location.search);
  }, []);
  return null;
}
