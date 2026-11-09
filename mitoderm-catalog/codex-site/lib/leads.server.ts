import type { D1Database } from "@cloudflare/workers-types";
import {
  LEAD_PRIVACY_VERSION, MAX_LEAD_BODY_BYTES, validateLeadPayload,
} from "./leads-validation.server";
import type { LeadSubmission } from "./leads-validation.server";

type SavedLead = { id: string; payload_hash: string };

class IntakeError extends Error {
  status: number;
  code: string;
  constructor(status: number, code: string) {
    super(code);
    this.status = status;
    this.code = code;
  }
}

function jsonResponse(
  status: number, body: Record<string, unknown>, extraHeaders: Record<string, string> = {},
): Response {
  return Response.json(body, {
    status,
    headers: {
      "Cache-Control": "no-store, max-age=0",
      "X-Content-Type-Options": "nosniff",
      "X-Robots-Tag": "noindex, nofollow",
      ...extraHeaders,
    },
  });
}

async function readLimitedJson(request: Request): Promise<unknown> {
  const contentType = (request.headers.get("content-type") ?? "")
    .split(";", 1)[0].trim().toLowerCase();
  if (contentType !== "application/json") {
    throw new IntakeError(415, "unsupported_media_type");
  }
  const encoding = request.headers.get("content-encoding");
  if (encoding && encoding.toLowerCase() !== "identity") {
    throw new IntakeError(415, "unsupported_media_type");
  }
  const length = request.headers.get("content-length");
  if (length !== null && (!/^\d+$/.test(length) || Number(length) > MAX_LEAD_BODY_BYTES)) {
    throw new IntakeError(413, "body_too_large");
  }
  if (!request.body) throw new IntakeError(400, "invalid_json");

  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let total = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      total += value.byteLength;
      if (total > MAX_LEAD_BODY_BYTES) {
        await reader.cancel().catch(() => undefined);
        throw new IntakeError(413, "body_too_large");
      }
      chunks.push(value);
    }
  } finally {
    reader.releaseLock();
  }
  const bytes = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    bytes.set(chunk, offset);
    offset += chunk.byteLength;
  }
  try {
    return JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(bytes));
  } catch {
    throw new IntakeError(400, "invalid_json");
  }
}

function hex(bytes: Uint8Array): string {
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function payloadHash(lead: LeadSubmission): Promise<string> {
  const canonical = JSON.stringify([
    lead.name, lead.phone, lead.profession, lead.productSlug, lead.comment,
    lead.locale, lead.sourceBlock, LEAD_PRIVACY_VERSION,
  ]);
  return hex(new Uint8Array(await crypto.subtle.digest(
    "SHA-256", new TextEncoder().encode(canonical),
  )));
}

/**
 * Atomic D1 counters protect anonymous intake across Worker instances.
 * No raw IP is persisted. The random HMAC salt stays in private D1, so rate
 * keys cannot be trivially enumerated from phone/IP dictionaries.
 * Counters expire at the end of their window and are pruned in bounded batches.
 */
async function checkRateLimit(
  db: D1Database, request: Request, phone: string,
): Promise<number | null> {
  const saltCandidate = hex(crypto.getRandomValues(new Uint8Array(32)));
  const inserted = await db.prepare(
    "INSERT INTO mitoderm_lead_rate_config (singleton, salt) VALUES (1, ?) " +
    "ON CONFLICT(singleton) DO NOTHING",
  ).bind(saltCandidate).run();
  if (!inserted.success) throw new Error("rate_config_unavailable");

  const config = await db.prepare(
    "SELECT salt FROM mitoderm_lead_rate_config WHERE singleton = 1",
  ).first<{ salt: string }>();
  if (!config || !/^[a-f0-9]{64}$/.test(config.salt)) {
    throw new Error("rate_config_unavailable");
  }
  const key = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(config.salt),
    { name: "HMAC", hash: "SHA-256" }, false, ["sign"],
  );

  // Cloudflare owns CF-Connecting-IP at the edge. Do not trust X-Forwarded-For.
  // If it is absent, use a conservative shared bucket rather than failing open.
  const edgeIp = request.headers.get("cf-connecting-ip") ?? "";
  const ip = /^[a-f0-9:.]{3,64}$/i.test(edgeIp) ? edgeIp : "unknown-edge";
  const now = Math.floor(Date.now() / 1000);
  const limits = [
    { scope: "ip-quarter-hour", subject: ip, seconds: 900, max: 12 },
    { scope: "ip-day", subject: ip, seconds: 86400, max: 60 },
    { scope: "phone-day", subject: phone, seconds: 86400, max: 5 },
  ];
  const buckets = await Promise.all(limits.map(async (limit) => {
    const start = Math.floor(now / limit.seconds) * limit.seconds;
    const token = limit.scope + ":" + start + ":" + limit.subject;
    const bucketKey = hex(new Uint8Array(await crypto.subtle.sign(
      "HMAC", key, new TextEncoder().encode(token),
    )));
    return { bucketKey, expiresAt: start + limit.seconds, max: limit.max };
  }));

  const statements = buckets.map((bucket) => db.prepare(
    "INSERT INTO mitoderm_lead_rate_limits (bucket_key, hits, expires_at) " +
    "VALUES (?, 1, ?) ON CONFLICT(bucket_key) DO UPDATE SET hits = hits + 1 " +
    "WHERE hits < ? RETURNING hits",
  ).bind(bucket.bucketKey, bucket.expiresAt, bucket.max));

  // Deletes only expired ephemeral counters, never contact records.
  statements.push(db.prepare(
    "DELETE FROM mitoderm_lead_rate_limits WHERE bucket_key IN " +
    "(SELECT bucket_key FROM mitoderm_lead_rate_limits " +
    "WHERE expires_at <= ? ORDER BY expires_at LIMIT 200)",
  ).bind(now));
  const results = await db.batch<{ hits: number }>(statements);
  if (results.length !== statements.length || results.some((result) => !result.success)) {
    throw new Error("rate_limit_unavailable");
  }
  let retryAfter = 0;
  for (let index = 0; index < buckets.length; index++) {
    if (!results[index].results?.length) {
      retryAfter = Math.max(retryAfter, buckets[index].expiresAt - now);
    }
  }
  return retryAfter > 0 ? retryAfter : null;
}

