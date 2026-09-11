import "server-only";

import { brand } from "./brand";

/**
 * The one client for the backend (docs/API_CONTRACT.md). Every call runs on the server,
 * carries the Supabase access token as `Authorization: Bearer …` and maps the §5 error
 * envelope to `ApiError`. Nothing here logs: tokens and bodies never reach a log line.
 */

const PATHS = {
  me: "/v1/me",
  plans: "/v1/plans",
  jobs: "/v1/jobs",
  apiKeys: "/v1/api-keys",
  status: "/v1/status",
  nps: "/v1/nps",
} as const;

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, unknown> | null;

  constructor(status: number, code: string, message: string, details: Record<string, unknown> | null = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }

  get isNotFound(): boolean {
    return this.status === 404;
  }
}

// --- Contract shapes ------------------------------------------------------------------

export type UserPlan = "free" | "credits" | "subscription";

export interface Balance {
  credits: number;
  reserved: number;
  available: number;
  subscription_renews_at?: string | null;
}

export interface Me {
  user: { id: string; email: string; plan: UserPlan };
  balance: Balance;
}

export interface Plan {
  id: string;
  name: string;
  credits: number;
  price_usd: number;
  interval: "month" | "year" | null;
  checkout_url: string | null;
}

export type JobState = "queued" | "running" | "succeeded" | "failed" | "cancelled";
export type JobStage = "upload" | "separate" | "transcribe" | "analyze" | "package" | "done";

export interface JobSummary {
  job_id: string;
  status: JobState;
  stage: JobStage;
  progress: number;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
  error: { code: string; message: string } | null;
  result: {
    credits_charged: number;
    input?: { duration_seconds: number };
  } | null;
}

export interface JobsPage {
  jobs: JobSummary[];
  next_cursor: string | null;
}

export interface ApiKey {
  id: string;
  name: string;
  prefix: string;
  created_at: string;
  last_used_at: string | null;
  revoked_at?: string | null;
}

export interface ApiKeysPage {
  keys: ApiKey[];
}

export interface ApiKeyCreated extends ApiKey {
  /** Plaintext secret, returned exactly once (§11). */
  key: string;
}

/** `GET /v1/status`: component health plus the last 24 hours of morph numbers. */
export type ComponentState = "operational" | "degraded" | "down" | "maintenance";

export interface ServiceStatus {
  components: Record<"api" | "engine" | "payments" | "website", ComponentState | string>;
  last_24h: {
    morphs: number;
    /** Fraction (0–1) of morphs that succeeded. */
    success_rate: number;
    p50_ms: number;
    p95_ms: number;
  };
}

export interface NpsSubmission {
  score: number;
  comment?: string;
}

// --- Error envelope --------------------------------------------------------------------

const FALLBACK_CODES: Record<number, string> = {
  400: "bad_request",
  401: "unauthorized",
  402: "insufficient_credits",
  403: "unauthorized",
  404: "not_found",
  409: "conflict",
  413: "payload_too_large",
  415: "unsupported_media_type",
  422: "validation_error",
  429: "rate_limited",
  500: "internal_error",
  503: "worker_unavailable",
};

/** Builds an ApiError from a non-2xx status and the raw body (a §5 envelope when the API sent one). */
export function errorFromResponse(status: number, bodyText: string): ApiError {
  const fallbackCode = FALLBACK_CODES[status] ?? "internal_error";
  try {
    const parsed: unknown = JSON.parse(bodyText);
    if (parsed && typeof parsed === "object" && "error" in parsed) {
      const err = (parsed as { error: unknown }).error;
      if (err && typeof err === "object") {
        const { code, message, details } = err as Record<string, unknown>;
        return new ApiError(
          status,
          typeof code === "string" && code ? code : fallbackCode,
          typeof message === "string" && message ? message : `Request failed with status ${status}.`,
          details && typeof details === "object" ? (details as Record<string, unknown>) : null,
        );
      }
    }
  } catch {
    // Not JSON; fall through to the status-based error.
  }
  return new ApiError(status, fallbackCode, `Request failed with status ${status}.`);
}

