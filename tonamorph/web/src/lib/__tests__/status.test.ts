import { describe, expect, it } from "vitest";
import { formatMs, parseStatus } from "../status";

describe("parseStatus", () => {
  it("reads the documented shape", () => {
    const view = parseStatus({
      components: { api: "operational", engine: "degraded", payments: "operational", website: "operational" },
      last_24h: { morphs: 412, success_rate: 0.9927, p50_ms: 3800, p95_ms: 9600 },
    });
    expect(view.components.map((c) => [c.key, c.state])).toEqual([
      ["api", "operational"],
      ["engine", "degraded"],
      ["payments", "operational"],
      ["website", "operational"],
    ]);
    expect(view.last24h).toEqual({ morphs: 412, successRatePercent: 99.3, p50Ms: 3800, p95Ms: 9600 });
    expect(view.overall).toBe("degraded");
  });

  it("accepts component objects, percentages and unknown wording without breaking", () => {
    const view = parseStatus({
      components: { api: { status: "OK" }, engine: "warming up", payments: { state: "down" } },
      last_24h: { morphs: "12", success_rate: 98.5, p50_ms: null },
    });
    expect(view.components[0]).toMatchObject({ key: "api", state: "operational", raw: null });
    expect(view.components[1]).toMatchObject({ key: "engine", state: "unknown", raw: "warming up" });
    expect(view.components[2]).toMatchObject({ key: "payments", state: "down" });
    expect(view.components[3]).toMatchObject({ key: "website", state: "unknown", raw: null });
    expect(view.last24h).toEqual({ morphs: null, successRatePercent: 98.5, p50Ms: null, p95Ms: null });
    expect(view.overall).toBe("down");
  });

  it("renders an empty or malformed body as unknown", () => {
    expect(parseStatus(null).overall).toBe("unknown");
    expect(parseStatus("nope").components).toHaveLength(4);
    expect(parseStatus({ last_24h: { success_rate: 250 } }).last24h.successRatePercent).toBeNull();
  });
});

describe("formatMs", () => {
  it("switches to seconds above one second", () => {
    expect(formatMs(null)).toBe("—");
    expect(formatMs(640)).toBe("640 ms");
    expect(formatMs(9600)).toBe("9.6 s");
  });
});
