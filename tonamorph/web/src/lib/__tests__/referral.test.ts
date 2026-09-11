import { describe, expect, it } from "vitest";
import { attributionFromSearch } from "../attribution";
import { parseUserReferralCode, referralSignupHref } from "../referral";

describe("parseUserReferralCode", () => {
  it("accepts an 8-character code from the contract alphabet and returns it upper-cased", () => {
    expect(parseUserReferralCode("AB23CDEF")).toBe("AB23CDEF");
    expect(parseUserReferralCode("ab23cdef")).toBe("AB23CDEF");
    expect(parseUserReferralCode(" ab23cdef ")).toBe("AB23CDEF");
    expect(parseUserReferralCode("23456789")).toBe("23456789");
  });

  it("rejects the wrong length, the ambiguous characters and anything outside the alphabet", () => {
    expect(parseUserReferralCode("AB23CDE")).toBeNull();
    expect(parseUserReferralCode("AB23CDEFG")).toBeNull();
    for (const ambiguous of ["0", "O", "1", "I", "L", "l"]) {
      expect(parseUserReferralCode(`AB23CDE${ambiguous}`)).toBeNull();
    }
    expect(parseUserReferralCode("AB23-DEF")).toBeNull();
    expect(parseUserReferralCode("AB23_DEF")).toBeNull();
    // An affiliate code (`GET /v1/plans?ref=`) is not a user code.
    expect(parseUserReferralCode("GREG30")).toBeNull();
    expect(parseUserReferralCode("AB23CDEF%0A")).toBeNull();
    expect(parseUserReferralCode("")).toBeNull();
    expect(parseUserReferralCode(undefined)).toBeNull();
    expect(parseUserReferralCode(null)).toBeNull();
  });
});

describe("referralSignupHref", () => {
  it("sends the code to the sign-up form in the URL", () => {
    expect(referralSignupHref("AB23CDEF")).toBe("/signup?ref=AB23CDEF");
  });

  it("is read by the sign-up form's attribution parser as the referral_code metadata", () => {
    const href = referralSignupHref("AB23CDEF");
    expect(attributionFromSearch(href.slice(href.indexOf("?")))).toEqual({ referral_code: "AB23CDEF" });
  });
});
