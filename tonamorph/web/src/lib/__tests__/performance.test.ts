import { describe, expect, it } from "vitest";
import { MEASURED_P95_SECONDS, SPEED_CLAIM, speedClaim } from "../../content/performance";

describe("speedClaim", () => {
  it("stays qualified until a p95 has been measured", () => {
    expect(speedClaim(null)).toEqual({ headline: "Playable in seconds, not minutes.", measurement: null });
    expect(speedClaim(0).headline).toBe("Playable in seconds, not minutes.");
    expect(speedClaim(Number.NaN).headline).toBe("Playable in seconds, not minutes.");
    expect(speedClaim(-3).headline).toBe("Playable in seconds, not minutes.");
  });

  it("switches to the measured figure once it exists", () => {
    expect(speedClaim(7.4).headline).toBe("Playable in 7.4 seconds.");
    expect(speedClaim(8).headline).toBe("Playable in 8 seconds.");
    expect(speedClaim(8).measurement).toMatch(/p95/);
  });

  it("drives the landing page from the single constant", () => {
    expect(SPEED_CLAIM).toEqual(speedClaim(MEASURED_P95_SECONDS));
    if (MEASURED_P95_SECONDS === null) {
      expect(SPEED_CLAIM.headline).toBe("Playable in seconds, not minutes.");
    } else {
      expect(SPEED_CLAIM.headline).toMatch(/^Playable in [\d.]+ seconds\.$/);
    }
  });
});
