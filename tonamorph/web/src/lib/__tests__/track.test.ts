import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const { vercelTrack, consent } = vi.hoisted(() => ({
  vercelTrack: vi.fn(),
  consent: { record: null as null | { analytics: boolean } },
}));

vi.mock("@vercel/analytics", () => ({ track: vercelTrack }));
vi.mock("../consent", () => ({ readConsent: () => consent.record }));

import { FORBIDDEN_PROPERTY_KEYS, track, type TrackEvent } from "../track";

/** One sample per event; the type forces every documented property and forbids any other. */
const SAMPLES: TrackEvent[] = [
  { name: "cta_clicked", properties: { cta: "get_free_morphs", location: "hero" } },
  { name: "signup_started" },
  { name: "signup_completed", properties: { source: "web" } },
  { name: "plugin_downloaded", properties: { os: "macos" } },
  { name: "demo_play" },
  { name: "pricing_view" },
  { name: "checkout_started", properties: { plan_id: "pack_50", ref: "partner-1" } },
  { name: "nps_submitted", properties: { score: 9 } },
];

describe("track", () => {
  beforeEach(() => {
    vercelTrack.mockReset();
    consent.record = null;
    vi.stubGlobal("window", {});
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("sends the event name with its properties", () => {
    track("cta_clicked", { cta: "get_free_morphs", location: "hero" });
    expect(vercelTrack).toHaveBeenCalledWith("cta_clicked", { cta: "get_free_morphs", location: "hero" });
  });

  it("sends property-less events with the name only", () => {
    track("demo_play");
    expect(vercelTrack).toHaveBeenCalledTimes(1);
    expect(vercelTrack.mock.calls[0]).toEqual(["demo_play"]);
  });

  it("drops optional properties that are undefined", () => {
    track("checkout_started", { plan_id: "pack_50", ref: undefined });
    expect(vercelTrack).toHaveBeenCalledWith("checkout_started", { plan_id: "pack_50" });
  });

  it("runs before a cookie choice and after analytics consent, but not after a rejection", () => {
    track("pricing_view");
    consent.record = { analytics: true };
    track("pricing_view");
    consent.record = { analytics: false };
    track("pricing_view");
    expect(vercelTrack).toHaveBeenCalledTimes(2);
  });

  it("is a no-op on the server", () => {
    vi.unstubAllGlobals();
    track("pricing_view");
    expect(vercelTrack).not.toHaveBeenCalled();
  });

  it("carries no personal data on any event", () => {
    for (const sample of SAMPLES) {
      const keys = Object.keys(sample.properties ?? {});
      for (const key of keys) {
        expect(FORBIDDEN_PROPERTY_KEYS).not.toContain(key);
      }
      for (const value of Object.values(sample.properties ?? {})) {
        expect(["string", "number", "boolean"]).toContain(typeof value);
        if (typeof value === "string") expect(value).not.toMatch(/@/);
      }
    }
  });

  it("rejects unknown events and extra properties at compile time", () => {
    // @ts-expect-error — not in the taxonomy
    const unknown: TrackEvent = { name: "page_scrolled" };
    // @ts-expect-error — an email is never an event property
    const pii: TrackEvent = { name: "cta_clicked", properties: { cta: "x", location: "hero", email: "a@b.c" } };
    // @ts-expect-error — the user id stays server-side
    const withUser: TrackEvent = { name: "signup_completed", properties: { source: "web", user_id: "u1" } };
    expect([unknown, pii, withUser]).toHaveLength(3);
  });
});
