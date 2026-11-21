declare namespace Cloudflare {
  interface Env {
    DB?: D1Database;
    BUCKET?: R2Bucket;
    // Where a saved inquiry is sent; see lib/leads-delivery.server.ts. All optional.
    RESEND_API_KEY?: string;
    LEADS_TO_EMAIL?: string;
    LEADS_FROM_EMAIL?: string;
    LEADS_WEBHOOK_URL?: string;
    LEADS_WEBHOOK_SECRET?: string;
  }
}
