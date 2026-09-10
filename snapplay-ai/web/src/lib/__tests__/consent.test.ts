import { describe, expect, it } from "vitest";
import { parseConsent } from "../consent";

describe("parseConsent", () => {
  it("reads a v1 record written by the banner", () => {
    const raw = encodeURIComponent(
      JSON.stringify({ v: 1, functional: true, analytics: false, marketing: true, policy: "2026-09-09", ts: "2026-09-10T00:00:00Z" }),
    );
    expect(parseConsent(raw)).toEqual({
      v: 1,
      functional: true,
      analytics: false,
      marketing: true,
      policy: "2026-09-09",
      ts: "2026-09-10T00:00:00Z",
    });
  });

  it("treats anything malformed or from another version as no choice", () => {
    expect(parseConsent(undefined)).toBeNull();
    expect(parseConsent("granted")).toBeNull();
    expect(parseConsent(encodeURIComponent(JSON.stringify({ v: 2, marketing: true })))).toBeNull();
    expect(parseConsent(encodeURIComponent(JSON.stringify({ v: 1, marketing: "yes" })))?.marketing).toBe(false);
  });
});
