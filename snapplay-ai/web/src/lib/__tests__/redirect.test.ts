import { describe, expect, it } from "vitest";
import { normalizeReferralCode, safeNext } from "../redirect";

describe("safeNext", () => {
  it("accepts same-origin relative paths", () => {
    expect(safeNext("/account")).toBe("/account");
    expect(safeNext("/pricing?plan=pack_50#buy")).toBe("/pricing?plan=pack_50#buy");
  });

  it("rejects absolute, protocol-relative and scheme-like targets", () => {
    expect(safeNext("https://evil.example")).toBe("/account");
    expect(safeNext("//evil.example/x")).toBe("/account");
    expect(safeNext("/\\evil.example")).toBe("/account");
    expect(safeNext("/javascript:alert(1)")).toBe("/account");
    expect(safeNext("/x\r\nLocation: y")).toBe("/account");
    expect(safeNext("")).toBe("/account");
    expect(safeNext(null, "/")).toBe("/");
  });
});

describe("normalizeReferralCode", () => {
  it("accepts the contract pattern and rejects everything else", () => {
    expect(normalizeReferralCode(" abc_DEF-9 ")).toBe("abc_DEF-9");
    expect(normalizeReferralCode("a b")).toBeNull();
    expect(normalizeReferralCode("x".repeat(65))).toBeNull();
    expect(normalizeReferralCode(undefined)).toBeNull();
  });
});
