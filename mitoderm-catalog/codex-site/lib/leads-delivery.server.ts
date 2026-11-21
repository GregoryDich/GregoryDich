/**
 * Tells the team about a saved inquiry: an e-mail through Resend and a signed
 * webhook for the CRM. Both are optional and are configured only by the worker's
 * environment (variables and secrets). With nothing configured the inquiry simply
 * stays in the database, as before. Delivery is best-effort: it never throws and
 * never writes the inquiry itself to the logs.
 */
export type LeadDeliveryEnv = {
  RESEND_API_KEY?: string;
  LEADS_TO_EMAIL?: string;
  LEADS_FROM_EMAIL?: string;
  LEADS_WEBHOOK_URL?: string;
  LEADS_WEBHOOK_SECRET?: string;
};

export type DeliveredLead = {
  id: string;
  createdAt: string;
  name: string;
  phone: string;
  profession: string;
  professionLabel: string;
  productSlug: string;
  productName: string;
  comment: string;
  locale: string;
  sourceBlock: string;
};

export type LeadEmailLabels = {
  received: string;
  name: string;
  phone: string;
  profession: string;
  product: string;
  comment: string;
};

export type ChannelOutcome = "sent" | "skipped" | "failed";
export type DeliveryOutcome = { email: ChannelOutcome; webhook: ChannelOutcome };

const RESEND_URL = "https://api.resend.com/emails";
const TIMEOUT_MS = 8000;

// Keeps a phone number or a Latin product name in its own order inside a Hebrew line.
const ltr = (value: string) => "⁦" + value + "⁩";

export function leadEmail(
  lead: DeliveredLead, labels: LeadEmailLabels,
): { subject: string; text: string } {
  // A comment may carry direction-override characters; they must not reorder the e-mail.
  const comment = lead.comment.replace(/[‪-‮⁦-⁩]/g, "");
  const lines = [
    labels.name + ": " + lead.name,
    labels.phone + ": " + ltr(lead.phone),
    "WhatsApp: https://wa.me/" + lead.phone.replace(/\D/g, ""),
    labels.profession + ": " + lead.professionLabel,
    labels.product + ": " + ltr(lead.productName),
  ];
  if (comment) lines.push("", labels.comment, comment);
  lines.push("", lead.id.slice(0, 8).toUpperCase() + " · " + lead.createdAt + " · " + lead.sourceBlock);
  return {
    subject: labels.received + " · " + lead.name + " · " + lead.productName,
    text: lines.join("\n"),
  };
}

async function post(
  fetchImpl: typeof fetch, channel: string, url: string,
  headers: Record<string, string>, body: string,
): Promise<ChannelOutcome> {
  try {
    const response = await fetchImpl(url, {
      method: "POST", headers, body, signal: AbortSignal.timeout(TIMEOUT_MS),
    });
    if (response.ok) return "sent";
    // Only the channel and the status are logged, never the inquiry.
    console.warn("lead delivery failed", channel, response.status);
  } catch {
    console.warn("lead delivery failed", channel, "no response");
  }
  return "failed";
}

function sendEmail(
  lead: DeliveredLead, env: LeadDeliveryEnv, labels: LeadEmailLabels, fetchImpl: typeof fetch,
): Promise<ChannelOutcome> {
  const to = (env.LEADS_TO_EMAIL ?? "").split(",").map((address) => address.trim()).filter(Boolean);
  if (!env.RESEND_API_KEY || !env.LEADS_FROM_EMAIL || !to.length) return Promise.resolve("skipped");
  const { subject, text } = leadEmail(lead, labels);
  return post(
    fetchImpl, "email", RESEND_URL,
    { Authorization: "Bearer " + env.RESEND_API_KEY, "Content-Type": "application/json" },
    JSON.stringify({ from: env.LEADS_FROM_EMAIL, to, subject, text }),
  );
}

async function signature(secret: string, body: string): Promise<string> {
  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw", encoder.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );
  const mac = new Uint8Array(await crypto.subtle.sign("HMAC", key, encoder.encode(body)));
  return Array.from(mac, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function sendWebhook(
  lead: DeliveredLead, env: LeadDeliveryEnv, fetchImpl: typeof fetch,
): Promise<ChannelOutcome> {
  if (!env.LEADS_WEBHOOK_URL) return "skipped";
  let url: URL;
  try {
    url = new URL(env.LEADS_WEBHOOK_URL);
  } catch {
    console.warn("lead delivery failed", "webhook", "bad address");
    return "failed";
  }
  // Contact details leave the site only over HTTPS; plain HTTP is for a local test.
  const local = url.hostname === "127.0.0.1" || url.hostname === "localhost";
  if (url.protocol !== "https:" && !(url.protocol === "http:" && local)) {
    console.warn("lead delivery failed", "webhook", "bad address");
    return "failed";
  }
  const body = JSON.stringify({ source: "mitoderm-site", receivedAt: new Date().toISOString(), lead });
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  try {
    if (env.LEADS_WEBHOOK_SECRET) {
      headers["x-mitoderm-signature"] = "sha256=" + await signature(env.LEADS_WEBHOOK_SECRET, body);
    }
  } catch {
    console.warn("lead delivery failed", "webhook", "signature");
    return "failed";
  }
  return post(fetchImpl, "webhook", url.href, headers, body);
}

export async function deliverLead(
  lead: DeliveredLead, env: LeadDeliveryEnv, labels: LeadEmailLabels,
  fetchImpl: typeof fetch = fetch,
): Promise<DeliveryOutcome> {
  const [email, webhook] = await Promise.all([
    sendEmail(lead, env, labels, fetchImpl),
    sendWebhook(lead, env, fetchImpl),
  ]);
  return { email, webhook };
}
