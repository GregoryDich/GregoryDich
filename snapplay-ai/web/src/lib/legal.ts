import "server-only";

import fs from "node:fs";
import path from "node:path";
import { brand, type Brand } from "./brand";
import { formatDate } from "./format";

/**
 * Loads the legal documents (Markdown, maintained outside this package) at build time,
 * strips authoring comments and substitutes the `[[TOKEN]]` placeholders from `brand`.
 * Any placeholder that is not in the list below fails the build.
 */

export const LEGAL_SLUGS = ["terms", "privacy", "refunds", "copyright", "cookies", "eula"] as const;
export type LegalSlug = (typeof LEGAL_SLUGS)[number];

export const LEGAL_DOCUMENTS: Record<LegalSlug, { file: string; title: string }> = {
  terms: { file: "terms-of-service.md", title: "Terms of Service" },
  privacy: { file: "privacy-policy.md", title: "Privacy Policy" },
  refunds: { file: "refund-policy.md", title: "Refund Policy" },
  copyright: { file: "copyright-policy.md", title: "Copyright Policy" },
  cookies: { file: "cookie-policy.md", title: "Cookie Policy" },
  eula: { file: "eula.md", title: "End-User Licence Agreement" },
};

/** `<repo>/legal`, relative to this package (`<repo>/web`). */
export const DEFAULT_LEGAL_DIR = path.resolve(process.cwd(), "..", "legal");

export const LEGAL_TOKEN_NAMES = [
  "PRODUCT_NAME",
  "COMPANY_LEGAL_NAME",
  "COMPANY_ADDRESS",
  "COMPANY_REG_ID",
  "WEBSITE_URL",
  "SUPPORT_EMAIL",
  "PRIVACY_EMAIL",
  "LEGAL_EMAIL",
  "MERCHANT_OF_RECORD",
  "EFFECTIVE_DATE",
  "EFFECTIVE_YEAR",
] as const;
export type LegalTokenName = (typeof LEGAL_TOKEN_NAMES)[number];
export type LegalTokens = Record<LegalTokenName, string>;

export function tokensFromBrand(b: Brand = brand): LegalTokens {
  const yearMatch = /^(\d{4})-\d{2}-\d{2}$/.exec(b.legalEffectiveDate);
  return {
    PRODUCT_NAME: b.productName,
    COMPANY_LEGAL_NAME: b.companyLegalName,
    COMPANY_ADDRESS: b.companyAddress,
    COMPANY_REG_ID: b.companyRegId,
    WEBSITE_URL: b.siteUrl,
    SUPPORT_EMAIL: b.supportEmail,
    PRIVACY_EMAIL: b.privacyEmail,
    LEGAL_EMAIL: b.legalEmail,
    MERCHANT_OF_RECORD: b.merchantOfRecord,
    EFFECTIVE_DATE: formatDate(b.legalEffectiveDate),
    EFFECTIVE_YEAR: yearMatch?.[1] ?? String(new Date().getUTCFullYear()),
  };
}

export function stripHtmlComments(markdown: string): string {
  return markdown.replace(/<!--[\s\S]*?-->/g, "");
}

const PLACEHOLDER = /\[\[([^\]]*)\]\]/g;

/** Replaces every known `[[TOKEN]]`; throws naming the source when an unknown one remains. */
export function substituteTokens(markdown: string, tokens: LegalTokens, sourceName: string): string {
  const unknown = new Set<string>();
  const result = markdown.replace(PLACEHOLDER, (match, name: string) => {
    if (Object.prototype.hasOwnProperty.call(tokens, name)) {
      return tokens[name as LegalTokenName];
    }
    unknown.add(match);
    return match;
  });
  if (unknown.size > 0) {
    throw new Error(`Unknown legal placeholder(s) in ${sourceName}: ${[...unknown].join(", ")}`);
  }
  return result;
}

export function renderLegalMarkdown(raw: string, tokens: LegalTokens, sourceName: string): string {
  return substituteTokens(stripHtmlComments(raw), tokens, sourceName).trim();
}

export function isLegalSlug(value: string): value is LegalSlug {
  return (LEGAL_SLUGS as readonly string[]).includes(value);
}

export function legalFilePath(slug: LegalSlug, dir: string = DEFAULT_LEGAL_DIR): string {
  return path.join(dir, LEGAL_DOCUMENTS[slug].file);
}

/** Slugs whose source file exists; the caller decides whether missing ones are a warning or an error. */
export function availableLegalSlugs(dir: string = DEFAULT_LEGAL_DIR): LegalSlug[] {
  return LEGAL_SLUGS.filter((slug) => fs.existsSync(legalFilePath(slug, dir)));
}

export interface LegalDocument {
  slug: LegalSlug;
  title: string;
  markdown: string;
}

export function loadLegalDocument(
  slug: LegalSlug,
  dir: string = DEFAULT_LEGAL_DIR,
  tokens: LegalTokens = tokensFromBrand(),
): LegalDocument | null {
  const file = legalFilePath(slug, dir);
  if (!fs.existsSync(file)) return null;
  const raw = fs.readFileSync(file, "utf8");
  const markdown = renderLegalMarkdown(raw, tokens, path.basename(file));
  const heading = /^#\s+(.+)$/m.exec(markdown);
  return { slug, title: heading?.[1]?.trim() || LEGAL_DOCUMENTS[slug].title, markdown };
}