// --- Transport -------------------------------------------------------------------------

interface RequestOptions {
  method?: "GET" | "POST" | "DELETE";
  token?: string;
  body?: unknown;
  query?: Record<string, string | number | undefined>;
  /** Seconds for Next's data cache; omitted → `no-store`. Only for public, unauthenticated calls. */
  revalidate?: number;
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  if (!brand.apiUrl) {
    throw new ApiError(0, "api_not_configured", "NEXT_PUBLIC_API_URL is not set.");
  }
  const url = new URL(`${brand.apiUrl}${path}`);
  for (const [key, value] of Object.entries(options.query ?? {})) {
    if (value !== undefined && value !== "") url.searchParams.set(key, String(value));
  }

  const headers: Record<string, string> = { Accept: "application/json" };
  if (options.token) headers.Authorization = `Bearer ${options.token}`;
  if (options.body !== undefined) headers["Content-Type"] = "application/json";

  const cacheOptions: RequestInit & { next?: { revalidate: number } } =
    options.revalidate !== undefined && !options.token
      ? { next: { revalidate: options.revalidate } }
      : { cache: "no-store" };

  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      ...cacheOptions,
    });
  } catch {
    throw new ApiError(0, "network_error", "The API could not be reached.");
  }

  if (!response.ok) {
    throw errorFromResponse(response.status, await response.text());
  }
  if (response.status === 204) {
    return undefined as T;
  }
  const text = await response.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

// --- Endpoints -------------------------------------------------------------------------

export const api = {
  /** §1 `GET /v1/me` */
  getMe(token: string): Promise<Me> {
    return request<Me>(PATHS.me, { token });
  },

  /**
   * §3 `GET /v1/plans?ref=`. With a token the API binds `checkout_url` to the user and the
   * response is never cached; anonymously the plan list is cached for five minutes.
   */
  async getPlans(options: { token?: string; ref?: string | null } = {}): Promise<Plan[]> {
    const page = await request<{ plans: Plan[] }>(PATHS.plans, {
      token: options.token,
      query: { ref: options.ref ?? undefined },
      revalidate: 300,
    });
    return page.plans;
  },

  /** §2 job list (`{ jobs, next_cursor }`, mirroring the §3 ledger page shape). */
  listJobs(token: string, limit = 20): Promise<JobsPage> {
    return request<JobsPage>(PATHS.jobs, { token, query: { limit } });
  },

  /** §11 key list (`{ keys }`). */
  listApiKeys(token: string): Promise<ApiKeysPage> {
    return request<ApiKeysPage>(PATHS.apiKeys, { token });
  },

  /** §11 `POST /v1/api-keys` — the plaintext key is in the response exactly once. */
  createApiKey(token: string, name: string): Promise<ApiKeyCreated> {
    return request<ApiKeyCreated>(PATHS.apiKeys, { method: "POST", token, body: { name } });
  },

  /** §11 `DELETE /v1/api-keys/{id}` → 204. */
  revokeApiKey(token: string, id: string): Promise<void> {
    return request<void>(`${PATHS.apiKeys}/${encodeURIComponent(id)}`, { method: "DELETE", token });
  },

  /** `GET /v1/status` — public, cached for a minute (the status page revalidates on the same clock). */
  getStatus(): Promise<ServiceStatus> {
    return request<ServiceStatus>(PATHS.status, { revalidate: 60 });
  },

  /** `POST /v1/nps` — one answer per user per 30 days; the API answers 409 for a repeat. */
  submitNps(token: string, submission: NpsSubmission): Promise<void> {
    return request<void>(PATHS.nps, { method: "POST", token, body: submission });
  },
};

export type Attempt<T> = { ok: true; data: T } | { ok: false; error: ApiError };

/** Runs one API call and captures its failure so a page can render partial data. */
export async function attempt<T>(call: () => Promise<T>): Promise<Attempt<T>> {
  try {
    return { ok: true, data: await call() };
  } catch (error) {
    if (error instanceof ApiError) return { ok: false, error };
    return { ok: false, error: new ApiError(0, "internal_error", "Unexpected error.") };
  }
}
