/**
 * Public contact intake validation. No patient data, authentication, or marketing
 * subscription is accepted here. Only the listed fields cross the trust boundary.
 */
export const MAX_LEAD_BODY_BYTES = 8192;
export const LEAD_PRIVACY_VERSION = "mitoderm-contact-v1";

const PROFESSIONS = Object.freeze([
  "cosmetologist", "doctor", "nurse", "clinic_owner", "other",
] as const);
const PRODUCT_SLUGS = Object.freeze([
  "unsure", "v-tech-system", "exo-nad", "exosignal-hair", "exosignal-spray",
  "exotech-gel", "exocell-mask", "micro-boost-10", "cellular-age-defense-2-5",
  "cell-renew-1-5", "derma-recovery-cream", "mitopen", "mitoscan",
  "mitotech-cell-booster",
] as const);
const LOCALES = Object.freeze(["he", "ru", "en"] as const);
const ALLOWED_FIELDS = Object.freeze([
  "name", "phone", "profession", "productSlug", "comment", "privacyConsent",
  "website", "requestId", "locale", "sourceBlock",
] as const);

export type LeadSubmission = {
  name: string;
  phone: string;
  profession: (typeof PROFESSIONS)[number];
  productSlug: (typeof PRODUCT_SLUGS)[number];
  comment: string;
  privacyConsent: true;
  requestId: string;
  locale: (typeof LOCALES)[number];
  sourceBlock: string;
};

export type LeadValidationResult =
  | { ok: true; value: LeadSubmission }
  | {
      ok: false;
      code: "validation_error" | "request_rejected";
      fields?: Record<string, string>;
    };

export function normalizeLeadPhone(raw: unknown): string | null {
  if (typeof raw !== "string" || raw.length > 40) return null;
  const text = raw.trim();
  if (!/^[+0-9()\s.\-]+$/.test(text)) return null;
  let phone = text.replace(/[()\s.\-]/g, "");
  if (phone.startsWith("00")) phone = "+" + phone.slice(2);
  if (/^0[2-9]\d{7,8}$/.test(phone)) phone = "+972" + phone.slice(1);
  else if (/^972[2-9]\d{7,8}$/.test(phone)) phone = "+" + phone;
  if (phone.startsWith("+9720")) phone = "+972" + phone.slice(5);
  if (!/^\+[1-9]\d{7,14}$/.test(phone)) return null;
  if (phone.startsWith("+972") && !/^\+972[2-9]\d{7,8}$/.test(phone)) return null;
  return phone;
}

export function validateLeadPayload(input: unknown): LeadValidationResult {
  if (input === null || typeof input !== "object" || Array.isArray(input)) {
    return { ok: false, code: "validation_error", fields: { _form: "invalid_object" } };
  }
  const raw = input as Record<string, unknown>;
  // A filled honeypot is rejected, never acknowledged as a saved lead.
  if (raw.website !== undefined &&
      (typeof raw.website !== "string" || raw.website.trim() !== "")) {
    return { ok: false, code: "request_rejected" };
  }

  const fields: Record<string, string> = {};
  if (Object.keys(raw).some((key) => !(ALLOWED_FIELDS as readonly string[]).includes(key))) {
    fields._form = "unsupported_fields";
  }

  const name = typeof raw.name === "string"
    ? raw.name.normalize("NFC").trim().replace(/[ \t]+/g, " ") : "";
  if (name.length < 2 || name.length > 100 || !/\p{L}/u.test(name) ||
      /[\u0000-\u001f\u007f-\u009f\u202a-\u202e\u2066-\u2069]/u.test(name)) {
    fields.name = "invalid_name";
  }
  const phone = normalizeLeadPhone(raw.phone);
  if (!phone) fields.phone = "invalid_phone";

  if (typeof raw.profession !== "string" ||
      !(PROFESSIONS as readonly string[]).includes(raw.profession)) {
    fields.profession = "invalid_profession";
  }
  if (typeof raw.productSlug !== "string" ||
      !(PRODUCT_SLUGS as readonly string[]).includes(raw.productSlug)) {
    fields.productSlug = "invalid_product";
  }

  let comment = "";
  if (raw.comment !== undefined) {
    if (typeof raw.comment !== "string") fields.comment = "invalid_comment";
    else {
      comment = raw.comment.normalize("NFC").replace(/\r\n?/g, "\n").trim();
      if (comment.length > 1000 ||
          /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]/u.test(comment)) {
        fields.comment = "invalid_comment";
      }
    }
  }

  if (raw.privacyConsent !== true) fields.privacyConsent = "consent_required";
  const requestId = typeof raw.requestId === "string" ? raw.requestId.toLowerCase() : "";
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(requestId)) {
    fields.requestId = "invalid_request_id";
  }

  const locale = raw.locale === undefined ? "he" : raw.locale;
  if (typeof locale !== "string" || !(LOCALES as readonly string[]).includes(locale)) {
    fields.locale = "invalid_locale";
  }
  const sourceBlock = raw.sourceBlock === undefined ? "unknown" : raw.sourceBlock;
  if (typeof sourceBlock !== "string" || !/^[a-z0-9][a-z0-9_.:\-]{0,63}$/i.test(sourceBlock)) {
    fields.sourceBlock = "invalid_source";
  }

  if (Object.keys(fields).length) return { ok: false, code: "validation_error", fields };
  return {
    ok: true,
    value: {
      name, phone: phone!, profession: raw.profession as LeadSubmission["profession"],
      productSlug: raw.productSlug as LeadSubmission["productSlug"], comment,
      privacyConsent: true, requestId, locale: locale as LeadSubmission["locale"],
      sourceBlock: sourceBlock as string,
    },
  };
}