/**
 * Anonymous, same-origin contact submission only. No retrieval API, messaging,
 * patient uploads, marketing subscription, or client-controlled verification.
 */
export async function handleLeadRequest(request: Request, db?: D1Database): Promise<Response> {
  if (request.method !== "POST") {
    return jsonResponse(405, { ok: false, code: "method_not_allowed" }, { Allow: "POST" });
  }

  try {
    const origin = request.headers.get("origin");
    if (!origin || origin !== new URL(request.url).origin ||
        request.headers.get("sec-fetch-site") === "cross-site") {
      return jsonResponse(403, { ok: false, code: "forbidden_origin" });
    }

    const result = validateLeadPayload(await readLimitedJson(request));
    if (!result.ok) {
      return jsonResponse(result.code === "request_rejected" ? 400 : 422, {
        ok: false, code: result.code, ...(result.fields ? { fields: result.fields } : {}),
      });
    }
    if (!db) return jsonResponse(503, { ok: false, code: "service_unavailable" });

    const lead = result.value;
    const retryAfter = await checkRateLimit(db, request, lead.phone);
    if (retryAfter !== null) {
      return jsonResponse(
        429, { ok: false, code: "rate_limited", retryAfter },
        { "Retry-After": String(retryAfter) },
      );
    }

    const fingerprint = await payloadHash(lead);
    const id = crypto.randomUUID();
    const saved = await db.prepare(
      "INSERT INTO mitoderm_leads " +
      "(id, request_id, payload_hash, name, phone, profession, product_slug, comment, " +
      "locale, source_block, privacy_consent, privacy_version, created_at) " +
      "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?) " +
      "ON CONFLICT(request_id) DO NOTHING RETURNING id, payload_hash",
    ).bind(
      id, lead.requestId, fingerprint, lead.name, lead.phone, lead.profession,
      lead.productSlug, lead.comment || null, lead.locale, lead.sourceBlock,
      LEAD_PRIVACY_VERSION, new Date().toISOString(),
    ).first<SavedLead>();

    if (saved?.id && saved.payload_hash === fingerprint) {
      return jsonResponse(201, { ok: true, code: "lead_saved", id: saved.id });
    }
    // Unique request_id makes simultaneous retries safe. A changed payload
    // cannot overwrite the first submission or be falsely acknowledged.
    const existing = await db.prepare(
      "SELECT id, payload_hash FROM mitoderm_leads WHERE request_id = ?",
    ).bind(lead.requestId).first<SavedLead>();
    if (!existing) return jsonResponse(503, { ok: false, code: "service_unavailable" });
    if (existing.payload_hash !== fingerprint) {
      return jsonResponse(409, { ok: false, code: "idempotency_conflict" });
    }
    return jsonResponse(200, { ok: true, code: "lead_saved", id: existing.id });
  } catch (error) {
    if (error instanceof IntakeError) {
      return jsonResponse(error.status, { ok: false, code: error.code });
    }
    // Never log the body, phone, name, IP, SQL exception, or database row.
    return jsonResponse(503, { ok: false, code: "service_unavailable" });
  }
}
