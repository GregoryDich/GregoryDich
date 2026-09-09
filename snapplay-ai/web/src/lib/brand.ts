/**
 * Every product-facing name, address and URL comes from here. The product is being
 * renamed, so no page, component or metadata may contain the name as a literal —
 * always `brand.productName`. All values are NEXT_PUBLIC_* so client components can
 * read them too; none of them are secrets.
 */

const DEFAULT_PRODUCT_NAME = "SnapPlay AI";

// Next.js inlines NEXT_PUBLIC_* into client bundles only when referenced literally.
const raw = {
  productName: process.env.NEXT_PUBLIC_PRODUCT_NAME,
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL,
  supportEmail: process.env.NEXT_PUBLIC_SUPPORT_EMAIL,
  companyLegalName: process.env.NEXT_PUBLIC_COMPANY_LEGAL_NAME,
  companyAddress: process.env.NEXT_PUBLIC_COMPANY_ADDRESS,
  companyRegId: process.env.NEXT_PUBLIC_COMPANY_REG_ID,
  privacyEmail: process.env.NEXT_PUBLIC_PRIVACY_EMAIL,
  legalEmail: process.env.NEXT_PUBLIC_LEGAL_EMAIL,
  merchantOfRecord: process.env.NEXT_PUBLIC_MERCHANT_OF_RECORD,
  legalEffectiveDate: process.env.NEXT_PUBLIC_LEGAL_EFFECTIVE_DATE,
  apiUrl: process.env.NEXT_PUBLIC_API_URL,
  billingPortalUrl: process.env.NEXT_PUBLIC_BILLING_PORTAL_URL,
  klaviyoCompanyId: process.env.NEXT_PUBLIC_KLAVIYO_COMPANY_ID,
  downloadBaseUrl: process.env.NEXT_PUBLIC_DOWNLOAD_BASE_URL,
};

function text(value: string | undefined, fallback: string): string {
  const trimmed = value?.trim();
  return trimmed ? trimmed : fallback;
}

function optional(value: string | undefined): string | null {
  const trimmed = value?.trim();
  return trimmed ? trimmed : null;
}

function stripTrailingSlash(url: string): string {
  return url.replace(/\/+$/, "");
}

const productName = text(raw.productName, DEFAULT_PRODUCT_NAME);
const siteUrl = stripTrailingSlash(text(raw.siteUrl, "http://localhost:3000"));
const siteHost = new URL(siteUrl).hostname;
const supportEmail = text(raw.supportEmail, `support@${siteHost}`);
const apiUrl = optional(raw.apiUrl);

export const brand = {
  productName,
  /** URL-safe, lower-case form of the product name, used for file names and ids. */
  slug: productName
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/(^-|-$)/g, ""),
  tagline: "Turn any track into a playable instrument in 2 seconds.",
  siteUrl,
  siteHost,
  supportEmail,
  privacyEmail: text(raw.privacyEmail, supportEmail),
  legalEmail: text(raw.legalEmail, supportEmail),
  companyLegalName: text(raw.companyLegalName, productName),
  companyAddress: text(raw.companyAddress, ""),
  companyRegId: text(raw.companyRegId, ""),
  merchantOfRecord: text(raw.merchantOfRecord, "Paddle"),
  /** ISO date (YYYY-MM-DD) the legal documents took effect. */
  legalEffectiveDate: text(raw.legalEffectiveDate, "2026-09-09"),
  /** Backend base URL (contract base URL, no trailing slash). Null disables live data. */
  apiUrl: apiUrl ? stripTrailingSlash(apiUrl) : null,
  billingPortalUrl: optional(raw.billingPortalUrl),
  klaviyoCompanyId: optional(raw.klaviyoCompanyId),
  downloadBaseUrl: stripTrailingSlash(text(raw.downloadBaseUrl, "/downloads")),
} as const;

export type Brand = typeof brand;
