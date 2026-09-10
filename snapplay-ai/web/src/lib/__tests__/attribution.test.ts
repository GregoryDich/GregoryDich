import { describe, expect, it } from "vitest";
import { attributionFromSearch, attributionQuery } from "../attribution";

describe("attribution parsing", () => {
  it("keeps a valid ref and the utm_* parameters, dropping everything else", () => {
    const search = "?utm_source=tiktok&utm_medium=social&utm_campaign=ugc_shorts&utm_content=item-1&ref=CODE_1&fbclid=x";
    expect(attributionFromSearch(search)).toEqual({
      referral_code: "CODE_1",
      utm_source: "tiktok",
      utm_medium: "social",
      utm_campaign: "ugc_shorts",
      utm_content: "item-1",
    });
    expect(attributionQuery(search)).toBe("ref=CODE_1&utm_source=tiktok&utm_medium=social&utm_campaign=ugc_shorts&utm_content=item-1");
  });

  it("rejects a ref that does not match the contract pattern", () => {
    expect(attributionFromSearch("?ref=bad%20code")).toEqual({});
    expect(attributionQuery("")).toBe("");
  });
});
