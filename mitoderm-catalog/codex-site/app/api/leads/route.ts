import { env, waitUntil } from "cloudflare:workers";
import { deliverLead } from "@/lib/leads-delivery.server";
import { handleLeadRequest, markLeadDelivered } from "@/lib/leads.server";
import type { SavedLeadRecord } from "@/lib/leads.server";
import { products } from "@/mitoderm/data";
import { leadLabels, professionLabels } from "@/mitoderm/lead-labels";

// A stored inquiry is sent to the team (e-mail, CRM webhook) in the background,
// so the visitor's confirmation never waits for those services.
function announce(lead: SavedLeadRecord) {
  const db = env.DB;
  waitUntil(deliverLead({
    id: lead.id,
    createdAt: lead.createdAt,
    name: lead.name,
    phone: lead.phone,
    profession: lead.profession,
    professionLabel: professionLabels.find(([value]) => value === lead.profession)?.[1] ?? lead.profession,
    productSlug: lead.productSlug,
    productName: products.find((product) => product.slug === lead.productSlug)?.name ?? leadLabels.unsure,
    comment: lead.comment,
    locale: lead.locale,
    sourceBlock: lead.sourceBlock,
  }, env, leadLabels).then((outcome) => {
    if (db && (outcome.email === "sent" || outcome.webhook === "sent")) {
      return markLeadDelivered(db, lead.id);
    }
  }).catch(() => undefined));
}

export function POST(request: Request) {
  return handleLeadRequest(request, env.DB, announce);
}

export function GET(request: Request) {
  return handleLeadRequest(request, env.DB);
}
