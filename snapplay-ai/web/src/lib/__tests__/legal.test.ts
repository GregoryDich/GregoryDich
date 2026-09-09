import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  availableLegalSlugs,
  loadLegalDocument,
  renderLegalMarkdown,
  stripHtmlComments,
  substituteTokens,
  tokensFromBrand,
  type LegalTokens,
} from "../legal";
import { brand } from "../brand";

const FIXTURES = path.join(__dirname, "fixtures");

const tokens: LegalTokens = {
  PRODUCT_NAME: "Example Product",
  COMPANY_LEGAL_NAME: "Example Ltd",
  COMPANY_ADDRESS: "1 Example Street, Example City",
  COMPANY_REG_ID: "REG-123",
  WEBSITE_URL: "https://example.com",
  SUPPORT_EMAIL: "support@example.com",
  PRIVACY_EMAIL: "privacy@example.com",
  LEGAL_EMAIL: "legal@example.com",
  MERCHANT_OF_RECORD: "Example Merchant",
  EFFECTIVE_DATE: "January 1, 2026",
  EFFECTIVE_YEAR: "2026",
};

describe("legal loader", () => {
  it("substitutes every supported token", () => {
    const doc = loadLegalDocument("terms", FIXTURES, tokens);
    expect(doc).not.toBeNull();
    const md = doc!.markdown;
    expect(md).toContain("Example Product is operated by Example Ltd (REG-123), 1 Example Street, Example City.");
    expect(md).toContain("Visit https://example.com or write to support@example.com, privacy@example.com or legal@example.com.");
    expect(md).toContain("Purchases are handled by Example Merchant.");
    expect(md).toContain("_Effective date: January 1, 2026_");
    expect(md).toContain("© 2026");
    expect(md).not.toMatch(/\[\[/);
    expect(doc!.title).toBe("Terms of Service");
  });

  it("strips single-line and multi-line HTML comments before checking tokens", () => {
    const doc = loadLegalDocument("terms", FIXTURES, tokens);
    expect(doc!.markdown).not.toContain("LAWYER-REVIEW");
    expect(doc!.markdown).not.toContain("Multi-line comment");
    expect(doc!.markdown).not.toContain("UNKNOWN_TOKEN_IN_COMMENT");
    expect(stripHtmlComments("a <!-- x\ny --> b <!-- z --> c")).toBe("a  b  c");
  });

  it("throws on an unknown placeholder, naming the file and the token", () => {
    expect(() => loadLegalDocument("privacy", FIXTURES, tokens)).toThrow(
      /Unknown legal placeholder\(s\) in privacy-policy\.md: \[\[DPO_NAME\]\]/,
    );
    expect(() => substituteTokens("[[NOPE]] and [[ALSO_NOPE]]", tokens, "x.md")).toThrow(/\[\[NOPE\]\], \[\[ALSO_NOPE\]\]/);
  });

  it("renderLegalMarkdown composes stripping and substitution", () => {
    expect(renderLegalMarkdown("<!-- c -->Hello [[PRODUCT_NAME]]", tokens, "t.md")).toBe("Hello Example Product");
  });

  it("returns null for a document whose file does not exist and lists only existing slugs", () => {
    expect(loadLegalDocument("eula", FIXTURES, tokens)).toBeNull();
    expect(availableLegalSlugs(FIXTURES)).toEqual(["terms", "privacy"]);
  });

  it("derives tokens from the brand object", () => {
    const derived = tokensFromBrand(brand);
    expect(derived.PRODUCT_NAME).toBe(brand.productName);
    expect(derived.WEBSITE_URL).toBe(brand.siteUrl);
    expect(derived.EFFECTIVE_YEAR).toMatch(/^\d{4}$/);
    expect(derived.EFFECTIVE_DATE).not.toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
